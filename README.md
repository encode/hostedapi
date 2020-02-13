# HostedAPI

I want to start building out an example Starlette service in production,
and writing about the process as I'm doing so.

I'm hoping that by taking this on I'll be able to start filling in any gaps
in the async Python web ecosystem we've been building up with Starlette, Uvicorn,
Databases, ORM, TypeSystem, and HTTPX.

I'll be doing this work against a public repository, and trying to deal with any
roadblocks openly without trying to hide away any points that might not yet be
as mature as building out a service with Django or Flask might be.

I don't want to make too much of a public commitment about where this project
will end up going just yet, but I'm keeping a [progress log here](https://github.com/encode/hostedapi.com/blob/master/PROGRESS.md) to help share the learnings along the way.

## Production Environment

The service is deployed to http://hostedapi.herokuapp.com/

## Local Development

Requirements:

* [Python 3.8](https://www.python.org/downloads/)
* [Postgres](https://www.postgresql.org/download/) (For Mac, I'd recommend [Postgres.app](https://postgresapp.com/))

To install and run the application:

Create a new database 'hostedapi', then:

```shell
$ ./scripts/install
$ ./scripts/migration upgrade head
$ ./scripts/run
```

Run the lint checks and test suite:

```shell
$ ./scripts/test
```

Apply code formatting:

```shell
$ ./scripts/lint
```
