from io import BytesIO
import requests
import pandas as pd

from app.core.constants import PREVIEW_ROWS_COUNT

class ExcelService:
    REQUIRED_COLUMN_GROUPS = [
        ("Название", "product_name", "title", "title / product name"),
        ("Цена", "price", "Discount Price", "Price"),
        ("URL", "product_url", "url"),
    ]

    @staticmethod
    async def read_excel_file(file) -> pd.DataFrame:
        file_bytes = await file.read()
        return ExcelService.read_excel_bytes(file_bytes)
    
    @staticmethod
    def validate_columns(dataframe: pd.DataFrame) -> None:
        columns = set(dataframe.columns)
        missing_groups = [
            "/".join(group)
            for group in ExcelService.REQUIRED_COLUMN_GROUPS
            if not any(column in columns for column in group)
        ]
        if missing_groups:
            raise ValueError(f"Missing required columns: {', '.join(missing_groups)}")
        
    @staticmethod
    def build_preview(dataframe: pd.DataFrame) -> list[dict]:
        preview_df = dataframe.head(PREVIEW_ROWS_COUNT).copy()
        preview_df = preview_df.fillna("")
        return preview_df.to_dict(orient="records")
    
    @staticmethod
    def read_excel_bytes(file_bytes: bytes) -> pd.DataFrame:
        if not file_bytes:
            raise ValueError("Empty Excel file")

        return pd.read_excel(BytesIO(file_bytes))

    @staticmethod
    def read_excel_from_url(file_url: str) -> pd.DataFrame:
        if not file_url:
            raise ValueError("File URL is required")

        if ".xlsx" not in file_url.lower():
            raise ValueError("Only .xlsx URLs are supported")

        response = requests.get(file_url, timeout=20)
        response.raise_for_status()

        return ExcelService.read_excel_bytes(response.content)
        
