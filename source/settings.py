from starlette.config import Config
import subprocess

config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")
GIT_REVISION = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True
).stdout.decode("ascii")
