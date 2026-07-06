from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.router import api_router
from core.config import get_settings
from core.database import init_db
from core.exceptions import add_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="jx-backend", version="0.1.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
add_exception_handlers(app)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.JXHOST,
        port=settings.JXPORT,
        reload=False,
    )
