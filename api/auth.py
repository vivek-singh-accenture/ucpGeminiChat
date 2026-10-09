from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

import config

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("static/login.html") as f:
        return HTMLResponse(f.read())


@router.post("/login")
async def login(token: str = Form(...)):
    if token == config.SECRET_TOKEN:
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie("session_token", token, httponly=True, samesite="lax", secure=True)
        return resp
    return HTMLResponse(
        "<p style='font-family:sans-serif'>Wrong token. <a href='/login'>Try again</a>.</p>",
        status_code=401,
    )
