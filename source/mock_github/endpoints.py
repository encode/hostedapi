from source.resources import templates
from starlette.responses import JSONResponse


async def authorize(request):
    redirect_url = request.query_params.get("redirect_url", "#")

    template = "mock_github/authorize.html"
    context = {"request": request, "redirect_url": redirect_url}
    return templates.TemplateResponse(template, context)


async def access_token(request):
    return JSONResponse(
        {"access_token": "mock", "scope": "user:email", "token_type": "bearer"}
    )


async def user(request):
    return JSONResponse(
        {
            "login": "tomchristie",
            "id": 123,
            "avatar_url": "https://avatars2.githubusercontent.com/u/647359?s=40&v=4",
        }
    )
