from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.response import PreviewResponse
from app.services.excel_service import ExcelService
from app.core.constants import EXTRACTION_PREVIEW_ROWS_COUNT
from app.services.extraction_service import ExtractionService

router = APIRouter()

@router.post("/preview", response_model=PreviewResponse)
async def preview_uploaded_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx")):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")
    
    try:
        dataframe = await ExcelService.read_excel_file(file)
        ExcelService.validate_columns(dataframe)
        
        return PreviewResponse(
            filename=file.filename,
            total_rows=len(dataframe),
            columns=[str(column) for column in dataframe.columns.tolist()],
            preview=ExcelService.build_preview(dataframe)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(exc)}")
    
@router.post("/extract-preview")
async def extract_preview(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx")):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")
    
    try:
        dataframe = await ExcelService.read_excel_file(file)
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
            "filename": str(file.filename),
            "total_rows": int(len(dataframe)),
            "preview_rows": int(len(result)),
            "preview": result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=500, detail=f"Failed to extract file: {str(exc)} | Traceback: {traceback.format_exc()}")
    