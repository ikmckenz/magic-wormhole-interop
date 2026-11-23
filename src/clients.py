import re
import shlex
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from transit import TRANSIT_HELPER_URL, TRANSIT_RELAY_URL

IMAGES = Path(__file__).parent.parent / "images"

CLIENT_IMAGE = str(IMAGES / "magic-wormhole" / "dev")
WILLIAM_IMAGE = str(IMAGES / "wormhole-william" / "dev")
RUST_IMAGE = str(IMAGES / "magic-wormhole-rs" / "dev")

# The default appid can't change it on wormhole-william at least
APPID = "lothar.com/wormhole/text-or-file-xfer"

# python and wormhole-william print "Wormhole code is:",
# rust prints "This wormhole's code is:".
CODE_RE = re.compile(r"[Ww]ormhole(?:'s)? code is: (\d+-[a-z]+-[a-z]+)")


class Client(ABC):
    name: str
    image: str

    # Needed because the tests replace the image's ENTRYPOINT with a shell
    binary: str

    @abstractmethod
    def env(self, mailbox_url: str) -> Mapping[str, str]:
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
    name = "pythonmain"
    image = CLIENT_IMAGE
    binary = "wormhole"

    def env(self, mailbox_url: str) -> Mapping[str, str]:
        return {
            "WORMHOLE_RELAY_URL": mailbox_url,
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
    name = "williammain"
    image = WILLIAM_IMAGE
    binary = "wormhole-william"

    def env(self, mailbox_url: str) -> Mapping[str, str]:
        # Transit is hardcoded to transit.magic-wormhole.io:4001
        return {"WORMHOLE_RELAY_URL": mailbox_url}

    def send_file(self, path: str) -> list[str]:
        return ["send", path]

    def send_text(self, message: str) -> list[str]:
        return ["send", "--text", message]

    def receive_file(self, code: str, path: str) -> str:
        return f"echo y | {shlex.join([self.binary, 'recv', code])}"

    def receive_text(self, code: str) -> list[str]:
        return ["recv", code]


class RustClient(Client):
    name = "rustmain"
    image = RUST_IMAGE
    binary = "wormhole-rs"

    def env(self, mailbox_url: str) -> Mapping[str, str]:
        return {
            "WORMHOLE_MAILBOX_URL": mailbox_url,
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


PYTHON_CLIENT = PythonClient()
WILLIAM_CLIENT = WilliamClient()
RUST_CLIENT = RustClient()
