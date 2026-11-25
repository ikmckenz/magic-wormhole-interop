import logging
from collections.abc import Callable

import pytest
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import (
    CODE_RE,
    PYTHON_CLIENT,
    PYTHON_RELEASE_CLIENT,
    RUST_CLIENT,
    RUST_RELEASE_CLIENT,
    WILLIAM_CLIENT,
    WILLIAM_RELEASE_CLIENT,
    Client,
    local_python_clients,
)
from containers import ExitedWaitStrategy, client_container, exit_code, logs, read_file
from mailbox import MAILBOX_ALIAS, mailbox_on
from transit import TRANSIT_ALIASES, relayed_connections, transit_on

logger = logging.getLogger(__name__)

PAYLOAD = bytes(range(256)) * 4096
WORK_DIR = "/tmp"
PAYLOAD_PATH = f"{WORK_DIR}/interop-payload.bin"

CLIENTS = [
    pytest.param(PYTHON_CLIENT, id=PYTHON_CLIENT.name),
    pytest.param(WILLIAM_CLIENT, id=WILLIAM_CLIENT.name),
    pytest.param(RUST_CLIENT, id=RUST_CLIENT.name),
    pytest.param(PYTHON_RELEASE_CLIENT, id=PYTHON_RELEASE_CLIENT.name),
    pytest.param(WILLIAM_RELEASE_CLIENT, id=WILLIAM_RELEASE_CLIENT.name),
    pytest.param(RUST_RELEASE_CLIENT, id=RUST_RELEASE_CLIENT.name),
]
CLIENTS.extend(
    pytest.param(client, id=client.name) for client in local_python_clients()
)


@pytest.mark.parametrize("receiver", CLIENTS)
@pytest.mark.parametrize("sender", CLIENTS)
def test_file(
    sender: Client,
    receiver: Client,
    mailbox_image: str,
    transit_image: str,
    image_for: Callable[[Client], str],
) -> None:
    with (
        # A network per peer, with the two mailbox and transit joined to both,
        # so neither peer can reach the other directly
        Network(
            docker_network_kw={"driver": "bridge", "internal": True}
        ) as sender_network,
        Network(
            docker_network_kw={"driver": "bridge", "internal": True}
        ) as receiver_network,
        mailbox_on(mailbox_image, sender_network) as mailbox,
        transit_on(transit_image, sender_network) as transit,
    ):
        receiver_network.connect(mailbox.get_wrapped_container().id, [MAILBOX_ALIAS])
        receiver_network.connect(transit.get_wrapped_container().id, TRANSIT_ALIASES)

        with (
            client_container(image_for(sender), sender, sender_network)
            .with_copy_into_container(PAYLOAD, PAYLOAD_PATH)
            .with_command(sender.send_file(PAYLOAD_PATH))
            .waiting_for(LogMessageWaitStrategy(CODE_RE)) as sending
        ):
            match = CODE_RE.search(logs(sending))
            assert match, "no wormhole code generated in sender logs"
            code = match.group(1)

            with (
                client_container(image_for(receiver), receiver, receiver_network)
                .with_kwargs(entrypoint="/bin/sh", working_dir=WORK_DIR)
                .with_command(["-c", receiver.receive_file(code, PAYLOAD_PATH)])
                .waiting_for(ExitedWaitStrategy()) as receiving
            ):
                received = read_file(receiving, PAYLOAD_PATH)
                assert received is not None, f"no file at {PAYLOAD_PATH}"
                assert received == PAYLOAD

                receiving_logs = logs(receiving)
                logger.warning(receiving_logs)
                assert exit_code(receiving) == 0, "receiver did not exit cleanly"

            sending_logs = logs(sending)
            logger.warning(sending_logs)
            assert exit_code(sending) == 0, "sender did not exit cleanly"

        # Both peers are gone by now, so the relay has already written its
        # usage row for the connection
        connections = relayed_connections(transit)
        assert connections is not None, "could not read the relay's usage database"
        assert [c["result"] for c in connections].count("happy") == 1
        assert sum(c["bytes"] for c in connections) >= len(PAYLOAD)
