from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes.upload import router as upload_router
from app.api.routes.vendor import router as vendor_router
from app.api.routes.process import router as process_router

app = FastAPI(title="Watch Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vendor_router, prefix="/api/vendor", tags=["vendor"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(process_router, prefix="/api/process", tags=["process"])

@app.get("/health")
def health_check():
    return {"status": "ok"}