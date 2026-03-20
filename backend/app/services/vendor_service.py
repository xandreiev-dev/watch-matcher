import requests

from app.core.config import API_BASE, API_PASSWORD, API_USER


class VendorService:
    @staticmethod
    def fetch_vendor_models() -> list[dict]:
        url = f"{API_BASE.rstrip('/')}/vendor/watch-models"

        response = requests.get(
            url,
            auth=(API_USER, API_PASSWORD),
            timeout=10,
        )
        response.raise_for_status()

        return response.json().get("data", [])