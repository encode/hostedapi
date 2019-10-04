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

## Fill in basic table functionality

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
