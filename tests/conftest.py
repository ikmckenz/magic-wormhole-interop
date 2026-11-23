from collections.abc import Iterator, Mapping
from contextlib import ExitStack
from mailbox import MAILBOX_IMAGE

import pytest
from testcontainers.core.image import DockerImage

from clients import PYTHON_CLIENT, RUST_CLIENT, WILLIAM_CLIENT, Client
from transit import TRANSIT_IMAGE


@pytest.fixture(scope="session")
def client_images() -> Iterator[Mapping[Client, str]]:
    with ExitStack() as stack:
        yield {
            client: str(stack.enter_context(DockerImage(client.image)))
            for client in (PYTHON_CLIENT, WILLIAM_CLIENT, RUST_CLIENT)
        }


@pytest.fixture(scope="session")
def mailbox_image() -> Iterator[str]:
    with DockerImage(MAILBOX_IMAGE) as image:
        yield str(image)


@pytest.fixture(scope="session")
def transit_image() -> Iterator[str]:
    with DockerImage(TRANSIT_IMAGE) as image:
        yield str(image)
