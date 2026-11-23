import json
from pathlib import Path

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

MAILBOX_IMAGE = str(Path(__file__).parent.parent / "images" / "mailbox" / "dev")
MAILBOX_ALIAS = "mailbox"
MAILBOX_PORT = 4000
MAILBOX_READY = "websocket listening"
MAILBOX_RELAY_URL = f"ws://{MAILBOX_ALIAS}:{MAILBOX_PORT}/v1"

CHANNEL_DB = "/var/lib/mailbox/relay.sqlite"

READ_NAMEPLATES = f"""
import json, sqlite3, sys
db = sqlite3.connect({CHANNEL_DB!r}, timeout=5)
rows = db.execute("SELECT name FROM nameplates WHERE app_id = ?", (sys.argv[1],))
print(json.dumps([row[0] for row in rows]))
"""


def mailbox_on(image: str, network: Network) -> DockerContainer:
    """The mailbox server answering as MAILBOX_ALIAS on `network`."""
    return DockerContainer(
        image, network=network, network_aliases=[MAILBOX_ALIAS]
    ).waiting_for(LogMessageWaitStrategy(MAILBOX_READY))


def reserved_nameplates(container: DockerContainer, appid: str) -> list[str] | None:
    """Nameplates the server currently holds reserved for this appid.

    None if the server's database could not be read.
    """
    result = container.exec(["python", "-c", READ_NAMEPLATES, appid])
    if result.exit_code != 0:
        return None
    nameplates: list[str] = json.loads(result.output)
    return nameplates
