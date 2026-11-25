import logging
import os
import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from mailbox import MAILBOX_RELAY_URL
from transit import TRANSIT_HELPER_URL, TRANSIT_RELAY_URL

IMAGES = Path(__file__).parent.parent / "images"

PYTHON_CONTEXT = str(IMAGES / "magic-wormhole" / "upstream")
PYTHON_LOCAL_DOCKERFILE = str(IMAGES / "magic-wormhole" / "local" / "Dockerfile")
PYTHON_CONTEXT_RELEASE = str(IMAGES / "magic-wormhole" / "release")
WILLIAM_CONTEXT = str(IMAGES / "wormhole-william" / "upstream")
WILLIAM_CONTEXT_RELEASE = str(IMAGES / "wormhole-william" / "release")
RUST_CONTEXT = str(IMAGES / "magic-wormhole-rs" / "upstream")
RUST_CONTEXT_RELEASE = str(IMAGES / "magic-wormhole-rs" / "release")

# The default appid, can't change it on wormhole-william at least
APPID = "lothar.com/wormhole/text-or-file-xfer"

# python and wormhole-william print "Wormhole code is:",
# rust prints "This wormhole's code is:".
CODE_RE = re.compile(r"[Ww]ormhole(?:'s)? code is: (\d+-[a-z]+-[a-z]+)")

logger = logging.getLogger(__name__)


class Client(ABC):
    name: str
    # the directory docker builds from
    context: str

    @property
    def dockerfile(self) -> str:
        return str(Path(self.context) / "Dockerfile")

    binary: str

    @abstractmethod
    def env(self) -> Mapping[str, str]:
        """environment variables"""

    @abstractmethod
    def send_file(self, path: str) -> list[str]:
        """A command offering the file at `path`."""

    @abstractmethod
    def send_text(self, message: str) -> list[str]:
        """A command offering `message` itself."""

    @abstractmethod
    def receive_file(self, code: str, path: str) -> str:
        """Get the file from `code`, write to `path`."""

    @abstractmethod
    def receive_text(self, code: str) -> list[str]:
        """A command taking up the text offered under `code`."""


class PythonClient(Client):
    name = "pythonupstream"
    context = PYTHON_CONTEXT
    binary = "wormhole"

    def env(self) -> Mapping[str, str]:
        return {
            "WORMHOLE_RELAY_URL": MAILBOX_RELAY_URL,
            "WORMHOLE_TRANSIT_HELPER": TRANSIT_HELPER_URL,
        }

    def send_file(self, path: str) -> list[str]:
        return ["send", path, "--no-qr"]

    def send_text(self, message: str) -> list[str]:
        return ["send", "--text", message, "--no-qr"]

    def receive_file(self, code: str, path: str) -> str:
        argv = [self.binary, "receive", code, "--accept-file", "--output-file", path]
        return shlex.join(argv)

    def receive_text(self, code: str) -> list[str]:
        return ["receive", code]


class WilliamClient(Client):
    name = "williamupstream"
    context = WILLIAM_CONTEXT
    binary = "wormhole-william"

    def env(self) -> Mapping[str, str]:
        # Transit is hardcoded to transit.magic-wormhole.io:4001
        return {"WORMHOLE_RELAY_URL": MAILBOX_RELAY_URL}

    def send_file(self, path: str) -> list[str]:
        return ["send", path]

    def send_text(self, message: str) -> list[str]:
        return ["send", "--text", message]

    def receive_file(self, code: str, path: str) -> str:
        return f"echo y | {shlex.join([self.binary, 'recv', code])}"

    def receive_text(self, code: str) -> list[str]:
        return ["recv", code]


class RustClient(Client):
    name = "rustupstream"
    context = RUST_CONTEXT
    binary = "wormhole-rs"

    def env(self) -> Mapping[str, str]:
        return {
            "WORMHOLE_MAILBOX_URL": MAILBOX_RELAY_URL,
            "WORMHOLE_RELAY_URL": TRANSIT_RELAY_URL,
        }

    def send_file(self, path: str) -> list[str]:
        return ["send", path, "--no-qr"]

    def send_text(self, message: str) -> list[str]:
        raise NotImplementedError("no text transfer in rust client")

    def receive_file(self, code: str, path: str) -> str:
        out_dir = str(PurePosixPath(path).parent)
        argv = [self.binary, "receive", code, "--noconfirm", "--out-dir", out_dir]
        return shlex.join(argv)

    def receive_text(self, code: str) -> list[str]:
        raise NotImplementedError("no text transfer in rust client")


class PythonReleaseClient(PythonClient):
    name = "pythonrelease"
    context = PYTHON_CONTEXT_RELEASE


class PythonLocalClient(PythonClient):
    name = "pythonlocal"

    def __init__(self, source: Path) -> None:
        self.context = str(source)

    @property
    def dockerfile(self) -> str:
        return PYTHON_LOCAL_DOCKERFILE


class WilliamReleaseClient(WilliamClient):
    name = "williamrelease"
    context = WILLIAM_CONTEXT_RELEASE


class RustReleaseClient(RustClient):
    name = "rustrelease"
    context = RUST_CONTEXT_RELEASE


PYTHON_CLIENT = PythonClient()
WILLIAM_CLIENT = WilliamClient()
RUST_CLIENT = RustClient()
PYTHON_RELEASE_CLIENT = PythonReleaseClient()
WILLIAM_RELEASE_CLIENT = WilliamReleaseClient()
RUST_RELEASE_CLIENT = RustReleaseClient()


def local_python_clients() -> tuple[Client, ...]:
    """python built from a local checkout, if one is configured"""
    source = os.environ.get("PYTHON_LOCAL_SRC")
    if not source:
        return ()
    checkout = Path(source).expanduser()
    git = subprocess.run(
        ["git", "-C", str(checkout), "describe", "--always", "--dirty"],
        capture_output=True,
        text=True,
        check=False,
    )
    logger.warning(
        "local python image will be built from %s at %s",
        checkout,
        git.stdout.strip() or "no git metadata",
    )
    return (PythonLocalClient(checkout),)
