from supabase import create_client, Client
from app.config import settings


class Database:
    """Client Supabase — singleton léger pour le projet.

    On laisse create_client() gerer automatiquement les headers
    d'authentification (apikey + Authorization: Bearer).
    Ne PAS passer de headers personnalises dans ClientOptions,
    cela interfere avec l'auth automatique.
    """

    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "SUPABASE_URL et SUPABASE_SERVICE_KEY doivent être définis dans .env"
            )

        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    def health_check(self) -> bool:
        """Ping rapide de Supabase — utilisé au démarrage."""
        try:
            self.client.table("deals").select("*", count="exact").limit(0).execute()
            return True
        except Exception:
            return False


# Instance unique, importée partout
db = Database()
