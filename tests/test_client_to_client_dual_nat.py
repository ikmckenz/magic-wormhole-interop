import logging
import shlex
from collections.abc import Callable

import pytest
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import CODE_RE, Client, local_python_clients
from containers import ExitedWaitStrategy, client_container, exit_code, logs, read_file
from mailbox import MAILBOX_ALIAS, mailbox_on
from router import address, router_on, via_router
from transit import TRANSIT_ALIAS, relayed_connections, transit_on

logger = logging.getLogger(__name__)

WORK_DIR = "/tmp"
PAYLOAD_PATH = f"{WORK_DIR}/interop-payload.bin"
PAYLOAD = bytes(range(256)) * 4096

CLIENTS = [pytest.param(client, id=client.name) for client in local_python_clients()]


@pytest.mark.parametrize("receiver", CLIENTS)
@pytest.mark.parametrize("sender", CLIENTS)
def test_file(
    sender: Client,
    receiver: Client,
    mailbox_image: str,
    transit_image: str,
    router_image: str,
    image_for: Callable[[Client], str],
) -> None:
    with (
        # Internetwork can be internal, but client networks can't (because they reach out)
        Network(
            docker_network_kw={"driver": "bridge", "internal": True}
        ) as internetwork,
        Network(docker_network_kw={"driver": "bridge"}) as sender_network,
        Network(docker_network_kw={"driver": "bridge"}) as receiver_network,
        mailbox_on(mailbox_image, internetwork) as mailbox,
        transit_on(transit_image, internetwork) as transit,
        router_on(router_image, internetwork) as sender_router,
        router_on(router_image, internetwork) as receiver_router,
    ):
        hosts = {
            MAILBOX_ALIAS: address(mailbox, internetwork),
            TRANSIT_ALIAS: address(transit, internetwork),
        }
        sender_network.connect(sender_router.get_wrapped_container().id)
        receiver_network.connect(receiver_router.get_wrapped_container().id)
        sender_gateway = address(sender_router, sender_network)
        receiver_gateway = address(receiver_router, receiver_network)
        logger.warning(
            "sender LAN gateway %s, receiver LAN gateway %s",
            sender_gateway,
            receiver_gateway,
        )

        with (
            client_container(image_for(sender), sender, sender_network)
            .with_kwargs(cap_add=["NET_ADMIN"], entrypoint="/bin/sh", extra_hosts=hosts)
            .with_command(
                via_router(
                    shlex.join([sender.binary, *sender.send_file(PAYLOAD_PATH)]),
                    sender_gateway,
                )
            )
            .with_copy_into_container(PAYLOAD, PAYLOAD_PATH)
            .waiting_for(LogMessageWaitStrategy(CODE_RE)) as sending
        ):
            match = CODE_RE.search(logs(sending))
            assert match, "no wormhole code generated in sender logs"
            code = match.group(1)
            logger.info(f"wormhole code {code}")

            with (
                client_container(image_for(receiver), receiver, receiver_network)
                .with_kwargs(
                    cap_add=["NET_ADMIN"],
                    entrypoint="/bin/sh",
                    extra_hosts=hosts,
                    working_dir=WORK_DIR,
                )
                .with_command(
                    via_router(
                        receiver.receive_file(code, PAYLOAD_PATH),
                        receiver_gateway,
                    )
                )
                .waiting_for(ExitedWaitStrategy()) as receiving
            ):
                received = read_file(receiving, PAYLOAD_PATH)
                logger.info("read file")
                assert received is not None, f"no file at {PAYLOAD_PATH}"
                assert received == PAYLOAD

                assert exit_code(receiving) == 0, "receiver did not exit cleanly"

            assert exit_code(sending) == 0, "sender did not exit cleanly"

        # Both peers are gone by now, so the relay has already written its
        # usage row for the connection
        # TODO: flip assert for no relayed connections, once wormhole has NAT holepunch
        connections = relayed_connections(transit)
        assert connections is not None, "could not read the relay's usage database"
        assert [c["result"] for c in connections].count("happy") == 1
        assert sum(c["bytes"] for c in connections) >= len(PAYLOAD)
