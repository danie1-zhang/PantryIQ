class ApplicationError(Exception):
    """Base class for expected application-layer failures."""


class ResourceNotFoundError(ApplicationError):
    """A requested resource does not exist within the current scope."""


class BusinessRuleError(ApplicationError):
    """Input is structurally valid but violates an application rule."""


class ConflictError(ApplicationError):
    """Persisted state conflicts with the requested operation."""


class AuthenticationError(ApplicationError):
    """Credentials are absent, invalid, expired, revoked, or inactive."""
