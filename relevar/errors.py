"""Errores de relevar con exit code (MEMORIA_RELEVAR §3)."""


class RelevarError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code
