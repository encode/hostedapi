This is a progress log for work on the HostedAPI service.

The work is not back-to-back over a continuous period, and days listed don't
necessarily indicate a full working day.

# Day 1

### Create the GitHub repo

Let's go! Get a repo setup and add a useful README.

### Setup Travis

I use GitHub's ["Scripts To Rule Them All" pattern](https://github.com/github/scripts-to-rule-them-all) as a standard way of managing project install, test, deployment etc. I think it's generally beneficial to always aim to reduce deliverable unit of works to the smallest possible coherent change. In this case that means plugging Travis in to a no-op test script, simply in order to demonstrate that we've integrated Travis correctly, without yet getting into the *actual* test suite setup.

### Crib from the starlette-example repo

Copied across the `app.py`, `templates`, and `statics` from the `Starlette-example` repository, so that we've got a bare bones project to work with.

### Create a new application on Heroku

Here we need to add a `Profile` to run `uvicorn`.

This helped thrash out some points of improvement for Uvicorn. For example, on some first attempts the static media were not initially displaying. It turned out this was because `url_for` was hyperlinking to an `http` URL, even though the application was being access from an `https` URL.

In order for uvicorn to properly determine that the incoming requests were `https`, I needed to add the `--proxy-headers` flag.

If I'd been using gunicorn then the `FORWARDED_ALLOW_IPS` environment variable would have automatically been used to determine if we are running behind a trusted proxy server, such as when running on Heroku.

Running `heroku run printenv` demonstrates that `FORWARDED_ALLOW_IPS=*` is set by default, which Gunicorn honours, but Uvicorn doesn't yet handle. It also shows that the `WEB_CONCURRENCY` environment variable is set, which Uvicorn could use to determine a default number of worker processes.

# Day 2

## Add test suite

The `./scripts/test` was previously just a placeholder. Let's actually hook that up to pytest, now, and add a single basic test for making a request to the homepage.

## Enforce black linting

Again, we're using GitHub's "scripts to rule them all", so...

* Add `./scripts/lint`, either invokable as `./scripts/lint --check` to just report the status, or as `./scripts/lint` to actually apply the linting.
* Call into `./scripts/lint --check` as the first part of running the tests, so that `./scripts/test` handles both lint checking and running the test suite. (Help enforce that we're getting it right in the first place before committing changes to the repo.)

## Pin dependencies

If you're managing this well, and you don't have overly massive dependency trees, then you don't necessarily need a tool like Poetry or Pipenv here.

My approach here is:

* `requirements.base` - Base set of dependencies, pinned against major version numbers for API stability.
* `requirements.txt` - Full set of pinned dependencies.

Any time `requirements.base` is updated in any way I'll run `./scripts/install --update`, which will give me a clean virtualenv, install all requirements from the base, and freeze the dependencies.

We also pin the Python runtime in Heroku, using the `runtime.txt` file.

## Environment Variables for config.

* Read config from the environment rather than hardcoded.
* Switch to running locally using `heroku local` so that our .env file is being loaded
automatically for us.
* Set `DEBUG=true` in the `.env` file on first install.
* Ensure that `.env` is included in the `.gitignore` file.

## Setup Sentry integration

Set the `SENTRY_DSN` environment to enable the integration.

Use `heroku config:set SENTRY_DSN=...` to set in production.
Modify the `.env` file if you want to test it locally.

Together with our `DEBUG` behavior this now means that:

* Errors when developing locally will display the traceback.
* Errors on the production site will render the 500 error page, and will trigger an event in Sentry.

## Automatic deploys

* Setup Heroku's deploy from GitHub, for auto deploys after Pull Requests are merged to master.

# Day 3

## Pass release version to Sentry

* Install the "Dyno Metadata" extenstion on Heroku to populate environment variables with release info.
* Pass the `HEROKU_RELEASE_VERSION` when instantiating the Sentry SDK.

## Configure the GitHub repo for neater history

Only allow "Squash Merge on pull requests, so that we have a nice neat commit history, with each commit being tied to an associated pull request.

## Render a table with associated pagination and search controls

* Crib from a pre-existing project, to render a table with basic search and pagination controls.
* Fill our table with a real data source. In this case we're using the results of the 2017 UK general election.

## Fill in basic table functionality

* Enforce 100% test coverage.
* Implement pagination controls.
* Implement column ordering controls.
* Implement search controls.

# Day 4

## Flesh out site structure

Put in place a basic admin-like site structure...

* Add a top-level dashboard page
* Add a single-item details page
* Breadcrumbs interlinking between each layer

# Day 5

## Hook up database

Loads the data from a postgres database, rather than a hardcoded data source.

* Added migrations, using alembic.
* Tests run against a newly created test database on each run.
* Individual test cases are isolated inside a transaction that rolls back at the end of each test.

# Day 6

## Make the data editable

* Add 'New Row', 'Edit Row', and 'Delete Row' controls.
* Input validation using `typesystem`.
* Persist changes to the database.

# Day 7

## Use dynamic table definitions

This work doesn't really change anything visible to the end user, but instead
changes how we store the data, so that we're using dynamic table definitions,
rather than pre-defined tables.

* Push all the data manipulation out of endpoints, and into a "DataSource" API.
* Switch our underlying SQL accesses from using a predefined table, to using dynamic table definitions.

Some issues that I ran into along the way:

#### Data migrations are awkward when they start to involve relationships.

Eg. if we're inserting some records, and then want to associate some other set of records against those,
then we need to know the primary keys of the data we've inserted. We can actually get at this by using
standard SQLAlchemy, but that means we're using a completely different type of data access than we're
using in the app itself, where we use "databases" and SQLAlchemy core.

#### Data access is awkward in test cases.

Right now we're using a synchronous test client, but our data access APIs are async, so the
two can't easily be used together in the same test case. For now we're just working around the issue.
We could resolve this issue by having an async client, based on `httpx`.

#### The 'typesystem' API doesn't feel right yet.

It's not as elegant to create new schema classes as I'd like it to be. Also I'd prefer to see
it validating into raw dictionary data types, rather than object instances. For now I'm just
working around these issues in the codebase.

# Day 8

Started implementing controls for dynamic tables. Allowing users to create new tables,
and add or delete columns from tables.

One particular thing that jumps out here is that typesystem doesn't yet support async validations,
so there's no graceful way to perform uniqueness validation for a field against the database.

Our tests are also a little bit threadbare because they don't currently test data persistence,
but instead just ensure that the expected response codes / redirects / page contexts are applied.

It's also starting to get closer to the point where I'd like to be using an ORM, rather than
working with SQLAlchemy core queries directly.

# Intermezzo

Work driven by this on Uvicorn (logging improvements, better deployment defaults).

Work driven by this on Starlette (declarative routing and middleware).

# Day 9

Implemented the GitHub authentication flow.

What's particularly nice here is how we provide a mock GitHub service that is used
in tests, and in local development. The `MOCK_GITHUB` environment variable switches
between using the live GitHub API, and using the mock application.

The authentication flow currently just affects the session, and does not create
a persistent user record.
