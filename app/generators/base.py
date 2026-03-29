"""
base.py — Abstract base class for all document generators.

To add a new document type:
  1. Create a new module in this package (e.g. my_type.py)
  2. Subclass BaseGenerator and fill in DOC_TYPE, DISPLAY_NAME, and generate()
  3. Register the class in __init__.GENERATORS
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..repo_reader import RepoScan


class BaseGenerator(ABC):
    # Subclasses must define these
    DOC_TYPE: str = ""        # snake_case key used in the API  (e.g. "technical")
    DISPLAY_NAME: str = ""    # Human-readable label            (e.g. "Documentación técnica")
    FILE_SUFFIX: str = ""     # Appended to the output filename (e.g. "documentacion_tecnica")

    @abstractmethod
    def generate(self, repo_scan: RepoScan, template_path: str | None = None) -> bytes:
        """
        Build the Word document from the scanned repository.

        Parameters
        ----------
        repo_scan:
            Result of ``repo_reader.scan()`` — contains all source files.
        template_path:
            Optional path to a reference document supplied by the user.

        Returns
        -------
        bytes
            Raw ``.docx`` file content ready to be written to disk or streamed.
        """
        ...

    def output_filename(self, repo_name: str) -> str:
        """Return the suggested output filename for this document type."""
        suffix = self.FILE_SUFFIX or self.DOC_TYPE
        return f"{repo_name}_{suffix}.docx"

    def output_path(self, repo_name: str, output_dir: str) -> Path:
        return Path(output_dir) / self.output_filename(repo_name)
