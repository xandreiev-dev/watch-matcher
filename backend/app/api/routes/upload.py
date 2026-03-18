from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.response import PreviewResponse
from app.services.excel_service import ExcelService

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
    