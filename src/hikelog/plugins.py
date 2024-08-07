"""Simple plugin hook registry.

Author: Marwan Helmy
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage

HookFn = Callable[..., Any]

BUILTIN_HOOKS = (
    "before_water",
    "after_water",
    "before_backup",
    "after_backup",
    "on_report",
    "cli_register",
)


class PluginRegistry:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self._handlers: dict[str, list[tuple[str, HookFn]]] = {h: [] for h in BUILTIN_HOOKS}

    def register_handler(self, hook: str, name: str, fn: HookFn) -> None:
        if hook not in BUILTIN_HOOKS:
            raise ValidationError(f"unknown hook: {hook}")
        self._handlers.setdefault(hook, []).append((name, fn))

    def register_plugin(self, plugin_id: str, name: str, hooks: list[str], enabled: bool = True) -> dict:
        for h in hooks:
            if h not in BUILTIN_HOOKS:
                raise ValidationError(f"unknown hook in plugin: {h}")
        return self.storage.upsert_plugin({
            "id": plugin_id,
            "name": name,
            "hooks": hooks,
            "enabled": enabled,
        })

    def disable(self, plugin_id: str) -> dict:
        return self.storage.upsert_plugin({"id": plugin_id, "enabled": False})

    def enable(self, plugin_id: str) -> dict:
        return self.storage.upsert_plugin({"id": plugin_id, "enabled": True})

    def list_plugins(self) -> list[dict]:
        return self.storage.list_plugins()

    def enabled_plugins(self) -> list[dict]:
        return [p for p in self.list_plugins() if p.get("enabled", True)]

    def emit(self, hook: str, *args, **kwargs) -> list[Any]:
        if hook not in BUILTIN_HOOKS:
            raise ValidationError(f"unknown hook: {hook}")
        results = []
        for name, fn in self._handlers.get(hook, []):
            try:
                results.append(fn(*args, **kwargs))
            except Exception as exc:
                # plugins shouldn't crash core - TODO proper logging
                results.append({"error": str(exc), "plugin": name})
        return results

    def unregister_handler(self, hook: str, name: str) -> bool:
        bucket = self._handlers.get(hook, [])
        before = len(bucket)
        self._handlers[hook] = [(n, fn) for n, fn in bucket if n != name]
        return len(self._handlers[hook]) < before

    def get_plugin(self, plugin_id: str) -> dict:
        for p in self.list_plugins():
            if p.get("id") == plugin_id:
                return p
        raise NotFoundError("plugins", plugin_id)
