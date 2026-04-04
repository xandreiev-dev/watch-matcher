from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.constants import EXTRACTION_PREVIEW_ROWS_COUNT
from app.services.excel_service import ExcelService
from app.services.watch_preprocess_service import WatchPreprocessService
from app.extractors.watch_feature_extractor import WatchFeatureExtractor
from app.matchers.watch_matcher import WatchMatcher
from app.catalog.watch_reference_catalog import WatchReferenceCatalog

router = APIRouter()


def process_watch_row(row: dict, catalog: list[dict]) -> dict:
    preprocessed = WatchPreprocessService.preprocess_row(row)

    features = WatchFeatureExtractor.extract(
    title=preprocessed.product_name,
    description=preprocessed.description,
    brand=preprocessed.brand,
    )

    # На текущем этапе считаем preprocess источником правды
    features.brand = preprocessed.brand
    features.size_mm = preprocessed.size_mm
    features.is_accessory = preprocessed.is_accessory
    features.is_multi_model = preprocessed.is_multi_model or features.is_multi_model

    match_result = WatchMatcher.match(features, catalog)

    if match_result.match_status == "ambiguous_multi_model":
        features.is_multi_model = True
        features.size_mm = None
        features.family = None
        features.generation = None
        features.variant = None

    return {
        "Название": preprocessed.product_name,
        "normalized_title": preprocessed.normalized_title,
        "Бренд": preprocessed.brand,
        "brand_from_url": preprocessed.brand_from_url,
        "brand_match": preprocessed.brand_match,
        "article": preprocessed.article,
        "size_mm": features.size_mm,
        "all_sizes_mm": preprocessed.all_sizes_mm,
        "is_accessory": preprocessed.is_accessory,
        "is_multi_model": features.is_multi_model,
        "family": features.family,
        "generation": features.generation,
        "variant": features.variant,
        "Цвет": features.color,
        "Гарантия": features.warranty_period,
        "URL": preprocessed.product_url,
        "image_url": preprocessed.image_url,
        "shop_rating": preprocessed.shop_rating,
        "price": preprocessed.price,
        "match_status": match_result.match_status,
        "matched_model_id": match_result.matched_model_id,
        "matched_model_name": match_result.matched_model_name,
        "match_method": match_result.match_method,
        "confidence": match_result.confidence,
        "needs_manual_review": match_result.needs_manual_review,
    }


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

        # Временно
        catalog = WatchReferenceCatalog.load_models(brand="Garmin")
        print("CATALOG SIZE:", len(catalog))
        print("FIRST CATALOG ROW:", catalog[0] if catalog else None)

        result = []
        for _, row in preview_df.iterrows():
            row_dict = row.to_dict()
            result.append(process_watch_row(row_dict, catalog))

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

        catalog = WatchReferenceCatalog.load_models()

        result = []
        for _, row in processed_df.iterrows():
            row_dict = row.to_dict()
            result.append(process_watch_row(row_dict, catalog))

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
        raise HTTPException(
            status_code=400,
            detail="Provide either file or file_url, not both",
        )

    if not file and not file_url:
        raise HTTPException(
            status_code=400,
            detail="Either file or file_url is required",
        )

    if file:
        if not file.filename.endswith(".xlsx"):
            raise HTTPException(
                status_code=400,
                detail="Only .xlsx files are supported",
            )

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load file from URL: {str(exc)}",
        )