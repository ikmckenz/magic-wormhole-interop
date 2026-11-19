import json
from pathlib import Path

MAILBOX_IMAGE = str(Path(__file__).parent.parent / "images" / "mailbox" / "dev")
MAILBOX_ALIAS = "mailbox"
MAILBOX_PORT = 4000
MAILBOX_READY = "websocket listening"

CHANNEL_DB = "/var/lib/mailbox/relay.sqlite"

READ_NAMEPLATES = f"""
import json, sqlite3, sys
db = sqlite3.connect({CHANNEL_DB!r}, timeout=5)
rows = db.execute("SELECT name FROM nameplates WHERE app_id = ?", (sys.argv[1],))
print(json.dumps([row[0] for row in rows]))
"""


def reserved_nameplates(container, appid):
    """Nameplates the server currently holds reserved for this appid."""
    result = container.exec(["python", "-c", READ_NAMEPLATES, appid])
    assert result.exit_code == 0, result.output.decode(errors="replace")
    return json.loads(result.output)
