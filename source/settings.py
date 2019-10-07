from starlette.config import Config
import databases


config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)
TESTING = config("TESTING", cast=bool, default=False)
DATABASE_URL = config(
    "DATABASE_URL", cast=databases.DatabaseURL, default="sqlite:///sqlite3.db"
)
TEST_DATABASE_URL = DATABASE_URL.replace(database="test_" + DATABASE_URL.database)


# The Sentry DSN is a unique identifier for our app when connecting to Sentry
# See https://docs.sentry.io/platforms/python/#connecting-the-sdk-to-sentry
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")

# Heroku Dyno Metadata, enabled with `heroku labs:enable runtime-dyno-metadata`
# See https://devcenter.heroku.com/articles/dyno-metadata
RELEASE_VERSION = config("HEROKU_RELEASE_VERSION", cast=str, default="<local dev>")
