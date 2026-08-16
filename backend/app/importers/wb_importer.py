from __future__ import annotations

from app.importers.common_importer import ImportRunSummary, process_shop_watch_data


def process_wb_watch_data(*, dry_run: bool = False, force: bool = False) -> list[ImportRunSummary]:
    return process_shop_watch_data("wb", dry_run=dry_run, force=force)
