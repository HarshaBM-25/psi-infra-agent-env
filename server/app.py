"""
server/app.py — OpenEnv server entry point.
Uses openenv create_app pattern — required by openenv validate.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

try:
    from openenv import create_app
    from env.infra_env import InfraEnv
    from env.schemas import InfraAction, InfraObservation

    app = create_app(
        InfraEnv,
        InfraAction,
        InfraObservation,
        env_name="infra-agent-env",
    )
except Exception:
    from main import app


def main():
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=7860,
        workers=1,
    )


if __name__ == "__main__":
    main()