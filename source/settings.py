from starlette.config import Config
import subprocess

config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")

# Heroku Dyno Metadata, enabled with `heroku labs:enable runtime-dyno-metadata`
# See https://devcenter.heroku.com/articles/dyno-metadata for more info.
RELEASE_VERSION = config("HEROKU_RELEASE_VERSION", cast=str, default="<local dev>")
