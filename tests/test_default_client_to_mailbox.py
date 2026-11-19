import json
import re

from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

APPID = "lothar.com/wormhole/text-or-file-xfer"
MAILBOX_ALIAS = "mailbox"
MAILBOX_PORT = 4000
CHANNEL_DB = "/var/lib/mailbox/relay.sqlite"

MAILBOX_READY = "websocket listening"
CODE_RE = re.compile(r"Wormhole code is: (\d+-[a-z]+-[a-z]+)")

READ_NAMEPLATES = f"""
import json, sqlite3, sys
db = sqlite3.connect({CHANNEL_DB!r}, timeout=5)
rows = db.execute("SELECT name FROM nameplates WHERE app_id = ?", (sys.argv[1],))
print(json.dumps([row[0] for row in rows]))
"""


def logs(container):
    stdout, stderr = container.get_logs()
    return stdout.decode(errors="replace") + stderr.decode(errors="replace")


def reserved_nameplates(mailbox):
    result = mailbox.exec(["python", "-c", READ_NAMEPLATES, APPID])
    assert result.exit_code == 0, result.output.decode(errors="replace")
    return json.loads(result.output)


def test_register_code():
    with (
        DockerImage("images/magic-wormhole/dev/", tag="interop-client") as client_image,
        DockerImage("images/mailbox/dev/", tag="interop-mailbox") as mailbox_image,
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
                .with_env("WORMHOLE_RELAY_URL", f"ws://{MAILBOX_ALIAS}:{MAILBOX_PORT}/v1")
                .with_command(["send", "--text", "interop", "--no-qr"])
                .waiting_for(LogMessageWaitStrategy(CODE_RE)) as client
            ):
                code = CODE_RE.search(logs(client)).group(1)
                nameplate = code.split("-")[0]
                assert nameplate in reserved_nameplates(mailbox)
