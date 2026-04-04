from app.core.db import get_db_connection


class WatchReferenceRepository:
    @classmethod
    def fetch_all_models(cls) -> list[dict]:
        query = """
            SELECT
                id,
                brand,
                model_name,
                normalized_name,
                case_size_mm
            FROM g_models_watch
            WHERE brand IS NOT NULL
              AND model_name IS NOT NULL
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
                id,
                brand,
                model_name,
                normalized_name,
                case_size_mm
            FROM g_models_watch
            WHERE LOWER(brand) = LOWER(%s)
              AND model_name IS NOT NULL
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (brand,))
                return cursor.fetchall()
        finally:
            connection.close()