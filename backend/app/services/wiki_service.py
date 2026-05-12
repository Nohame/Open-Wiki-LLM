from pathlib import Path
from ..models.page import WikiPage
from ..storage import wiki as wiki_storage
from ..core.config import settings


def list_pages() -> list[WikiPage]:
    return wiki_storage.list_pages(Path(settings.wiki_path))


def get_page(slug: str) -> WikiPage | None:
    return wiki_storage.get_page(slug, Path(settings.wiki_path))
