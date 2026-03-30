# OpenEnv server entry point
# This re-exports the main app for openenv validate compatibility
from app import app

__all__ = ["app"]
