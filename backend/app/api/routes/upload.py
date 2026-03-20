from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.response import PreviewResponse
from app.services.excel_service import ExcelService
from app.core.constants import EXTRACTION_PREVIEW_ROWS_COUNT
from app.services.extraction_service import ExtractionService

router = APIRouter()

@router.post("/preview", response_model=PreviewResponse)
async def preview_file(
    file: UploadFile | None = File(None),
    file_url: str | None = Form(""),
):

    try:
        dataframe, source_name = await get_dataframe_from_input(file, file_url)
        ExcelService.validate_columns(dataframe)
         
        return PreviewResponse(
            filename=source_name,
            total_rows=len(dataframe),
            columns=[str(column) for column in dataframe.columns.tolist()],
            preview=ExcelService.build_preview(dataframe)
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(exc)}")
    
@router.post("/extract-preview")
async def preview_file(
    file: UploadFile | None = File(None),
    file_url: str | None = Form(""),
):

    try:
        dataframe, source_name = await get_dataframe_from_input(file, file_url)
        ExcelService.validate_columns(dataframe)
        
        preview_df = dataframe.head(EXTRACTION_PREVIEW_ROWS_COUNT).copy()
        preview_df = preview_df.fillna("")

        result = []

        for _, row in preview_df.iterrows():
            title = str(row.get("Название", ""))
            description = str(row.get("Описание", ""))

            brand = ExtractionService.extract_brand(title, description)
            model = ExtractionService.extract_model(title, brand)
            color = ExtractionService.extract_color(title, description)
            warranty = ExtractionService.extract_warranty(description)
            
            result.append(
                {
                    "Название": str(title),
                    "Бренд": str(brand),
                    "Модель": str(model),
                    "Цвет": str(color),
                    "Гарантия": str(warranty),
                }
            )
        return {
            "filename": str(source_name),
            "total_rows": int(len(dataframe)),
            "preview_rows": int(len(result)),
            "preview": result,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=500, detail=f"Failed to extract file: {str(exc)} | Traceback: {traceback.format_exc()}")

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