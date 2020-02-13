import typing

import typing

from httpx import AsyncClient
from httpx.config import TimeoutTypes
from httpx.content_streams import ByteStream
from httpx.models import Request, Response
from httpx.dispatch.base import AsyncDispatcher
from base64 import b64encode
import json
import itsdangerous


class TestClient(AsyncClient):
    __test__ = False

    def __init__(self, app, raise_server_exceptions=True):
        from source.settings import SECRET

        dispatch = ASGIDispatch(app=app, raise_app_exceptions=raise_server_exceptions)
        self.signer = itsdangerous.TimestampSigner(SECRET)
        super().__init__(
            base_url="https://testserver",
            dispatch=dispatch,
            headers={"accept": "text/html; */*"},
        )

    def login(self, user):
        session = {"username": user["username"], "avatar_url": user["avatar_url"]}
        data = b64encode(json.dumps(session).encode("utf-8"))
        data = self.signer.sign(data)
        self.cookies.set("session", data.decode("ascii"))


class ASGIDispatch(AsyncDispatcher):
    """
    A custom AsyncDispatcher that handles sending requests directly to an ASGI app.
    The simplest way to use this functionality is to use the `app` argument.
    ```
    client = httpx.AsyncClient(app=app)
    ```
    Alternatively, you can setup the dispatch instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the ASGIDispatch class:
    ```
    dispatch = httpx.ASGIDispatch(
        app=app,
        root_path="/submount",
        client=("1.2.3.4", 123)
    )
    client = httpx.AsyncClient(dispatch=dispatch)
    ```
    Arguments:
    * `app` - The ASGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `root_path` - The root path on which the ASGI application should be mounted.
    * `client` - A two-tuple indicating the client IP and port of incoming requests.
    ```
    """

    def __init__(
        self,
        app: typing.Callable,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: typing.Tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

    async def send(self, request: Request, timeout: TimeoutTypes = None) -> Response:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": request.headers.raw,
            "scheme": request.url.scheme,
            "path": request.url.path,
            "query_string": request.url.query.encode("ascii"),
            "server": request.url.host,
            "client": self.client,
            "root_path": self.root_path,
            "extensions": ["http.response.template"],
        }
        status_code = None
        headers = None
        body_parts = []
        response_started = False
        response_complete = False
        template = None
        context = None

        request_body_chunks = request.stream.__aiter__()

        async def receive() -> dict:
            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict) -> None:
            nonlocal status_code, headers, body_parts
            nonlocal response_started, response_complete
            nonlocal template, context

            if message["type"] == "http.response.start":
                assert not response_started

                status_code = message["status"]
                headers = message.get("headers", [])
                response_started = True

            elif message["type"] == "http.response.body":
                assert not response_complete
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and request.method != "HEAD":
                    body_parts.append(body)

                if not more_body:
                    response_complete = True

            elif message["type"] == "http.response.template":
                template = message["template"]
                context = message["context"]

        try:
            await self.app(scope, receive, send)
        except Exception:
            if self.raise_app_exceptions or not response_complete:
                raise

        assert response_complete
        assert status_code is not None
        assert headers is not None

        stream = ByteStream(b"".join(body_parts))

        response = Response(
            status_code=status_code,
            http_version="HTTP/1.1",
            headers=headers,
            stream=stream,
            request=request,
        )
        response.template = template
        response.context = context
        return response
