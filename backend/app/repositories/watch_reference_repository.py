from app.core.db import get_db_connection


class WatchReferenceRepository:
    @classmethod
    def fetch_all_models(cls) -> list[dict]:
        query = """
            SELECT
                wm.id,
                wm.brand,
                wm.model_name,
                wm.normalized_name
            FROM g_watch_model wm
            WHERE wm.brand IS NOT NULL
              AND wm.model_name IS NOT NULL
              AND wm.normalized_name IS NOT NULL
            ORDER BY wm.brand, wm.model_name
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        finally:
            connection.close()

    @classmethod
    def fetch_models_by_brand(cls, brand: str) -> list[dict]:
        query = """
            SELECT
                wm.id,
                wm.brand,
                wm.model_name,
                wm.normalized_name
            FROM g_watch_model wm
            WHERE LOWER(wm.brand) = LOWER(%s)
              AND wm.model_name IS NOT NULL
              AND wm.normalized_name IS NOT NULL
            ORDER BY wm.model_name
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (brand,))
                return cursor.fetchall()
        finally:
            connection.close()

    @classmethod
    def fetch_all_variants(cls) -> list[dict]:
        query = """
            SELECT
                wv.id,
                wv.watch_model_id,
                wm.brand,
                wm.model_name,
                wm.normalized_name,
                wv.variant_name,
                wv.case_size_mm,
                wv.case_material,
                wv.connectivity_type,
                wv.case_material_key,
                wv.connectivity_key
            FROM g_watch_variant wv
            JOIN g_watch_model wm
                ON wm.id = wv.watch_model_id
            WHERE wm.brand IS NOT NULL
            AND wm.model_name IS NOT NULL
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        finally:
            connection.close()

    @classmethod
    def fetch_variants_by_brand(cls, brand: str) -> list[dict]:
        query = """
            SELECT
                wv.id,
                wv.watch_model_id,
                wm.brand,
                wm.model_name,
                wm.normalized_name,
                wv.variant_name,
                wv.case_size_mm,
                wv.case_material,
                wv.connectivity_type,
                wv.case_material_key,
                wv.connectivity_key
            FROM g_watch_variant wv
            JOIN g_watch_model wm
                ON wm.id = wv.watch_model_id
            WHERE LOWER(wm.brand) = LOWER(%s)
            AND wm.model_name IS NOT NULL
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (brand,))
                return cursor.fetchall()
        finally:
            connection.close()