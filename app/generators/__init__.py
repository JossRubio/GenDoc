"""
generators package — maps document-type keys to their generator classes.
"""

from .base import BaseGenerator
from .executive import ExecutivePresentationGenerator
from .technical import TechnicalDocsGenerator
from .user_manual import UserManualGenerator

# Registry: API key → generator class
GENERATORS: dict[str, type[BaseGenerator]] = {
    TechnicalDocsGenerator.DOC_TYPE:        TechnicalDocsGenerator,
    UserManualGenerator.DOC_TYPE:           UserManualGenerator,
    ExecutivePresentationGenerator.DOC_TYPE: ExecutivePresentationGenerator,
}

DEFAULT_DOC_TYPE = TechnicalDocsGenerator.DOC_TYPE


def get_generator(doc_type: str) -> BaseGenerator:
    """
    Return an instance of the generator for *doc_type*.

    Raises
    ------
    ValueError — if *doc_type* is not registered.
    """
    cls = GENERATORS.get(doc_type)
    if cls is None:
        valid = ", ".join(GENERATORS.keys())
        raise ValueError(f"Tipo de documento desconocido: '{doc_type}'. Válidos: {valid}")
    return cls()


__all__ = [
    "BaseGenerator",
    "TechnicalDocsGenerator",
    "UserManualGenerator",
    "ExecutivePresentationGenerator",
    "GENERATORS",
    "DEFAULT_DOC_TYPE",
    "get_generator",
]
