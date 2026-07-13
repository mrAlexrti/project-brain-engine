"""Cross-platform local-only application launcher."""

import ipaddress
import socket
import threading
import webbrowser
import argparse
from pathlib import Path

import uvicorn

from brain_engine.application.app import create_app


def select_port(host: str, requested: int) -> int:
    with socket.socket() as probe:
        try:
            probe.bind((host, requested))
            return int(probe.getsockname()[1])
        except OSError:
            if requested != 8765:
                raise
    with socket.socket() as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def is_loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def run_app(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True, data_dir: Path | None = None) -> None:
    actual = select_port(host, port)
    url = f"http://{host}:{actual}/"
    print(f"Project Brain Engine: {url}")
    if not is_loopback(host):
        print("WARNING: non-loopback binding exposes this local application to the network.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(data_dir), host=host, port=actual, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(prog="brain-app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    values = parser.parse_args()
    run_app(values.host, values.port, not values.no_open, values.data_dir)
