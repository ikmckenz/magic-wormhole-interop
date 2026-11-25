from collections.abc import Callable, Iterator
from contextlib import ExitStack

import pytest
from testcontainers.core.image import DockerImage

from clients import Client
from mailbox import MAILBOX_CONTEXT
from transit import TRANSIT_CONTEXT


@pytest.fixture(scope="session")
def image_for() -> Iterator[Callable[[Client], str]]:
    """Image factory with memoization that also cleans up on exit
    Hopefully not too clever
    """
    with ExitStack() as stack:
        built: dict[str, str] = {}

        def build(client: Client) -> str:
            existing = built.get(client.name)
            if existing is not None:
                return existing
            image = str(
                stack.enter_context(
                    DockerImage(client.context, dockerfile_path=client.dockerfile)
                )
            )
            built[client.name] = image
            return image

        yield build


@pytest.fixture(scope="session")
def mailbox_image() -> Iterator[str]:
    with DockerImage(MAILBOX_CONTEXT) as image:
        yield str(image)


@pytest.fixture(scope="session")
def transit_image() -> Iterator[str]:
    with DockerImage(TRANSIT_CONTEXT) as image:
        yield str(image)
