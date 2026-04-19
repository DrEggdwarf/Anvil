"""Tests for workspace file manager — per-session isolated directories."""

from __future__ import annotations

import os

import pytest

from backend.app.core.exceptions import InvalidFile
from backend.app.core.workspace import WorkspaceManager


@pytest.fixture
def wmgr(tmp_path):
    """WorkspaceManager with a temp base directory."""
    return WorkspaceManager(base_dir=str(tmp_path))


class TestCreateWorkspace:
    def test_creates_directory(self, wmgr, tmp_path):
        path = wmgr.create_workspace("session-1")
        assert os.path.isdir(path)
        assert "session-1" in path

    def test_idempotent(self, wmgr):
        p1 = wmgr.create_workspace("session-1")
        p2 = wmgr.create_workspace("session-1")
        assert p1 == p2

    def test_get_creates_if_missing(self, wmgr):
        path = wmgr.get_workspace("new-session")
        assert os.path.isdir(path)


class TestDestroyWorkspace:
    def test_removes_directory(self, wmgr):
        path = wmgr.create_workspace("session-1")
        assert wmgr.destroy_workspace("session-1") is True
        assert not os.path.exists(path)

    def test_nonexistent_returns_false(self, wmgr):
        assert wmgr.destroy_workspace("nonexistent") is False


class TestWriteSource:
    def test_write_and_read(self, wmgr):
        wmgr.create_workspace("s1")
        path = wmgr.write_source("s1", "hello.asm", "section .text\n")
        assert os.path.isfile(path)
        content = wmgr.read_source("s1", "hello.asm")
        assert content == "section .text\n"

    def test_overwrite(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.write_source("s1", "prog.asm", "v1")
        wmgr.write_source("s1", "prog.asm", "v2")
        assert wmgr.read_source("s1", "prog.asm") == "v2"

    def test_invalid_extension(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.write_source("s1", "malware.exe", "bad")

    def test_path_traversal_blocked(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.write_source("s1", "../../../etc/passwd.asm", "bad")

    def test_slash_in_filename_blocked(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.write_source("s1", "sub/dir.asm", "code")

    def test_allowed_extensions(self, wmgr):
        wmgr.create_workspace("s1")
        for ext in [".asm", ".s", ".c", ".h", ".py", ".ld"]:
            wmgr.write_source("s1", f"file{ext}", "content")


class TestReadSource:
    def test_file_not_found(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile, match="not found"):
            wmgr.read_source("s1", "nonexistent.asm")

    def test_path_traversal_blocked(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.read_source("s1", "../../etc/passwd")


class TestListFiles:
    def test_empty_workspace(self, wmgr):
        wmgr.create_workspace("s1")
        files = wmgr.list_files("s1")
        assert files == []

    def test_lists_files(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.write_source("s1", "hello.asm", "code")
        wmgr.write_source("s1", "util.c", "int x;")
        files = wmgr.list_files("s1")
        assert len(files) == 2
        names = {f["name"] for f in files}
        assert names == {"hello.asm", "util.c"}

    def test_file_metadata(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.write_source("s1", "test.asm", "hello")
        files = wmgr.list_files("s1")
        assert files[0]["name"] == "test.asm"
        assert files[0]["size"] == 5
        assert files[0]["is_binary"] is False


class TestDeleteFile:
    def test_delete_existing(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.write_source("s1", "file.asm", "code")
        assert wmgr.delete_file("s1", "file.asm") is True
        assert wmgr.list_files("s1") == []

    def test_delete_nonexistent(self, wmgr):
        wmgr.create_workspace("s1")
        assert wmgr.delete_file("s1", "nope.asm") is False

    def test_path_traversal_blocked(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.delete_file("s1", "../../../etc/passwd")


class TestCleanupAll:
    def test_cleanup(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.create_workspace("s2")
        wmgr.create_workspace("s3")
        count = wmgr.cleanup_all()
        assert count == 3

    def test_cleanup_empty(self, wmgr):
        assert wmgr.cleanup_all() == 0


class TestGetFilePath:
    def test_returns_path(self, wmgr):
        wmgr.create_workspace("s1")
        wmgr.write_source("s1", "prog.asm", "code")
        path = wmgr.get_file_path("s1", "prog.asm")
        assert path.endswith("prog.asm")
        assert os.path.isfile(path)

    def test_path_traversal_blocked(self, wmgr):
        wmgr.create_workspace("s1")
        with pytest.raises(InvalidFile):
            wmgr.get_file_path("s1", "../../etc/passwd")
