import logging
from collections.abc import Callable

import pytest
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import (
    CODE_RE,
    PYTHON_CLIENT,
    PYTHON_RELEASE_CLIENT,
    WILLIAM_CLIENT,
    WILLIAM_RELEASE_CLIENT,
    Client,
    local_python_clients,
)
from containers import client_container, exit_code, logs
from mailbox import mailbox_on

logger = logging.getLogger(__name__)

MESSAGE = "interop transfer payload message 123456"

TEXT_CLIENTS = [
    pytest.param(PYTHON_CLIENT, id=PYTHON_CLIENT.name),
    pytest.param(WILLIAM_CLIENT, id=WILLIAM_CLIENT.name),
    pytest.param(PYTHON_RELEASE_CLIENT, id=PYTHON_RELEASE_CLIENT.name),
    pytest.param(WILLIAM_RELEASE_CLIENT, id=WILLIAM_RELEASE_CLIENT.name),
    # Rust client has no text transfer
]
TEXT_CLIENTS.extend(
    pytest.param(client, id=client.name) for client in local_python_clients()
)


@pytest.mark.parametrize("receiver", TEXT_CLIENTS)
@pytest.mark.parametrize("sender", TEXT_CLIENTS)
def test_text(
    sender: Client,
    receiver: Client,
    mailbox_image: str,
    image_for: Callable[[Client], str],
) -> None:
    with (
        Network(docker_network_kw={"driver": "bridge", "internal": True}) as network,
        mailbox_on(mailbox_image, network),
        client_container(image_for(sender), sender, network)
        .with_command(sender.send_text(MESSAGE))
        .waiting_for(LogMessageWaitStrategy(CODE_RE)) as sending,
    ):
        match = CODE_RE.search(logs(sending))
        assert match, "no wormhole code generated in sender logs"
        code = match.group(1)
        logger.info(f"wormhole code {code}")

        with (
            client_container(image_for(receiver), receiver, network)
            .with_command(receiver.receive_text(code))
            .waiting_for(LogMessageWaitStrategy(MESSAGE)) as receiving
        ):
            receiving_logs = logs(receiving)
            assert MESSAGE in receiving_logs
            assert exit_code(receiving) == 0, "receiver did not exit cleanly"

        assert exit_code(sending) == 0, "sender did not exit cleanly"
