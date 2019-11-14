from starlette.config import Config
import databases
import sentry_sdk

config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)
TESTING = config("TESTING", cast=bool, default=False)
MOCK_GITHUB = config("MOCK_GITHUB", cast=bool, default=False)
HTTPS_ONLY = config("HTTPS_ONLY", cast=bool, default=False)
SECRET = config("SECRET", cast=str)

DATABASE_URL = config(
    "DATABASE_URL",
    cast=databases.DatabaseURL,
    default="postgresql://localhost:5432/hostedapi",
)
if DATABASE_URL.dialect == "postgres":
    DATABASE_URL = DATABASE_URL.replace(dialect="postgresql")  # pragma: nocover
    DATABASE_URL = DATABASE_URL.replace(query="max_size=8")  # pragma: nocover

TEST_DATABASE_URL = DATABASE_URL.replace(database="test_" + DATABASE_URL.database)


# GitHub API
GITHUB_CLIENT_ID = config("GITHUB_CLIENT_ID", cast=str, default="")
GITHUB_CLIENT_SECRET = config("GITHUB_CLIENT_SECRET", cast=str, default="")

# The Sentry DSN is a unique identifier for our app when connecting to Sentry
# See https://docs.sentry.io/platforms/python/#connecting-the-sdk-to-sentry
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")


# Heroku Dyno Metadata, enabled with `heroku labs:enable runtime-dyno-metadata`
# See https://devcenter.heroku.com/articles/dyno-metadata
RELEASE_VERSION = config("HEROKU_RELEASE_VERSION", cast=str, default="<local dev>")


if SENTRY_DSN:  # pragma: nocover
    sentry_sdk.init(dsn=SENTRY_DSN, release=RELEASE_VERSION)
