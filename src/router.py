from pathlib import Path

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

ROUTER_CONTEXT = str(Path(__file__).parent.parent / "images" / "router")
ROUTER_READY = "nat-ready"


def router_on(image: str, internetwork: Network) -> DockerContainer:
    return (
        DockerContainer(image, network=internetwork)
        .with_kwargs(cap_add=["NET_ADMIN"])
        .waiting_for(LogMessageWaitStrategy(ROUTER_READY))
    )


def address(container: DockerContainer, network: Network) -> str:
    """The IP `container` holds on `network`."""
    info = container.get_docker_client().get_container_inspect_info(
        container.get_wrapped_container().id
    )
    settings = info.NetworkSettings
    joined = {} if settings is None or settings.Networks is None else settings.Networks
    return str(joined[network.name].IPAddress)


def via_router(command: str, router: str) -> list[str]:
    # Ideally we'd just run the `ip route` command, then run the send command
    # later in its own thing, but Docker seems to be fighting me here
    return ["-c", f"ip route replace default via {router} && exec {command}"]
