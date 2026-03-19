import httpx

from app.core.config import VENDOR_WATCH_MODELS_URL, API_USER, API_PASSWORD

class VendorService:
    @staticmethod
    async def fetch_vendor_models() -> list[dict]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                VENDOR_WATCH_MODELS_URL,
                auth=(API_USER, API_PASSWORD)
            )
            response.raise_for_status()
        
        data = response.json()
        return data.get("data", [])