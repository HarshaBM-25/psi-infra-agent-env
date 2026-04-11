from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def dashboard():
    with open("dashboard/dashboard.html") as f:
        return f.read()