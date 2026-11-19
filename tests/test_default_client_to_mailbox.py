import re
from uuid import uuid4

from mailbox import MAILBOX_ALIAS, MAILBOX_IMAGE, MAILBOX_PORT, MAILBOX_READY, reserved_nameplates
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

CODE_RE = re.compile(r"Wormhole code is: (\d+-[a-z]+-[a-z]+)")


def logs(container):
    stdout, stderr = container.get_logs()
    return stdout.decode(errors="replace") + stderr.decode(errors="replace")


def test_register_code():
    appid = f"interop.test/{uuid4()}"

    with (
        DockerImage("images/magic-wormhole/dev/", tag="interop-client") as client_image,
        DockerImage(MAILBOX_IMAGE, tag="interop-mailbox") as mailbox_image,
    ):
        with (
            Network(docker_network_kw={"driver": "bridge", "internal": True}) as network,
            DockerContainer(str(mailbox_image), network=network, network_aliases=[MAILBOX_ALIAS])
            .waiting_for(LogMessageWaitStrategy(MAILBOX_READY)) as mailbox,
        ):
            # 'wormhole send' allocates a code, then blocks waiting for a
            # peer we never provide, keeping the nameplate claimed.
            with (
                DockerContainer(str(client_image), network=network)
                .with_kwargs(entrypoint=["wormhole", "--appid", appid])
                .with_env("WORMHOLE_RELAY_URL", f"ws://{MAILBOX_ALIAS}:{MAILBOX_PORT}/v1")
                .with_command(["send", "--text", "interop", "--no-qr"])
                .waiting_for(LogMessageWaitStrategy(CODE_RE)) as client
            ):
                match = CODE_RE.search(logs(client))
                assert match, "no wormhole code generated in client logs"
                nameplate = match.group(1).split("-")[0]
                assert nameplate in reserved_nameplates(mailbox, appid)
