from collections.abc import Callable

import pytest
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from clients import (
    APPID,
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
from containers import client_container, logs
from mailbox import mailbox_on, reserved_nameplates

PAYLOAD = b"interop"
PAYLOAD_PATH = "/tmp/interop-payload.bin"

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


@pytest.mark.parametrize("client", CLIENTS)
def test_register_code(
    client: Client,
    mailbox_image: str,
    image_for: Callable[[Client], str],
) -> None:
    with (
        Network(docker_network_kw={"driver": "bridge", "internal": True}) as network,
        mailbox_on(mailbox_image, network) as mailbox,
        client_container(image_for(client), client, network)
        .with_copy_into_container(PAYLOAD, PAYLOAD_PATH)
        .with_command(client.send_file(PAYLOAD_PATH))
        .waiting_for(LogMessageWaitStrategy(CODE_RE)) as sending,
    ):
        # 'send' allocates a code, then blocks waiting for a peer we never
        # provide, keeping the nameplate claimed.
        match = CODE_RE.search(logs(sending))
        assert match, "no wormhole code generated in client logs"
        nameplate = match.group(1).split("-")[0]
        reserved = reserved_nameplates(mailbox, APPID)
        assert reserved is not None, "could not read the mailbox database"
        assert nameplate in reserved
