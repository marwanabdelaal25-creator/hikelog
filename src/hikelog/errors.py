"""Custom exceptions for hikelog — keep messages human-readable."""

from __future__ import annotations

__author__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"


class HikelogError(Exception):
    """Base error for all hikelog failures."""

    def __init__(self, message: str, code: str = "PLANTCARE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StorageError(HikelogError):
    """Raised when JSON persistence read/write fails."""

    def __init__(self, message: str, path: str | None = None):
        self.path = path
        detail = message if path is None else "%s (%s)" % (message, path)
        super().__init__(detail, code="STORAGE_ERROR")


class ValidationError(HikelogError):
    """Input failed schema or business validation."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        if field:
            detail = f"{field}: {message}"
        else:
            detail = message
        super().__init__(detail, code="VALIDATION_ERROR")


class NotFoundError(HikelogError):
    """Entity lookup returned nothing."""

    def __init__(self, entity: str, identifier: str):
        msg = "no {0} matching '{1}'".format(entity, identifier)
        super().__init__(msg, code="NOT_FOUND")
        self.entity = entity
        self.identifier = identifier


class ImportPipelineError(HikelogError):
    """External import pipeline failed — not the builtin ImportError."""

    def __init__(self, source: str, message: str):
        super().__init__("[{source}] {message}".format(source=source, message=message), code="IMPORT_ERROR")
        self.source = source


class ExportError(HikelogError):
    """Export pipeline failed."""

    def __init__(self, target: str, message: str):
        super().__init__(f"export to {target} failed — {message}", code="EXPORT_ERROR")
        self.target = target


class MigrationError(HikelogError):
    """Schema migration could not complete."""

    def __init__(self, from_ver: int, to_ver: int, reason: str):
        super().__init__(
            "migration %d -> %d: %s" % (from_ver, to_ver, reason),
            code="MIGRATION_ERROR",
        )
        self.from_ver = from_ver
        self.to_ver = to_ver


class PluginError(HikelogError):
    """Plugin load or hook execution failed."""

    pass  # noqa: E701 — keep it minimal for now


class ConflictError(HikelogError):
    """Optimistic concurrency or duplicate key."""

    def __init__(self, message: str, key: str | None = None):
        self.key = key
        super().__init__(message, code="CONFLICT")


def is_not_found(exc: BaseException) -> bool:
    return isinstance(exc, NotFoundError)


def is_validation(exc: BaseException) -> bool:
    return isinstance(exc, ValidationError)


def format_error(exc: HikelogError) -> str:
    if isinstance(exc, ValidationError) and exc.field:
        return "[%s] %s" % (exc.code, exc.message)
    return "%s: %s" % (exc.code, exc.message)


def wrap_os_error(exc: OSError, context: str) -> StorageError:
    return StorageError("%s: %s" % (context, exc))


def raise_if_missing(entity: str, obj: object | None, identifier: str) -> None:
    if obj is None:
        raise NotFoundError(entity, identifier)


class HikelogWarning(HikelogError):
    """Non-fatal issue — logged but not always raised."""

    def __init__(self, message: str):
        super().__init__(message, code="WARNING")


def chain_errors(errors: list[HikelogError]) -> str:
    return "; ".join(format_error(e) for e in errors)


def validation_errors_from_dict(
    data: dict,
    rules: dict[str, Callable[[Any], Any]],
) -> list[ValidationError]:
    """Run multiple field validators, collect all failures."""
    out: list[ValidationError] = []
    for field, fn in rules.items():
        try:
            if field in data:
                fn(data[field])
        except ValidationError as exc:
            out.append(exc)
    return out


def storage_read_error(path: str, detail: str) -> StorageError:
    return StorageError("failed to read storage: %s" % detail, path=path)


def storage_write_error(path: str, detail: str) -> StorageError:
    return StorageError("failed to write storage: %s" % detail, path=path)


def import_pipeline_error(source: str, line_no: int, msg: str) -> ImportPipelineError:
    return ImportPipelineError(source, "line %d: %s" % (line_no, msg))

