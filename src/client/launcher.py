"""Game process spawning."""

import logging
import os
import subprocess
import sys
from pathlib import Path

from src import config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def launch_game(game_path: str, zaap_port: int = 5559) -> None:
    """Spawn the game client process with autologin arguments.

    Args:
        game_path: Path to the game executable.
        zaap_port: Local zaap port (default 5559).
    """
    game = Path(game_path)
    if not game.exists():
        msg = f"Game not found: {game_path}"
        raise FileNotFoundError(msg)

    args = [
        str(game.absolute()),
        f"--port={zaap_port}",
        "--gameName=retro",
        "--gameRelease=main",
        "--instanceId=1",
        "--gameInstanceKey=starloco_forge",
    ]

    env = os.environ.copy()

    if sys.platform.startswith("linux"):
        args.insert(len(args), "--disable-software-rasterizer")
        args.insert(len(args), "--disable-gpu")

        env["ELECTRON_ENABLE_STACK_DUMPING"] = "1"
        logger.info("Linux detected, wrapping with wine")
        cmd = ["wine", *args]

        wine_prefix = config.get("wine_prefix", "~/.wine-dofus")
        wine_prefix_path = Path(wine_prefix.replace("~", str(Path.home())))

        if wine_prefix_path.exists():
            env["WINEPREFIX"] = str(wine_prefix_path)
            logger.info("Using WINEPREFIX: %s", wine_prefix_path)
        else:
            logger.info(
                "WINEPREFIX not found at %s, will be created on first run", wine_prefix_path
            )
    else:
        cmd = args

    logger.info("Launching game: %s", cmd)
    subprocess.Popen(cmd, start_new_session=True, cwd=str(game.parent), env=env)
