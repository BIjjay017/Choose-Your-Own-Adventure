from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings


app =  FastAPI(
    title = "Choose Your Own Adventure Game API",
    description = "This api generates cool stories using LLM.",
    version = '0.1.0',
    docs_url = "/docs",
    redoc_url = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_original = settings.ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers =["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload =True)