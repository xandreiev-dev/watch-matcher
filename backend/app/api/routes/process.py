from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.excel_service import ExcelService
from app.services.extraction_service import ExtractionService
from app.services.vendor_service import VendorService
from app.services.matching_service import MatchingService
from app.core.constants import EXTRACTION_PREVIEW_ROWS_COUNT

router = APIRouter()


@router.post("/preview")
async def process_preview(
    file: UploadFile | None = File(None),
    file_url: str | None = Form(""),
):

    try:
        dataframe, source_name = await get_dataframe_from_input(file, file_url)
        ExcelService.validate_columns(dataframe)

        preview_df = dataframe.head(EXTRACTION_PREVIEW_ROWS_COUNT).copy()
        preview_df = preview_df.fillna("")

        vendor_models = VendorService.fetch_vendor_models()

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
                    ## "confidence": matched.get("score") if matched else 0,
                    ## "match_type": match_type,
                    "g_model_matched": matched.get("model") if matched else "Unknown",
                    "image_url": matched.get("image_url") if matched else None,
                    "Цвет": color,
                    "Гарантия": warranty,
                    "URL": row.get("URL", ""),
                }
            )

        return {
            "filename": source_name,
            "preview": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(exc)}",
        )
    
@router.post("")
async def process_file(
    file: UploadFile | None = File(None),
    file_url: str | None = Form(""),
):

    try:
        dataframe, source_name = await get_dataframe_from_input(file, file_url)
        ExcelService.validate_columns(dataframe)

        processed_df = dataframe.copy()
        processed_df = processed_df.fillna("")

        vendor_models = VendorService.fetch_vendor_models()

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
                    ## "confidence": confidence,
                    ## "match_type": match_type,
                    "g_model_matched": matched.get("model") if matched else "Unknown",
                    "image_url": matched.get("image_url") if matched else None,
                    "Цвет": color,
                    "Гарантия": warranty,
                    "URL": url,
                }
            )

        return {
            "filename": source_name,
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
    
async def get_dataframe_from_input(file: UploadFile | None, file_url: str | None):
    
    if file is not None and getattr(file, "filename", "") == "":
        file = None

    if file_url is not None:
        file_url = file_url.strip()
        if file_url == "":
            file_url = None

    if file and file_url:
        raise HTTPException(status_code=400, detail="Provide either file or file_url, not both")

    if not file and not file_url:
        raise HTTPException(status_code=400, detail="Either file or file_url is required")

    if file:
        if not file.filename.endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

        dataframe = await ExcelService.read_excel_file(file)
        source_name = file.filename
        return dataframe, source_name

    try:
        dataframe = ExcelService.read_excel_from_url(file_url)
        source_name = file_url
        return dataframe, source_name
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load file from URL: {str(exc)}")