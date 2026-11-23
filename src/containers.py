import io
import tarfile
from collections.abc import Mapping

from requests.exceptions import ConnectionError
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import WaitStrategy, WaitStrategyTarget

EXIT_TIMEOUT = 30
STILL_RUNNING = frozenset(("created", "running", "paused", "restarting"))


class ExitedWaitStrategy(WaitStrategy):
    def wait_until_ready(self, container: WaitStrategyTarget) -> None:
        def finished() -> bool:
            container.reload()
            return container.status not in STILL_RUNNING

        if not self._poll(finished):
            raise TimeoutError(
                f"container did not finish in {self._startup_timeout:.3f} seconds"
            )


def with_envs(container: DockerContainer, envs: Mapping[str, str]) -> DockerContainer:
    """Set a whole mapping's worth of environment variables on `container`."""
    for key, value in envs.items():
        container.with_env(key, value)
    return container


def logs(container: DockerContainer) -> str:
    stdout, stderr = container.get_logs()
    return stdout.decode(errors="replace") + stderr.decode(errors="replace")


def exit_code(container: DockerContainer) -> int | None:
    try:
        status = int(
            container.get_wrapped_container().wait(timeout=EXIT_TIMEOUT)["StatusCode"]
        )
        return status
    except ConnectionError:
        # docs say ReadTimeout for this, but I get ConnectionError?
        return None


def read_file(container: DockerContainer, source_in_container: str) -> bytes | None:
    """Bytes of a file inside a container, read straight out of docker's tar.

    None if the path is absent or is not a regular file; callers decide what
    that means, since only a test knows what it expected.
    Hopefully we can delete this eventually: https://github.com/testcontainers/testcontainers-python/issues/1149
    """
    stream, _ = container.get_wrapped_container().get_archive(source_in_container)
    with tarfile.open(fileobj=io.BytesIO(b"".join(stream)), mode="r|*") as archive:
        entry = archive.next()
        if entry is None:
            return None
        member = archive.extractfile(entry)
        if member is None:
            return None
        return member.read()
