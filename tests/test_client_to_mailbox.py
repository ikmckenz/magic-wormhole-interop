from collections.abc import Mapping
from mailbox import MAILBOX_RELAY_URL, mailbox_on, reserved_nameplates

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import APPID, CODE_RE, PYTHON_CLIENT, RUST_CLIENT, WILLIAM_CLIENT, Client
from containers import logs, with_envs

PAYLOAD = b"interop"
PAYLOAD_PATH = "/tmp/interop-payload.bin"


@pytest.mark.parametrize(
    "client",
    [PYTHON_CLIENT, WILLIAM_CLIENT, RUST_CLIENT],
    ids=lambda client: client.name,
)
def test_register_code(
    client: Client, client_images: Mapping[Client, str], mailbox_image: str
) -> None:
    with (
        Network(docker_network_kw={"driver": "bridge", "internal": True}) as network,
        mailbox_on(mailbox_image, network) as mailbox,
        with_envs(
            DockerContainer(client_images[client], network=network),
            client.env(MAILBOX_RELAY_URL),
        )
        .with_copy_into_container(PAYLOAD, PAYLOAD_PATH)
        .with_command(client.send_file(PAYLOAD_PATH))
        .waiting_for(LogMessageWaitStrategy(CODE_RE)) as client_container,
    ):
        # 'send' allocates a code, then blocks waiting for a peer we never
        # provide, keeping the nameplate claimed.
        match = CODE_RE.search(logs(client_container))
        assert match, "no wormhole code generated in client logs"
        nameplate = match.group(1).split("-")[0]
        reserved = reserved_nameplates(mailbox, APPID)
        assert reserved is not None, "could not read the mailbox database"
        assert nameplate in reserved
