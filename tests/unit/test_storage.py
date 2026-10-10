import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.cli import main, write_json
from controlomics.project import load_project, parse_project_json, save_project
from controlomics.reports import write_report
from controlomics.storage import require_distinct_outputs, staged_directory, write_bytes_atomic
from tests.fixtures import ROOT, payload


class StorageTests(unittest.TestCase):
    def test_directory_publication_failure_and_interrupt_cleanup(self):
        with TemporaryDirectory() as temporary:
            root, target = Path(temporary), Path(temporary) / "complete"
            for failure in (OSError("synthetic write failure"), KeyboardInterrupt()):
                with self.assertRaises(type(failure)):
                    with staged_directory(target) as staged:
                        (staged / "first.json").write_bytes(b"synthetic only")
                        self.assertFalse(target.exists())
                        raise failure
                self.assertEqual(list(root.iterdir()), [])
            with patch("controlomics.storage.os.rename", side_effect=OSError("synthetic rename failure")), self.assertRaises(OSError):
                with staged_directory(target) as staged:
                    (staged / "first.json").write_bytes(b"synthetic only")
            self.assertEqual(list(root.iterdir()), [])
            with staged_directory(target) as staged:
                (staged / "first.json").write_bytes(b"complete")
                self.assertFalse(target.exists())
            self.assertEqual((target / "first.json").read_bytes(), b"complete")

    def test_existing_directories_and_concurrent_destination_are_preserved(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "retained"
            target.mkdir()
            with self.assertRaises(ValueError), staged_directory(target):
                pass
            self.assertEqual(list(target.iterdir()), [])
            (target / "retained.json").write_bytes(b"retained")
            with self.assertRaises(ValueError), staged_directory(target):
                pass
            new = target.parent / "new"
            with self.assertRaises(ValueError), staged_directory(new) as staged:
                (staged / "private.json").write_bytes(b"synthetic only")
                new.mkdir()
                (new / "other.json").write_bytes(b"retained")
            self.assertEqual((new / "other.json").read_bytes(), b"retained")
            self.assertFalse(list(target.parent.glob(".controlomics_directory_*")))

    def test_replacement_preserves_explicit_access_restrictions(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "restricted.json"
            target.write_bytes(b"retained original")
            if os.name == "nt":
                import ctypes
                import struct
                from ctypes import wintypes
                security = ctypes.WinDLL("advapi32", use_last_error=True)
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                convert = security.ConvertStringSecurityDescriptorToSecurityDescriptorW
                convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
                convert.restype = wintypes.BOOL
                setter = security.SetFileSecurityW
                setter.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
                setter.restype = wintypes.BOOL
                getter = security.GetFileSecurityW
                getter.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
                getter.restype = wintypes.BOOL
                kernel.LocalFree.argtypes = [ctypes.c_void_p]
                kernel.LocalFree.restype = ctypes.c_void_p
                descriptor = ctypes.c_void_p()
                # OW is the well-known Owner Rights SID, not a personal identity.
                self.assertTrue(convert("D:P(A;;FA;;;OW)", 1, ctypes.byref(descriptor), None))
                try:
                    self.assertTrue(setter(str(target), 4 | 0x80000000, descriptor))
                finally:
                    kernel.LocalFree(descriptor)

                def acl_snapshot():
                    needed = wintypes.DWORD()
                    getter(str(target), 4, None, 0, ctypes.byref(needed))
                    buffer = ctypes.create_string_buffer(needed.value)
                    self.assertTrue(getter(str(target), 4, buffer, len(buffer), ctypes.byref(needed)))
                    raw = buffer.raw
                    offset = struct.unpack_from("<I", raw, 16)[0]
                    size = struct.unpack_from("<H", raw, offset + 2)[0]
                    return bool(struct.unpack_from("<H", raw, 2)[0] & 0x1000), raw[offset:offset + size]

                before = acl_snapshot()
                write_bytes_atomic(target, b"complete replacement")
                self.assertTrue(acl_snapshot() == before, "Existing protected discretionary ACL changed")
            else:
                os.chmod(target, 0o640)
                before = target.stat()
                write_bytes_atomic(target, b"complete replacement")
                after = target.stat()
                self.assertEqual(after.st_mode & 0o777, 0o640)
                self.assertEqual((after.st_uid, after.st_gid), (before.st_uid, before.st_gid))
            self.assertEqual(target.read_bytes(), b"complete replacement")

    def test_access_restriction_failure_preserves_old_file(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "retained.json"
            target.write_bytes(b"retained original")
            operation = "_copy_windows_dacl" if os.name == "nt" else "os.chmod"
            with patch("controlomics.storage." + operation, side_effect=OSError("synthetic access failure")):
                with self.assertRaises(OSError):
                    write_bytes_atomic(target, b"new private_sentinel")
            self.assertEqual(target.read_bytes(), b"retained original")
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_complete_project_replacement_and_utf8_exports(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary) / "new"
            target = folder / "project.json"
            project = parse_project_json(json.dumps(payload()))
            save_project(project, target)
            self.assertEqual(load_project(target), project)
            save_project(project, target)
            self.assertEqual(load_project(target), project)
            write_json(folder / "unicode.json", {"text": "\u03bb"})
            self.assertEqual(json.loads((folder / "unicode.json").read_bytes())["text"], "\u03bb")
            write_report(project, folder / "report.html")
            self.assertIn(b"Controlomics scientific audit", (folder / "report.html").read_bytes())
            self.assertFalse(list(folder.glob(".controlomics_*.tmp")))

    def test_flush_and_replace_failures_preserve_existing_export(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "retained.json"
            target.write_bytes(b"retained original")
            for operation in ("os.fsync", "os.replace"):
                with self.subTest(operation=operation), patch("controlomics.storage." + operation, side_effect=OSError("synthetic failure")):
                    with self.assertRaises(OSError):
                        write_bytes_atomic(target, b"new private_sentinel")
                self.assertEqual(target.read_bytes(), b"retained original")
                self.assertEqual(list(target.parent.iterdir()), [target])

    def test_failed_new_export_leaves_no_partial_file(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "new.json"
            with patch("controlomics.storage.os.replace", side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError):
                    write_json(target, {"private_sentinel": "synthetic only"})
            self.assertEqual(list(target.parent.iterdir()), [])

    def test_nonregular_destinations_are_preserved(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with self.assertRaises(ValueError):
                write_bytes_atomic(folder, b"synthetic only")
            self.assertTrue(folder.is_dir())
            if os.name != "nt":
                original, link = folder / "original", folder / "link"
                original.write_bytes(b"retained")
                link.symlink_to(original)
                with self.assertRaises(ValueError):
                    write_bytes_atomic(link, b"changed")
                self.assertTrue(link.is_symlink())
                self.assertEqual(original.read_bytes(), b"retained")

    def test_distinct_outputs_reject_aliases_and_hard_links(self):
        if os.name == "nt":
            with TemporaryDirectory() as temporary:
                target = Path(temporary) / "read_only.json"
                target.write_bytes(b"retained")
                os.chmod(target, 0o400)
                try:
                    with self.assertRaises(ValueError):
                        write_bytes_atomic(target, b"new private_sentinel")
                    self.assertEqual(target.read_bytes(), b"retained")
                    self.assertEqual(list(target.parent.iterdir()), [target])
                finally:
                    os.chmod(target, 0o600)
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            first, second = folder / "first.json", folder / "second.json"
            require_distinct_outputs(first, second)
            with self.assertRaises(ValueError):
                require_distinct_outputs(first, folder / "child" / ".." / "first.json")
            first.write_bytes(b"retained")
            os.link(first, second)
            with self.assertRaises(ValueError):
                require_distinct_outputs(first, second)

    def test_conflicting_cli_sidecars_fail_before_reads_or_transmission(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()), patch("socket.create_connection", side_effect=AssertionError("Unexpected network")):
            target = Path(temporary) / "retained.json"
            target.write_bytes(b"private_sentinel")
            for arguments in (
                ["retrieve", str(ROOT / "examples" / "transcriptomics.project.json"), "--query", "public method", "--output", str(target), "--audit-output", str(target)],
                ["annotate", "absent.json", "absent.submission.json", "--output", str(target), "--revision-output", str(target)],
                ["annotate", str(target), "absent.submission.json", "--output", str(target.parent / "updated.json"), "--revision-output", str(target)],
                ["package", "absent.json", "--control-id", "fixture", "--config", "absent.config.json", "--directory", str(target.parent), "--output", str(target.parent / "stats.py")],
            ):
                self.assertEqual(main(arguments), 1)
                self.assertEqual(target.read_bytes(), b"private_sentinel")
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_cli_save_failure_is_redacted_and_retains_prior_project(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "retained.json"
            target.write_bytes(b"retained original")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch("controlomics.storage.os.replace", side_effect=OSError("private_sentinel")):
                self.assertEqual(main(["analyze", str(ROOT / "examples" / "transcriptomics.project.json"), "--output", str(target)]), 1)
            self.assertNotIn("private_sentinel", output.getvalue())
            self.assertNotIn(str(target), output.getvalue())
            self.assertEqual(target.read_bytes(), b"retained original")
