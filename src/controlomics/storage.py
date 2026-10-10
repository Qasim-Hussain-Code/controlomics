"""Replace local exports only after a complete write. No automatic persistence."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory


def require_new_directory(path: Path):
    """Never replace an existing directory, file, or final-component link."""
    try:
        Path(path).lstat()
    except FileNotFoundError:
        return
    raise ValueError("choose a new directory that does not already exist")


@contextmanager
def staged_directory(path: Path):
    """Prepare an owned directory before publishing it under a new name.

    Ordinary preparation failures leave the destination absent. Cleanup can fail
    or be interrupted; concurrent filesystem changes and power loss are outside
    this guarantee. Empty existing directories are also rejected.
    """
    path = Path(path).absolute()
    require_new_directory(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent, prefix=".controlomics_directory_") as temporary:
        staged = Path(temporary)
        yield staged
        require_new_directory(path)
        os.rename(staged, path)


def _copy_windows_dacl(source: Path, destination: Path):
    """Copy the discretionary ACL before writing sensitive staging content."""
    import ctypes
    from ctypes import wintypes

    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_security = security.GetNamedSecurityInfoW
    get_security.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD] + [ctypes.POINTER(ctypes.c_void_p)] * 5
    get_security.restype = wintypes.DWORD
    set_security = security.SetNamedSecurityInfoW
    set_security.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD] + [ctypes.c_void_p] * 4
    set_security.restype = wintypes.DWORD
    control_of = security.GetSecurityDescriptorControl
    control_of.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    control_of.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    descriptor, dacl = ctypes.c_void_p(), ctypes.c_void_p()
    # SE_FILE_OBJECT = 1; DACL_SECURITY_INFORMATION = 4.
    error = get_security(str(source), 1, 4, None, None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
    try:
        if error:
            raise OSError(error, "export access restrictions could not be read")
        control, revision = wintypes.WORD(), wintypes.DWORD()
        if not control_of(descriptor, ctypes.byref(control), ctypes.byref(revision)):
            raise OSError(ctypes.get_last_error(), "export access restrictions could not be read")
        # Preserve SE_DACL_PROTECTED; never fall back to a broader inherited ACL.
        information = 4 | (0x80000000 if control.value & 0x1000 else 0x20000000)
        error = set_security(str(destination), 1, information, None, None, dacl, None)
        if error:
            raise OSError(error, "export access restrictions could not be retained")
    finally:
        if descriptor.value:
            kernel.LocalFree(descriptor)


def write_bytes_atomic(path: Path, content: bytes):
    """Stage beside the destination, flush, then replace one regular file.

    This preserves the previous file on ordinary write or replacement failures.
    It does not provide a multi-file transaction or a power-loss guarantee.
    """
    path = Path(path)
    mode = None
    try:
        existing = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if not stat.S_ISREG(existing.st_mode):
            raise ValueError("export destination must be a regular file")
        if getattr(existing, "st_file_attributes", 0) & (0x4000 | 0x400 | 0x1):
            raise ValueError("encrypted, read-only, or reparse-point exports require a new ordinary destination")
        if os.name != "nt" and hasattr(os, "listxattr") and any(name in {"system.posix_acl_access", "com.apple.system.Security"} for name in os.listxattr(path)):
            raise ValueError("extended access-control exports require a new ordinary destination")
        mode = stat.S_IMODE(existing.st_mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".controlomics_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            if mode is not None:
                if os.name == "nt":
                    _copy_windows_dacl(path, temporary)
                else:
                    staged = temporary.stat()
                    if (staged.st_uid, staged.st_gid) != (existing.st_uid, existing.st_gid):
                        os.chown(temporary, existing.st_uid, existing.st_gid)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_text_atomic(path: Path, content: str):
    write_bytes_atomic(path, content.encode("utf-8"))


def require_distinct_outputs(*paths: Path):
    """Reject output aliases before writes or external transmission begin."""
    resolved = [Path(path).resolve() for path in paths]
    for index, left in enumerate(resolved):
        for right in resolved[index + 1:]:
            if left == right or left.exists() and right.exists() and left.samefile(right):
                raise ValueError("different outputs require distinct destinations")
