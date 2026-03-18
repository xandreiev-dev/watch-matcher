from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes.upload import router as upload_router

app = FastAPI(tittle="Watch Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/upload", tags=["upload"])

@app.get("/health")
def health_check():
    return {"status": "ok"}