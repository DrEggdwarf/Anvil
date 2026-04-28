"""Workspace file manager — per-session isolated directories.

Manages temporary workspaces for compilation, binary analysis, etc.
Each session gets its own sandbox directory under workspace_base_dir.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.exceptions import InvalidFile

logger = logging.getLogger(__name__)

# Allowed source extensions for writing.
# Aligned with pwn._LANG_MAP so /api/compile/files and /api/pwn/upload share
# the same allowlist (Sprint 14 fix #3).
_SOURCE_EXTENSIONS = frozenset({
    ".asm", ".s", ".c", ".h", ".py", ".ld",
    ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    ".rs", ".go",
})


class WorkspaceManager:
    """Manage per-session workspace directories."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(base_dir or settings.workspace_base_dir).expanduser()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def create_workspace(self, session_id: str) -> str:
        """Create an isolated workspace directory for a session.

        Returns the absolute path to the workspace.
        """
        workspace = self._base_dir / session_id
        workspace.mkdir(parents=True, exist_ok=True)
        logger.info("Created workspace: %s", workspace)
        return str(workspace)

    def get_workspace(self, session_id: str) -> str:
        """Get workspace path. Creates if it doesn't exist."""
        workspace = self._base_dir / session_id
        if not workspace.exists():
            return self.create_workspace(session_id)
        return str(workspace)

    def destroy_workspace(self, session_id: str) -> bool:
        """Remove a session's workspace directory entirely."""
        workspace = self._base_dir / session_id
        if workspace.exists():
            shutil.rmtree(workspace)
            logger.info("Destroyed workspace: %s", workspace)
            return True
        return False

    def write_source(
        self, session_id: str, filename: str, content: str
    ) -> str:
        """Write source code to a file in the session workspace.

        Validates filename and extension. Returns the absolute path.
        """
        _validate_filename(filename)
        workspace = self.get_workspace(session_id)
        filepath = Path(workspace) / filename
        # Prevent path traversal
        if not filepath.resolve().is_relative_to(Path(workspace).resolve()):
            raise InvalidFile("Path traversal detected")
        filepath.write_text(content)
        return str(filepath)

    def read_source(self, session_id: str, filename: str) -> str:
        """Read a source file from the session workspace."""
        workspace = self.get_workspace(session_id)
        filepath = Path(workspace) / filename
        if not filepath.resolve().is_relative_to(Path(workspace).resolve()):
            raise InvalidFile("Path traversal detected")
        if not filepath.exists():
            raise InvalidFile(f"File not found: {filename}")
        return filepath.read_text()

    def list_files(self, session_id: str) -> list[dict]:
        """List all files in a session workspace.

        Returns: [{name, size, is_binary}]
        """
        workspace = Path(self.get_workspace(session_id))
        files = []
        for p in sorted(workspace.iterdir()):
            if p.is_file():
                files.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "is_binary": p.suffix not in _SOURCE_EXTENSIONS,
                })
        return files

    def delete_file(self, session_id: str, filename: str) -> bool:
        """Delete a file from the session workspace."""
        workspace = Path(self.get_workspace(session_id))
        filepath = workspace / filename
        if not filepath.resolve().is_relative_to(workspace.resolve()):
            raise InvalidFile("Path traversal detected")
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def get_file_path(self, session_id: str, filename: str) -> str:
        """Get the absolute path to a file in the workspace."""
        workspace = Path(self.get_workspace(session_id))
        filepath = workspace / filename
        if not filepath.resolve().is_relative_to(workspace.resolve()):
            raise InvalidFile("Path traversal detected")
        return str(filepath)

    def resolve_under_workspace(self, session_id: str, raw_path: str) -> str:
        """Resolve any path (basename or absolute) to an absolute path under the workspace.

        Used by API endpoints that accept a user-supplied path
        (e.g. /api/pwn/elf/checksec?path=...). Rejects paths outside the workspace,
        symlinks pointing outside, and null bytes.

        Sprint 14 fix #3 (Security A1, Pentester #5/#6): closes LFI via pwntools.ELF()
        and symlink escape via write_source over a pre-existing symlink.
        """
        if not raw_path or "\x00" in raw_path:
            raise InvalidFile("Empty or null-byte path")

        workspace = Path(self.get_workspace(session_id)).resolve()
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = workspace / candidate

        # Reject symlinks (refuse to follow even pre-existing ones).
        if candidate.is_symlink():
            raise InvalidFile("Symlinks are not allowed in workspace paths")

        resolved = candidate.resolve()
        if not resolved.is_relative_to(workspace):
            raise InvalidFile("Path traversal detected")
        return str(resolved)

    def cleanup_all(self) -> int:
        """Remove all workspaces. Returns count of removed."""
        count = 0
        if self._base_dir.exists():
            for child in self._base_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                    count += 1
        logger.info("Cleaned up %d workspaces", count)
        return count


def _validate_filename(filename: str) -> None:
    """Validate source filename — no path separators, valid extension."""
    if "/" in filename or "\\" in filename:
        raise InvalidFile("Filename must not contain path separators")
    ext = Path(filename).suffix.lower()
    if ext not in _SOURCE_EXTENSIONS:
        raise InvalidFile(
            f"Extension '{ext}' not allowed. Allowed: {sorted(_SOURCE_EXTENSIONS)}"
        )
    if len(filename) > 255:
        raise InvalidFile("Filename too long")
