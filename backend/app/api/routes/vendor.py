from fastapi import APIRouter, HTTPException

from app.services.vendor_service import VendorService

router = APIRouter()

@router.get("/models-preview")
async def get_vendor_models_preview():
    try:
        models = VendorService.fetch_vendor_models()
        return {"total": len(models),
                "preview": models[:10],
                }
    
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch vendor models: {str(exc)}"
        )