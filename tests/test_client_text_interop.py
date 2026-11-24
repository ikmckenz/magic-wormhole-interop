import logging
from collections.abc import Mapping
from mailbox import MAILBOX_RELAY_URL, mailbox_on

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import (
    CODE_RE,
    PYTHON_CLIENT,
    PYTHON_RELEASE_CLIENT,
    WILLIAM_CLIENT,
    WILLIAM_RELEASE_CLIENT,
    Client,
)
from containers import exit_code, logs, with_envs

logger = logging.getLogger(__name__)

MESSAGE = "interop transfer payload message 123456"

TEXT_CLIENTS = [
    pytest.param(PYTHON_CLIENT, id=PYTHON_CLIENT.name),
    pytest.param(WILLIAM_CLIENT, id=WILLIAM_CLIENT.name),
    pytest.param(PYTHON_RELEASE_CLIENT, id=PYTHON_RELEASE_CLIENT.name),
    pytest.param(WILLIAM_RELEASE_CLIENT, id=WILLIAM_RELEASE_CLIENT.name),
    # Rust client has no text transfer
]


@pytest.mark.parametrize("receiver", TEXT_CLIENTS)
@pytest.mark.parametrize("sender", TEXT_CLIENTS)
def test_text(
    sender: Client,
    receiver: Client,
    client_images: Mapping[Client, str],
    mailbox_image: str,
) -> None:
    with (
        Network(docker_network_kw={"driver": "bridge", "internal": True}) as network,
        mailbox_on(mailbox_image, network),
        with_envs(
            DockerContainer(client_images[sender], network=network),
            sender.env(MAILBOX_RELAY_URL),
        )
        .with_command(sender.send_text(MESSAGE))
        .waiting_for(LogMessageWaitStrategy(CODE_RE)) as sending,
    ):
        match = CODE_RE.search(logs(sending))
        assert match, "no wormhole code generated in sender logs"
        code = match.group(1)

        with (
            with_envs(
                DockerContainer(client_images[receiver], network=network),
                receiver.env(MAILBOX_RELAY_URL),
            )
            .with_command(receiver.receive_text(code))
            .waiting_for(LogMessageWaitStrategy(MESSAGE)) as receiving
        ):
            receiving_logs = logs(receiving)
            logger.warning(receiving_logs)
            assert MESSAGE in receiving_logs
            assert exit_code(receiving) == 0, "receiver did not exit cleanly"

        logger.warning(logs(sending))
        assert exit_code(sending) == 0, "sender did not exit cleanly"
