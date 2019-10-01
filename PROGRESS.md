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
