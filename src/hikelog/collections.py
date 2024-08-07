"""Trail groupings / collections (e.g. kitchen herbs).

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


class CollectionManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def create(self, name: str, description: str = "", trail_ids: Optional[Iterable[str]] = None) -> dict:
        if not name.strip():
            raise ValidationError("collection name required")
        ids = list(trail_ids or [])
        for pid in ids:
            self.storage.get_trail(pid)
        return self.storage.create_collection({
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "description": description,
            "trail_ids": ids,
        })

    def list_all(self) -> list[dict]:
        return self.storage.list_collections()

    def get(self, collection_id: str) -> dict:
        for c in self.list_all():
            if c.get("id") == collection_id:
                return c
        raise NotFoundError("collections", collection_id)

    def add_trail(self, collection_id: str, trail_id: str) -> dict:
        coll = self.get(collection_id)
        self.storage.get_trail(trail_id)
        ids = list(coll.get("trail_ids", []))
        if trail_id not in ids:
            ids.append(trail_id)
        return self.storage.update_collection(collection_id, {"trail_ids": ids})

    def remove_trail(self, collection_id: str, trail_id: str) -> dict:
        coll = self.get(collection_id)
        ids = [x for x in coll.get("trail_ids", []) if x != trail_id]
        return self.storage.update_collection(collection_id, {"trail_ids": ids})

    def rename(self, collection_id: str, name: str) -> dict:
        if not name.strip():
            raise ValidationError("name required")
        return self.storage.update_collection(collection_id, {"name": name.strip()})

    def delete(self, collection_id: str) -> None:
        self.storage.delete_collection(collection_id)

    def trails_in(self, collection_id: str) -> list[dict]:
        coll = self.get(collection_id)
        out = []
        for pid in coll.get("trail_ids", []):
            try:
                out.append(self.storage.get_trail(pid).to_dict())
            except NotFoundError:
                pass  # stale id
        return out

    def collections_for_trail(self, trail_id: str) -> list[dict]:
        return [
            c for c in self.list_all()
            if trail_id in c.get("trail_ids", [])
        ]

    def merge(self, target_id: str, source_id: str) -> dict:
        target = self.get(target_id)
        source = self.get(source_id)
        merged_ids = list(dict.fromkeys(
            list(target.get("trail_ids", [])) + list(source.get("trail_ids", []))
        ))
        self.storage.update_collection(target_id, {"trail_ids": merged_ids})
        self.delete(source_id)
        return self.get(target_id)
