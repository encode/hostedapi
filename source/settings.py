from starlette.config import Config

config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)

# The Sentry DSN is a unique identifier for our app when connecting to Sentry
# See https://docs.sentry.io/platforms/python/#connecting-the-sdk-to-sentry
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")

# Heroku Dyno Metadata, enabled with `heroku labs:enable runtime-dyno-metadata`
# See https://devcenter.heroku.com/articles/dyno-metadata
RELEASE_VERSION = config("HEROKU_RELEASE_VERSION", cast=str, default="<local dev>")
