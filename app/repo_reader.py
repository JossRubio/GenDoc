"""
repo_reader.py — Scans a local repository and extracts source file contents.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────

IGNORED_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", ".pnp",
    "venv", "env", ".venv", ".env",
    "dist", "build", "out", "target", "bin", "obj",
    ".next", ".nuxt", ".output",
    "coverage", ".nyc_output",
    ".idea", ".vscode",
})

SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    # Web
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    # Backend / scripting
    ".py", ".rb", ".php", ".go", ".java", ".kt", ".scala",
    ".cs", ".fs", ".vb",
    ".c", ".h", ".cpp", ".hpp", ".cc",
    ".rs", ".swift", ".dart", ".m", ".mm",
    ".r", ".jl",
    ".sh", ".bash", ".zsh", ".ps1", ".psm1",
    # Config / data
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".env.example",
    # Docs / markup
    ".md", ".mdx", ".rst", ".txt",
    # Database
    ".sql",
    # Other
    ".proto", ".graphql", ".gql",
})

MAX_FILE_BYTES = 500_000  # skip files larger than ~500 KB


# ── Data model ───────────────────────────────────────────────────────

@dataclass
class SourceFile:
    relative_path: str   # e.g. "src/main.py"
    extension: str       # e.g. ".py"
    size_bytes: int
    content: str


@dataclass
class RepoScan:
    root: str
    files: list[SourceFile]
    skipped: list[str]   # paths skipped due to read errors or size limit

    @property
    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def total_files(self) -> int:
        return len(self.files)


# ── Public API ───────────────────────────────────────────────────────

def scan(repo_path: str) -> RepoScan:
    """
    Recursively walk *repo_path*, collect all source files, and return a
    :class:`RepoScan` with their content.

    Raises
    ------
    ValueError  — if *repo_path* does not exist, is not a directory, or
                  cannot be accessed due to permissions.
    """
    try:
        root = Path(repo_path).resolve()
    except (OSError, ValueError) as exc:
        raise ValueError(f"Ruta inválida: {repo_path} — {exc}") from exc

    try:
        exists = root.exists()
        is_dir = root.is_dir()
    except PermissionError:
        raise ValueError(
            f"Sin permisos para acceder a la ruta: {repo_path}"
        )

    if not exists:
        raise ValueError(f"La ruta no existe: {repo_path}")
    if not is_dir:
        raise ValueError(f"La ruta no es una carpeta: {repo_path}")

    collected: list[SourceFile] = []
    skipped: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=None):
        # Prune ignored directories in-place so os.walk skips their subtrees
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS and not d.startswith(".")
        ]

        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext not in SOURCE_EXTENSIONS:
                continue

            abs_path = Path(dirpath) / filename

            try:
                size = abs_path.stat().st_size
            except OSError:
                skipped.append(str(abs_path.relative_to(root)).replace("\\", "/"))
                continue

            if size > MAX_FILE_BYTES:
                skipped.append(str(abs_path.relative_to(root)).replace("\\", "/"))
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                skipped.append(str(abs_path.relative_to(root)).replace("\\", "/"))
                continue

            collected.append(
                SourceFile(
                    relative_path=str(abs_path.relative_to(root)).replace("\\", "/"),
                    extension=ext,
                    size_bytes=size,
                    content=content,
                )
            )

    return RepoScan(root=str(root), files=collected, skipped=skipped)
