"""Tests for hikelog.plugins."""

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.plugins import PluginRegistry, BUILTIN_HOOKS


class TestPluginRegistry:
    def test_register_handler(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_handler("before_water", "test", lambda *a, **k: "ok")
        results = reg.emit("before_water")
        assert results == ["ok"]

    def test_unknown_hook_on_register_raises(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        with pytest.raises(ValidationError):
            reg.register_handler("invalid_hook", "test", lambda: None)

    def test_register_plugin(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        plugin = reg.register_plugin("p1", "Test Plugin", ["before_water"])
        assert plugin["name"] == "Test Plugin"

    def test_register_plugin_invalid_hook(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        with pytest.raises(ValidationError):
            reg.register_plugin("p1", "Bad", ["not_a_hook"])

    def test_emit_unknown_hook_raises(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        with pytest.raises(ValidationError):
            reg.emit("bad_hook")

    def test_emit_handler_exception(self, empty_storage):
        reg = PluginRegistry(empty_storage)

        def boom():
            raise RuntimeError("fail")

        reg.register_handler("after_water", "bad", boom)
        results = reg.emit("after_water")
        assert results[0]["error"] == "fail"
        assert results[0]["plugin"] == "bad"

    def test_unregister_handler(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_handler("on_report", "r1", lambda: 1)
        assert reg.unregister_handler("on_report", "r1") is True
        assert reg.emit("on_report") == []

    def test_unregister_missing(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        assert reg.unregister_handler("on_report", "missing") is False

    def test_get_plugin(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_plugin("p1", "Test", ["before_backup"])
        plugin = reg.get_plugin("p1")
        assert plugin["id"] == "p1"

    def test_get_plugin_not_found(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        with pytest.raises(NotFoundError):
            reg.get_plugin("missing")

    def test_disable_enable(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_plugin("p1", "Test", ["cli_register"])
        reg.disable("p1")
        assert reg.get_plugin("p1")["enabled"] is False
        reg.enable("p1")
        assert reg.get_plugin("p1")["enabled"] is True

    def test_enabled_plugins(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_plugin("p1", "On", ["before_water"], enabled=True)
        reg.register_plugin("p2", "Off", ["after_water"], enabled=False)
        enabled = reg.enabled_plugins()
        assert all(p.get("enabled", True) for p in enabled)

    def test_list_plugins(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_plugin("p1", "Test", ["before_water"])
        assert len(reg.list_plugins()) == 1

    def test_multiple_handlers(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        reg.register_handler("before_water", "a", lambda: 1)
        reg.register_handler("before_water", "b", lambda: 2)
        assert reg.emit("before_water") == [1, 2]

    def test_args_kwargs_passed(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        captured = {}

        def handler(trail_id, amount=None):
            captured["trail_id"] = trail_id
            captured["amount"] = amount

        reg.register_handler("before_water", "cap", handler)
        reg.emit("before_water", "p1", amount=250)
        assert captured == {"trail_id": "p1", "amount": 250}

    def test_empty_emit(self, empty_storage):
        reg = PluginRegistry(empty_storage)
        assert reg.emit("after_backup") == []

    def test_builtin_hooks(self):
        assert "before_water" in BUILTIN_HOOKS
        assert "cli_register" in BUILTIN_HOOKS

    @pytest.mark.parametrize("hook", list(BUILTIN_HOOKS))
    def test_all_builtin_hooks_accepted(self, empty_storage, hook):
        reg = PluginRegistry(empty_storage)
        reg.register_handler(hook, "h", lambda: None)
        reg.emit(hook)
