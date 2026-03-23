import os
import base64
from pathlib import Path

import pandas as pd
import requests


BASE_URL = os.getenv("API_BASE_URL", "https://api.premikum.com")
VENDOR_API_USER = os.getenv("API_USER", "ozon_api_user")
VENDOR_API_PASSWORD = os.getenv("API_PASSWORD", "secret_password_for_ozon^_^")


def main() -> None:
    # Путь к xlsx, который сгенерировал твой backend
    src = Path("backend/output/watch_sample_matched.xlsx")

    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")

    df = pd.read_excel(src, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    required_cols = ["Название", "Бренд", "g_model_matched"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    payload = {"rows": df[required_cols].to_dict(orient="records")}

    response = requests.post(
        f"{BASE_URL.rstrip('/')}/vendor/watch-matched/compare",
        json=payload,
        auth=(VENDOR_API_USER, VENDOR_API_PASSWORD),
        timeout=30,
    )
    response.raise_for_status()
    out = response.json()

    print("stats:", out.get("stats"))

    matches_path = Path("backend/output/matches_from_api.xlsx")
    mismatches_path = Path("backend/output/mismatches_from_api.xlsx")

    matches_xlsx_base64 = out.get("matches_xlsx_base64")
    mismatches_xlsx_base64 = out.get("mismatches_xlsx_base64")

    if matches_xlsx_base64:
        matches_path.write_bytes(base64.b64decode(matches_xlsx_base64))
        print(f"saved: {matches_path}")

    if mismatches_xlsx_base64:
        mismatches_path.write_bytes(base64.b64decode(mismatches_xlsx_base64))
        print(f"saved: {mismatches_path}")


if __name__ == "__main__":
    main()