import json
from pathlib import Path
from typing import Any

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

TRANSIT_IMAGE = str(Path(__file__).parent.parent / "images" / "transit" / "upstream")
# We use the real address because wormhole-william hardcodes it, not configurable
TRANSIT_ALIAS = "transit.magic-wormhole.io"
TRANSIT_PORT = 4001
TRANSIT_READY = "ServerFactory starting on 4001"
# python takes any name at all through WORMHOLE_TRANSIT_HELPER, in this hint form
TRANSIT_HELPER_URL = f"tcp:{TRANSIT_ALIAS}:{TRANSIT_PORT}"
# rust wants a real URL instead: tcp://transit.magic-wormhole.io:4001
TRANSIT_RELAY_URL = f"tcp://{TRANSIT_ALIAS}:{TRANSIT_PORT}"
TRANSIT_ALIASES = [TRANSIT_ALIAS]


def transit_on(image: str, network: Network) -> DockerContainer:
    """The transit relay answering as TRANSIT_ALIASES on `network`."""
    return DockerContainer(
        image, network=network, network_aliases=TRANSIT_ALIASES
    ).waiting_for(LogMessageWaitStrategy(TRANSIT_READY))


USAGE_DB = "/var/lib/transit/usage.sqlite"

READ_USAGE = f"""
import json, sqlite3
db = sqlite3.connect({USAGE_DB!r}, timeout=5)
rows = db.execute("SELECT result, total_bytes FROM usage")
print(json.dumps([{{"result": row[0], "bytes": row[1]}} for row in rows]))
"""


def relayed_connections(container: DockerContainer) -> list[dict[str, Any]] | None:
    """Every connection the relay glued, each with its result and byte count.

    None if the relay's usage database could not be read.
    """
    result = container.exec(["python", "-c", READ_USAGE])
    if result.exit_code != 0:
        return None
    rows: list[dict[str, Any]] = json.loads(result.output)
    return rows
