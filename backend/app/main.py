from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.process import router as process_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router, prefix="/api/process", tags=["process"])

@app.get("/health")
def health_check():
    return {"status": "ok"}