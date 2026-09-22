import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import auth, results, submissions, topics, votes

Base.metadata.create_all(bind=engine)
os.makedirs(settings.upload_dir, exist_ok=True)

app = FastAPI(title="CookBattle API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before shipping past the hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(submissions.router)
app.include_router(votes.router)
app.include_router(results.router)


@app.get("/health")
def health():
    return {"status": "ok"}
