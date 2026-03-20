from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.excel_service import ExcelService
from app.services.extraction_service import ExtractionService
from app.services.vendor_service import VendorService
from app.services.matching_service import MatchingService
from app.core.constants import EXTRACTION_PREVIEW_ROWS_COUNT

router = APIRouter()


@router.post("/preview")
async def process_preview(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    try:
        dataframe = await ExcelService.read_excel_file(file)
        ExcelService.validate_columns(dataframe)

        preview_df = dataframe.head(EXTRACTION_PREVIEW_ROWS_COUNT).copy()
        preview_df = preview_df.fillna("")

        vendor_models = await VendorService.fetch_vendor_models()

        result = []

        for _, row in preview_df.iterrows():
            title = str(row.get("Название", ""))
            description = str(row.get("Описание", ""))

            brand = ExtractionService.extract_brand(title, description)
            model = ExtractionService.extract_model(title, brand)
            color = ExtractionService.extract_color(title, description)
            warranty = ExtractionService.extract_warranty(description)

            matched = MatchingService.match_model(brand, model, vendor_models)

            confidence = matched.get("score") if matched else 0
            match_type = matched.get("match_type") if matched else "none"

            result.append(
                {
                    "Название": title,
                    "Бренд": brand,
                    "Модель": model,
                    "confidence": matched.get("score") if matched else 0,
                    "match_type": match_type,
                    "g_model_matched": matched.get("model") if matched else "Unknown",
                    "image_url": matched.get("image_url") if matched else None,
                    "Цвет": color,
                    "Гарантия": warranty,
                    "URL": row.get("URL", ""),
                }
            )

        return {
            "filename": file.filename,
            "preview": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(exc)}",
        )
    
@router.post("")
async def process_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    try:
        dataframe = await ExcelService.read_excel_file(file)
        ExcelService.validate_columns(dataframe)

        processed_df = dataframe.copy()
        processed_df = processed_df.fillna("")

        vendor_models = await VendorService.fetch_vendor_models()

        result = []

        for _, row in processed_df.iterrows():
            title = str(row.get("Название", ""))
            description = str(row.get("Описание", ""))
            url = str(row.get("URL", ""))

            brand = ExtractionService.extract_brand(title, description)
            model = ExtractionService.extract_model(title, brand)
            color = ExtractionService.extract_color(title, description)
            warranty = ExtractionService.extract_warranty(description)

            matched = MatchingService.match_model(brand, model, vendor_models)

            confidence = matched.get("score") if matched else 0
            match_type = matched.get("match_type") if matched else "none"

            result.append(
                {
                    "Название": title,
                    "Бренд": brand,
                    "Модель": model,
                    "confidence": confidence,
                    "match_type": match_type,
                    "g_model_matched": matched.get("model") if matched else "Unknown",
                    "image_url": matched.get("image_url") if matched else None,
                    "Цвет": color,
                    "Гарантия": warranty,
                    "URL": url,
                }
            )

        return {
            "filename": file.filename,
            "total_rows": len(result),
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(exc)}",
        )