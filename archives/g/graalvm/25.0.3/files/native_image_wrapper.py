#!/usr/bin/env python3
"""Run Native Image with the required OpenHarmony build and finalization flags."""

import ctypes
import errno
import fcntl
import hashlib
import os
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


INFORMATIONAL_ARGUMENTS = {
    "--expert-options",
    "--expert-options-all",
    "--help",
    "--help-extra",
    "--version",
    "-h",
}
SANITIZED_ENVIRONMENT = {
    "JAVA_TOOL_OPTIONS",
    "JDK_JAVA_OPTIONS",
    "LD_LIBRARY_PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "_JAVA_OPTIONS",
}


class _ForwardedSignal(Exception):
    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


class _SignalExitState:
    def __init__(self):
        self.committed = False
        self.pending = None
        self.preserved_paths = set()

    def handle(self, signum):
        first_signal = self.pending is None
        if first_signal:
            self.pending = signum
        if first_signal and not self.committed:
            raise SystemExit(128 + signum)


@dataclass(frozen=True)
class _FileIdentity:
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    mode: int
    uid: int
    gid: int
    links: int
    sha256: str


@dataclass(frozen=True)
class _StagedOutput:
    path: Path
    directory_identity: tuple

    def __fspath__(self):
        return os.fspath(self.path)

    def __str__(self):
        return str(self.path)

    def __getattr__(self, name):
        return getattr(self.path, name)


@dataclass(frozen=True)
class _PrivateLock:
    path: Path
    descriptor: int
    identity: tuple
    parent_descriptor: int
    parent_identity: tuple


@dataclass(frozen=True)
class _LockedTemporaryDirectory:
    path: Path
    cwd_identity: tuple
    destination_parent_identity: tuple

    def __fspath__(self):
        return os.fspath(self.path)

    def __str__(self):
        return str(self.path)

    def __truediv__(self, name):
        return self.path / name

    def __eq__(self, other):
        return self.path == other

    def __getattr__(self, name):
        return getattr(self.path, name)


def _watched_signals():
    return tuple(
        signum
        for signum in (
            getattr(signal, "SIGHUP", None),
            signal.SIGINT,
            signal.SIGTERM,
        )
        if signum is not None
    )


def _java_home(wrapper):
    wrapper = Path(wrapper).resolve()
    if (
        wrapper.parent.parent.name == "svm"
        and wrapper.parent.parent.parent.name == "lib"
    ):
        return wrapper.parents[3]
    if wrapper.parent.name == "bin":
        return wrapper.parents[1]
    raise RuntimeError(f"cannot derive JAVA_HOME from {wrapper}")


def _is_elf(path):
    try:
        with Path(path).open("rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


def _resolve_for_policy(path):
    resolved_path = Path(os.path.abspath(path))
    resolved = Path(resolved_path.anchor)
    parts = list(resolved_path.parts[1:])
    seen = set()
    while parts:
        candidate = resolved / parts.pop(0)
        try:
            target = os.readlink(candidate)
        except OSError:
            resolved = candidate
            continue
        key = os.path.abspath(candidate)
        if key in seen or len(seen) >= 40:
            raise RuntimeError(f"Native Image path symlink loop: {path}")
        seen.add(key)
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = resolved / target_path
        combined = Path(os.path.abspath(target_path.joinpath(*parts)))
        resolved = Path(combined.anchor)
        parts = list(combined.parts[1:])
    return resolved


def _absolute_output(cwd, value):
    raw_cwd = Path(os.path.abspath(cwd))
    cwd = raw_cwd.resolve(strict=True)
    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    else:
        path = Path(os.path.abspath(path))
        try:
            path = cwd / path.relative_to(raw_cwd)
        except ValueError:
            pass
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        resolved_parent = _resolve_for_policy(path.parent)
        scratch = _resolve_for_policy(cwd / ".t")
        if resolved_parent == scratch or scratch in resolved_parent.parents:
            return resolved_parent / path.name
        raise RuntimeError(
            f"Native Image output directory is missing: {path.parent}"
        ) from exc
    return parent / path.name


def _lock_path(directory):
    return directory / ".graalvm-native-image.lock"


def _canonical_lock_path(directory):
    return Path(directory).resolve(strict=True) / ".graalvm-native-image.lock"


def _require_safe_destination(path, cwd):
    resolved = _resolve_for_policy(path)
    scratch = _resolve_for_policy(Path(cwd).resolve(strict=True) / ".t")
    if resolved == scratch or scratch in resolved.parents:
        raise RuntimeError(f"Native Image output must not use scratch path: {path}")
    lock_paths = {
        _lock_path(cwd).resolve(strict=False),
        _lock_path(path.parent).resolve(strict=False),
    }
    if resolved in lock_paths:
        raise RuntimeError(f"Native Image output must not replace a lock: {path}")
    if path.name == "libg.so":
        raise RuntimeError(f"Native Image output must not be named libg.so: {path}")


def _explicit_output(arguments, cwd):
    outputs = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ("-o", "--output"):
            if index + 1 >= len(arguments):
                raise RuntimeError(f"{argument} requires an output path")
            outputs.append((arguments[index + 1], index + 1, ""))
            index += 2
            continue
        elif argument.startswith("--output="):
            outputs.append((argument.split("=", 1)[1], index, "--output="))
        elif argument.startswith("-o="):
            outputs.append((argument[3:], index, "-o="))
        elif argument.startswith("-o") and len(argument) > 2:
            outputs.append((argument[2:], index, "-o"))
        index += 1
    if len(outputs) > 1:
        raise RuntimeError("Native Image output path is specified more than once")
    if not outputs:
        return None, None
    output, output_index, prefix = outputs[0]
    if not output:
        raise RuntimeError("Native Image output path is empty")
    return _absolute_output(cwd, output), (output_index, prefix)


def _replace_explicit_output(arguments, location, replacement):
    replaced = list(arguments)
    index, prefix = location
    replaced[index] = f"{prefix}{replacement}"
    return replaced


def _destination_identity(path):
    if not os.path.lexists(path):
        return None
    path_status = os.lstat(path)
    if stat.S_ISLNK(path_status.st_mode):
        raise RuntimeError(f"Native Image output must not be a symlink: {path}")
    if not stat.S_ISREG(path_status.st_mode):
        raise RuntimeError(f"Native Image output is not a regular file: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(
            f"Native Image output cannot be opened safely: {path}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"Native Image output is not a regular file: {path}")
        if (before.st_dev, before.st_ino) != (
            path_status.st_dev,
            path_status.st_ino,
        ):
            raise RuntimeError(f"Native Image output changed while opening: {path}")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
        )
        if any(
            getattr(before, name) != getattr(after, name)
            for name in stable_fields
        ):
            raise RuntimeError(f"Native Image output changed while hashing: {path}")
        return _FileIdentity(
            device=after.st_dev,
            inode=after.st_ino,
            size=after.st_size,
            mtime_ns=after.st_mtime_ns,
            ctime_ns=after.st_ctime_ns,
            mode=after.st_mode,
            uid=after.st_uid,
            gid=after.st_gid,
            links=after.st_nlink,
            sha256=digest.hexdigest(),
        )
    finally:
        os.close(descriptor)


def _require_unchanged_destination(path, identity):
    current = _destination_identity(path)
    if current != identity:
        raise RuntimeError(
            f"Native Image output changed during finalization: {path}"
        )


def _destination_identity_at(directory_descriptor, name, path):
    try:
        path_status = os.stat(
            name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(path_status.st_mode):
        raise RuntimeError(f"Native Image output must not be a symlink: {path}")
    if not stat.S_ISREG(path_status.st_mode):
        raise RuntimeError(f"Native Image output is not a regular file: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise RuntimeError(
            f"Native Image output cannot be opened safely: {path}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"Native Image output is not a regular file: {path}")
        if (before.st_dev, before.st_ino) != (
            path_status.st_dev,
            path_status.st_ino,
        ):
            raise RuntimeError(f"Native Image output changed while opening: {path}")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
        )
        if any(
            getattr(before, field) != getattr(after, field)
            for field in stable_fields
        ):
            raise RuntimeError(f"Native Image output changed while hashing: {path}")
        return _FileIdentity(
            device=after.st_dev,
            inode=after.st_ino,
            size=after.st_size,
            mtime_ns=after.st_mtime_ns,
            ctime_ns=after.st_ctime_ns,
            mode=after.st_mode,
            uid=after.st_uid,
            gid=after.st_gid,
            links=after.st_nlink,
            sha256=digest.hexdigest(),
        )
    finally:
        os.close(descriptor)


def _require_unchanged_destination_at(directory_descriptor, name, path, identity):
    current = _destination_identity_at(directory_descriptor, name, path)
    if current != identity:
        raise RuntimeError(
            f"Native Image output changed during finalization: {path}"
        )


def _same_content_identity(left, right):
    return (
        left is not None
        and right is not None
        and left.size == right.size
        and left.sha256 == right.sha256
    )


def _same_preserved_identity(left, right):
    if left is None or right is None:
        return False
    return (
        left.device,
        left.inode,
        left.size,
        left.mtime_ns,
        left.mode,
        left.uid,
        left.gid,
        left.links,
        left.sha256,
    ) == (
        right.device,
        right.inode,
        right.size,
        right.mtime_ns,
        right.mode,
        right.uid,
        right.gid,
        right.links,
        right.sha256,
    )


def _require_trusted_regular_identity(path, identity, expected_sha, description):
    if identity is None:
        raise RuntimeError(f"{description} is missing: {path}")
    permissions = stat.S_IMODE(identity.mode)
    authorized_groups = {os.getegid(), *os.getgroups()}
    trusted_owner = identity.uid == os.geteuid()
    trusted_group = identity.gid in authorized_groups
    if not trusted_owner and not trusted_group:
        raise RuntimeError(f"{description} is not owned by a trusted principal: {path}")
    if identity.links != 1:
        raise RuntimeError(f"{description} must not be hard-linked: {path}")
    if permissions & 0o002:
        raise RuntimeError(f"{description} must not be writable by others: {path}")
    if permissions & 0o020 and not trusted_group:
        raise RuntimeError(
            f"{description} group write is not trusted for gid {identity.gid}: {path}"
        )
    if expected_sha is not None and identity.sha256 != expected_sha:
        raise RuntimeError(f"{description} hash mismatch: {path}")


def _renameat2(
    source,
    target,
    flags,
    source_dir_fd=-100,
    target_dir_fd=-100,
):
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, "renameat2", None)
    if function is None:
        raise RuntimeError("Native Image requires renameat2")
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    result = function(
        source_dir_fd,
        os.fsencode(source),
        target_dir_fd,
        os.fsencode(target),
        flags,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise FileExistsError(error, os.strerror(error), target)
    raise OSError(error, os.strerror(error), target)


def _rename_noreplace(source, target):
    _renameat2(source, target, 1)


def _rename_exchange(left, right):
    _renameat2(left, right, 2)


def _rename_noreplace_at(source_dir_fd, source_name, target_dir_fd, target_name):
    _renameat2(source_name, target_name, 1, source_dir_fd, target_dir_fd)


def _rename_exchange_at(left_dir_fd, left_name, right_dir_fd, right_name):
    _renameat2(left_name, right_name, 2, left_dir_fd, right_dir_fd)


def _unique_sibling(path, label):
    path = Path(path)
    for _attempt in range(16):
        candidate = path.with_name(
            f".{path.name}.graalvm-ohos-{label}-{secrets.token_hex(16)}"
        )
        if not os.path.lexists(candidate):
            return candidate
    raise RuntimeError(f"cannot reserve Native Image {label} path beside {path}")


def _preserve_stage(path, signal_state, reason):
    directory = Path(path).parent
    signal_state.preserved_paths.add(directory)
    print(
        f"Native Image preserved transaction stage {directory}: {reason}",
        file=sys.stderr,
    )


def _move_back_noreplace(source, target, expected, signal_state, description):
    current = _destination_identity(source)
    if not _same_preserved_identity(current, expected):
        raise RuntimeError(f"{description} changed before rollback")
    try:
        _rename_noreplace(source, target)
    except BaseException:
        _preserve_stage(target, signal_state, f"cannot move back {description}")
        raise
    moved = _destination_identity(target)
    if _same_preserved_identity(moved, expected):
        return
    try:
        _rename_noreplace(target, source)
        restored = _destination_identity(source)
        if not _same_preserved_identity(restored, moved):
            raise RuntimeError(f"cannot verify restored {description}")
    except BaseException:
        _preserve_stage(target, signal_state, f"changed {description}")
        raise
    raise RuntimeError(f"{description} changed during rollback")


def _exchange_back_unflushed(
    staged,
    destination,
    expected_destination,
    expected_staged,
    signal_state,
    description,
):
    quarantine = _unique_sibling(staged, "quarantine")
    try:
        _rename_noreplace(destination, quarantine)
    except BaseException:
        _preserve_stage(staged, signal_state, f"cannot quarantine {description}")
        raise

    quarantined_identity = _destination_identity(quarantine)
    if not _same_preserved_identity(quarantined_identity, expected_staged):
        try:
            _move_back_noreplace(
                quarantine,
                destination,
                quarantined_identity,
                signal_state,
                description,
            )
        finally:
            _preserve_stage(staged, signal_state, f"changed {description}")
        raise RuntimeError(f"{description} changed before rollback")

    current_staged = _destination_identity(staged)
    if not _same_preserved_identity(current_staged, expected_destination):
        try:
            _move_back_noreplace(
                quarantine,
                destination,
                quarantined_identity,
                signal_state,
                description,
            )
        finally:
            _preserve_stage(staged, signal_state, f"changed old {description}")
        raise RuntimeError(f"old {description} changed before rollback")

    try:
        _rename_noreplace(staged, destination)
    except BaseException:
        _preserve_stage(staged, signal_state, f"cannot restore old {description}")
        raise
    restored_identity = _destination_identity(destination)
    if not _same_preserved_identity(restored_identity, expected_destination):
        _preserve_stage(staged, signal_state, f"changed restored {description}")
        raise RuntimeError(f"old {description} changed during rollback")

    try:
        _rename_noreplace(quarantine, staged)
    except BaseException:
        _preserve_stage(staged, signal_state, f"cannot retain new {description}")
        raise
    retained_identity = _destination_identity(staged)
    if not _same_preserved_identity(retained_identity, expected_staged):
        _preserve_stage(staged, signal_state, f"changed retained {description}")
        raise RuntimeError(f"new {description} changed during rollback")


def _exchange_back(
    staged,
    destination,
    expected_destination,
    expected_staged,
    signal_state,
    description,
):
    try:
        return _exchange_back_unflushed(
            staged,
            destination,
            expected_destination,
            expected_staged,
            signal_state,
            description,
        )
    finally:
        _fsync_directory(Path(destination).parent)


def _directory_identity(path):
    if not os.path.lexists(path):
        return None
    status = os.lstat(path)
    if not stat.S_ISDIR(status.st_mode) or stat.S_ISLNK(status.st_mode):
        raise RuntimeError(f"Native Image temporary path is not a directory: {path}")
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
    )


def _directory_identity_from_status(status):
    if not stat.S_ISDIR(status.st_mode):
        raise RuntimeError("Native Image directory descriptor is not a directory")
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
    )


def _directory_fd_identity(descriptor):
    return _directory_identity_from_status(os.fstat(descriptor))


def _open_directory_descriptor(path, expected_identity, description):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        identity = _directory_fd_identity(descriptor)
        if expected_identity is not None and identity != expected_identity:
            raise RuntimeError(f"{description} changed after finalization: {path}")
        path_identity = _directory_identity(path)
        if path_identity != identity:
            raise RuntimeError(f"{description} changed while opening: {path}")
        return descriptor, identity
    except BaseException:
        os.close(descriptor)
        raise


def _require_directory_path_identity(path, expected_identity, description):
    if _directory_identity(path) != expected_identity:
        raise RuntimeError(f"{description} changed during finalization: {path}")


def _fsync_directory_descriptor(descriptor):
    os.fsync(descriptor)


def _move_back_noreplace_at(
    source_dir_fd,
    source_name,
    source_path,
    target_dir_fd,
    target_name,
    target_path,
    expected,
    signal_state,
    description,
):
    current = _destination_identity_at(source_dir_fd, source_name, source_path)
    if not _same_preserved_identity(current, expected):
        raise RuntimeError(f"{description} changed before rollback")
    try:
        _rename_noreplace_at(source_dir_fd, source_name, target_dir_fd, target_name)
    except BaseException:
        _preserve_stage(target_path, signal_state, f"cannot move back {description}")
        raise
    moved = _destination_identity_at(target_dir_fd, target_name, target_path)
    if _same_preserved_identity(moved, expected):
        return
    try:
        _rename_noreplace_at(target_dir_fd, target_name, source_dir_fd, source_name)
        restored = _destination_identity_at(source_dir_fd, source_name, source_path)
        if not _same_preserved_identity(restored, moved):
            raise RuntimeError(f"cannot verify restored {description}")
    except BaseException:
        _preserve_stage(target_path, signal_state, f"changed {description}")
        raise
    raise RuntimeError(f"{description} changed during rollback")


def _exchange_back_at(
    staged_dir_fd,
    staged_name,
    staged_path,
    destination_dir_fd,
    destination_name,
    destination_path,
    expected_destination,
    expected_staged,
    signal_state,
    description,
):
    current_destination = _destination_identity_at(
        destination_dir_fd,
        destination_name,
        destination_path,
    )
    if not _same_preserved_identity(current_destination, expected_staged):
        _preserve_stage(staged_path, signal_state, f"changed {description}")
        raise RuntimeError(f"{description} changed before rollback")
    current_staged = _destination_identity_at(staged_dir_fd, staged_name, staged_path)
    if not _same_preserved_identity(current_staged, expected_destination):
        _preserve_stage(staged_path, signal_state, f"changed old {description}")
        raise RuntimeError(f"old {description} changed before rollback")
    try:
        _rename_exchange_at(
            staged_dir_fd,
            staged_name,
            destination_dir_fd,
            destination_name,
        )
    except BaseException:
        _preserve_stage(staged_path, signal_state, f"cannot restore old {description}")
        raise
    restored = _destination_identity_at(
        destination_dir_fd,
        destination_name,
        destination_path,
    )
    retained = _destination_identity_at(staged_dir_fd, staged_name, staged_path)
    if not _same_preserved_identity(restored, expected_destination):
        _preserve_stage(staged_path, signal_state, f"changed restored {description}")
        raise RuntimeError(f"old {description} changed during rollback")
    if not _same_preserved_identity(retained, expected_staged):
        _preserve_stage(staged_path, signal_state, f"changed retained {description}")
        raise RuntimeError(f"new {description} changed during rollback")
    _fsync_directory_descriptor(destination_dir_fd)


def _move_directory_back_noreplace(source, target, expected, signal_state, description):
    try:
        _rename_noreplace(source, target)
    except BaseException:
        signal_state.preserved_paths.add(Path(source))
        raise
    moved = _directory_identity(target)
    if moved == expected:
        return
    try:
        _rename_noreplace(target, source)
        if _directory_identity(source) != moved:
            raise RuntimeError(f"cannot verify restored {description}")
    except BaseException:
        signal_state.preserved_paths.add(Path(source))
        raise
    raise RuntimeError(f"{description} changed during cleanup quarantine")


def _clear_directory_fd(descriptor):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    with os.scandir(descriptor) as entries:
        for entry in entries:
            name = entry.name
            status = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(status.st_mode) and not stat.S_ISLNK(status.st_mode):
                child = os.open(name, flags, dir_fd=descriptor)
                try:
                    child_status = os.fstat(child)
                    if not os.path.samestat(status, child_status):
                        raise RuntimeError(
                            f"Native Image cleanup child changed: {name}"
                        )
                    _clear_directory_fd(child)
                    current = os.stat(
                        name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                    if not os.path.samestat(current, child_status):
                        raise RuntimeError(
                            f"Native Image cleanup child changed: {name}"
                        )
                    os.rmdir(name, dir_fd=descriptor)
                finally:
                    os.close(child)
            else:
                os.unlink(name, dir_fd=descriptor)


def _cleanup_tree(path, expected_identity, signal_state, description):
    if path is None:
        return
    path = Path(path)
    if path in signal_state.preserved_paths:
        print(
            f"Native Image retained {description} for recovery: {path}",
            file=sys.stderr,
        )
        return
    previous_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK, set(_watched_signals())
    )
    cleanup_error = None
    quarantine = None
    try:
        if os.path.lexists(path):
            quarantine = _unique_sibling(path, "cleanup")
            _rename_noreplace(path, quarantine)
            moved_identity = _directory_identity(quarantine)
            if moved_identity != expected_identity:
                _move_directory_back_noreplace(
                    quarantine,
                    path,
                    moved_identity,
                    signal_state,
                    description,
                )
                raise RuntimeError(
                    f"Native Image {description} path changed before cleanup: {path}"
                )

            flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                flags |= os.O_DIRECTORY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            if hasattr(os, "O_CLOEXEC"):
                flags |= os.O_CLOEXEC
            descriptor = os.open(quarantine, flags)
            try:
                status = os.fstat(descriptor)
                actual_identity = (
                    status.st_dev,
                    status.st_ino,
                    status.st_mode,
                    status.st_uid,
                    status.st_gid,
                )
                if actual_identity != expected_identity:
                    raise RuntimeError(
                        f"Native Image {description} changed while opening cleanup fd"
                    )
                _clear_directory_fd(descriptor)
                if _directory_identity(quarantine) != expected_identity:
                    raise RuntimeError(
                        f"Native Image {description} changed during fd cleanup"
                    )
            finally:
                os.close(descriptor)
            os.rmdir(quarantine)
    except (OSError, RuntimeError) as exc:
        if quarantine is not None and os.path.lexists(quarantine):
            signal_state.preserved_paths.add(quarantine)
        cleanup_error = exc
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    if cleanup_error is not None:
        if signal_state.committed:
            print(
                f"Native Image committed with {description} cleanup warning: "
                f"{cleanup_error}",
                file=sys.stderr,
            )
        else:
            raise cleanup_error


@contextmanager
def _staged_output(path, signal_state, parent_identity=None):
    if not path.parent.is_dir():
        raise RuntimeError(
            f"Native Image output directory is missing: {path.parent}"
        )
    if parent_identity is not None:
        _require_directory_path_identity(
            path.parent,
            parent_identity,
            "Native Image output directory",
        )
    staging = None
    staging_identity = None
    try:
        previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, set(_watched_signals())
        )
        try:
            staging = Path(
                tempfile.mkdtemp(
                    prefix=f".{path.name}.graalvm-ohos-stage-",
                    dir=path.parent,
                )
            )
            if parent_identity is not None:
                _require_directory_path_identity(
                    path.parent,
                    parent_identity,
                    "Native Image output directory",
                )
            staging_identity = _directory_identity(staging)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        yield _StagedOutput(staging / path.name, staging_identity)
    finally:
        _cleanup_tree(staging, staging_identity, signal_state, "output stage")


def _fsync_directory(path):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_file(path):
    flags = os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RuntimeError(f"Native Image staged file is not regular: {path}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def _staged_libg(source, directory, expected_sha, signal_state, parent_identity=None):
    if parent_identity is not None:
        _require_directory_path_identity(
            directory,
            parent_identity,
            "Native Image output directory",
        )
    staging = None
    staging_identity = None
    try:
        previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, set(_watched_signals())
        )
        try:
            staging = Path(
                tempfile.mkdtemp(
                    prefix=".libg.so.graalvm-ohos-stage-", dir=directory
                )
            )
            if parent_identity is not None:
                _require_directory_path_identity(
                    directory,
                    parent_identity,
                    "Native Image output directory",
                )
            staging_identity = _directory_identity(staging)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        target = staging / "libg.so"
        shutil.copy2(source, target)
        os.chmod(target, source.stat().st_mode & 0o777 or 0o755)
        if _sha256(target) != expected_sha:
            raise RuntimeError("staged Native Image libg.so hash mismatch")
        _fsync_file(target)
        yield target
    finally:
        _cleanup_tree(staging, staging_identity, signal_state, "libg.so stage")


def _commit_output(
    staged,
    destination,
    destination_identity,
    staged_libg,
    libg_sha,
    signal_state,
    finalized_sha256,
    destination_parent_identity_expected=None,
):
    if isinstance(staged, _StagedOutput):
        staged_directory_identity = staged.directory_identity
        staged = staged.path
    else:
        staged_directory_identity = None
    previous_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK, set(_watched_signals())
    )
    libg_target = destination.parent / "libg.so"
    opened_descriptors = []
    staged_parent_descriptor = None
    staged_libg_parent_descriptor = None
    destination_parent_descriptor = None
    destination_parent_identity = None
    staged_identity = None
    staged_libg_identity = None
    target_mode = None
    libg_created = False
    libg_identity = None
    try:
        staged_parent_descriptor, _staged_parent_identity = (
            _open_directory_descriptor(
                staged.parent,
                staged_directory_identity,
                "Native Image output stage",
            )
        )
        opened_descriptors.append(staged_parent_descriptor)
        staged_libg_parent_descriptor, _staged_libg_parent_identity = (
            _open_directory_descriptor(
                staged_libg.parent,
                _directory_identity(staged_libg.parent),
                "Native Image libg.so stage",
            )
        )
        opened_descriptors.append(staged_libg_parent_descriptor)
        if destination_parent_identity_expected is None:
            destination_parent_identity_expected = _directory_identity(destination.parent)
        destination_parent_descriptor, destination_parent_identity = (
            _open_directory_descriptor(
                destination.parent,
                destination_parent_identity_expected,
                "Native Image output directory",
            )
        )
        opened_descriptors.append(destination_parent_descriptor)

        staged_identity = _destination_identity_at(
            staged_parent_descriptor,
            staged.name,
            staged,
        )
        staged_libg_identity = _destination_identity_at(
            staged_libg_parent_descriptor,
            staged_libg.name,
            staged_libg,
        )
        _require_trusted_regular_identity(
            staged,
            staged_identity,
            finalized_sha256,
            "finalized Native Image output",
        )
        _require_trusted_regular_identity(
            staged_libg,
            staged_libg_identity,
            libg_sha,
            "staged Native Image libg.so",
        )

        _require_unchanged_destination_at(
            destination_parent_descriptor,
            destination.name,
            destination,
            destination_identity,
        )
        _require_directory_path_identity(
            destination.parent,
            destination_parent_identity,
            "Native Image output directory",
        )

        libg_identity = _destination_identity_at(
            destination_parent_descriptor,
            libg_target.name,
            libg_target,
        )
        if libg_identity is not None:
            _require_trusted_regular_identity(
                libg_target,
                libg_identity,
                libg_sha,
                "existing Native Image libg.so",
            )
        else:
            try:
                _rename_noreplace_at(
                    staged_libg_parent_descriptor,
                    staged_libg.name,
                    destination_parent_descriptor,
                    libg_target.name,
                )
            except FileExistsError as exc:
                raise RuntimeError(
                    f"libg.so appeared during Native Image commit: {libg_target}"
                ) from exc
            libg_created = True
            libg_identity = _destination_identity_at(
                destination_parent_descriptor,
                libg_target.name,
                libg_target,
            )
            _require_trusted_regular_identity(
                libg_target,
                libg_identity,
                libg_sha,
                "published Native Image libg.so",
            )
            if not _same_preserved_identity(
                libg_identity, staged_libg_identity
            ):
                raise RuntimeError(
                    f"published Native Image libg.so identity mismatch: {libg_target}"
                )
            _fsync_directory_descriptor(destination_parent_descriptor)
            _require_directory_path_identity(
                destination.parent,
                destination_parent_identity,
                "Native Image output directory",
            )

        _require_unchanged_destination_at(
            destination_parent_descriptor,
            destination.name,
            destination,
            destination_identity,
        )
        _require_directory_path_identity(
            destination.parent,
            destination_parent_identity,
            "Native Image output directory",
        )
        if destination_identity is None:
            try:
                _rename_noreplace_at(
                    staged_parent_descriptor,
                    staged.name,
                    destination_parent_descriptor,
                    destination.name,
                )
            except FileExistsError as exc:
                raise RuntimeError(
                    f"Native Image output appeared during commit: {destination}"
                ) from exc
            target_mode = "noreplace"
        else:
            _rename_exchange_at(
                staged_parent_descriptor,
                staged.name,
                destination_parent_descriptor,
                destination.name,
            )
            target_mode = "exchange"
            displaced_identity = _destination_identity_at(
                staged_parent_descriptor,
                staged.name,
                staged,
            )
            if not _same_preserved_identity(
                displaced_identity, destination_identity
            ):
                try:
                    _exchange_back_at(
                        staged_parent_descriptor,
                        staged.name,
                        staged,
                        destination_parent_descriptor,
                        destination.name,
                        destination,
                        displaced_identity,
                        staged_identity,
                        signal_state,
                        "Native Image output",
                    )
                finally:
                    target_mode = None
                raise RuntimeError(
                    f"Native Image output changed during finalization: {destination}"
                )

        _fsync_directory_descriptor(destination_parent_descriptor)
        _require_directory_path_identity(
            destination.parent,
            destination_parent_identity,
            "Native Image output directory",
        )
        current_identity = _destination_identity_at(
            destination_parent_descriptor,
            destination.name,
            destination,
        )
        if not _same_preserved_identity(current_identity, staged_identity):
            raise RuntimeError("installed Native Image identity changed during commit")
        if (
            _destination_identity_at(
                destination_parent_descriptor,
                libg_target.name,
                libg_target,
            )
            != libg_identity
        ):
            raise RuntimeError(
                f"Native Image libg.so changed during commit: {libg_target}"
            )
        signal_state.committed = True
        return
    except BaseException:
        rollback_error = None
        rolled_back = False
        try:
            if target_mode == "exchange":
                _exchange_back_at(
                    staged_parent_descriptor,
                    staged.name,
                    staged,
                    destination_parent_descriptor,
                    destination.name,
                    destination,
                    destination_identity,
                    staged_identity,
                    signal_state,
                    "Native Image output",
                )
                rolled_back = True
            elif target_mode == "noreplace":
                _move_back_noreplace_at(
                    destination_parent_descriptor,
                    destination.name,
                    destination,
                    staged_parent_descriptor,
                    staged.name,
                    staged,
                    staged_identity,
                    signal_state,
                    "Native Image output",
                )
                rolled_back = True
        except BaseException as exc:
            rollback_error = exc
        try:
            if libg_created:
                _move_back_noreplace_at(
                    destination_parent_descriptor,
                    libg_target.name,
                    libg_target,
                    staged_libg_parent_descriptor,
                    staged_libg.name,
                    staged_libg,
                    staged_libg_identity,
                    signal_state,
                    "Native Image libg.so",
                )
                rolled_back = True
        except BaseException as exc:
            rollback_error = rollback_error or exc
        try:
            if rolled_back:
                _fsync_directory_descriptor(destination_parent_descriptor)
        except BaseException as exc:
            rollback_error = rollback_error or exc
        if rollback_error is not None:
            raise RuntimeError("Native Image transaction rollback failed") from rollback_error
        raise
    finally:
        for descriptor in reversed(opened_descriptors):
            os.close(descriptor)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def _validate_output(path):
    if not os.path.lexists(path):
        raise RuntimeError(f"Native Image did not create explicit output: {path}")
    if path.is_symlink():
        raise RuntimeError(
            f"Native Image output must not be a symlink: {path}"
        )
    if not path.is_file():
        raise RuntimeError(f"Native Image output is not a regular file: {path}")
    if not _is_elf(path):
        raise RuntimeError(f"Native Image output is not an ELF: {path}")
    return path


@contextmanager
def _signal_exit_guard():
    watched = _watched_signals()
    previous_handlers = {signum: signal.getsignal(signum) for signum in watched}
    state = _SignalExitState()

    def stop(signum, _frame):
        state.handle(signum)

    for signum in watched:
        signal.signal(signum, stop)
    try:
        yield state
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def _open_private_lock(lock_path):
    lock_path = Path(lock_path)
    parent = lock_path.parent.resolve(strict=True)
    parent_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        parent_flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        parent_flags |= os.O_CLOEXEC
    parent_descriptor = os.open(parent, parent_flags)
    parent_identity = None
    flags = os.O_RDONLY | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        parent_identity = _directory_fd_identity(parent_descriptor)
        if _directory_identity(parent) != parent_identity:
            raise RuntimeError(
                f"Native Image lock directory changed while opening: {parent}"
            )
        descriptor = os.open(lock_path.name, flags, 0o660, dir_fd=parent_descriptor)
    except BaseException:
        os.close(parent_descriptor)
        raise
    try:
        lock_status = os.fstat(descriptor)
        path_status = os.stat(
            lock_path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        permissions = stat.S_IMODE(lock_status.st_mode)
        authorized_groups = {os.getegid(), *os.getgroups()}
        if (
            not stat.S_ISREG(lock_status.st_mode)
            or lock_status.st_nlink != 1
            or not (
                lock_status.st_uid == os.geteuid()
                or lock_status.st_gid in authorized_groups
            )
            or (permissions & ~0o660) != 0
            or (permissions & 0o007) != 0
            or (permissions & 0o600) != 0o600
            or (lock_status.st_dev, lock_status.st_ino)
            != (path_status.st_dev, path_status.st_ino)
        ):
            raise RuntimeError(
                f"Native Image lock is not a trusted regular file: {lock_path}"
            )
    except BaseException:
        os.close(descriptor)
        os.close(parent_descriptor)
        raise
    return _PrivateLock(
        path=lock_path,
        descriptor=descriptor,
        identity=(lock_status.st_dev, lock_status.st_ino),
        parent_descriptor=parent_descriptor,
        parent_identity=parent_identity,
    )


@contextmanager
def _locked_temporary_directory(cwd, destination, signal_state):
    lock_paths = sorted(
        {
            _canonical_lock_path(cwd),
            _canonical_lock_path(destination.parent),
        },
        key=lambda path: os.fsencode(path),
    )
    locks = []
    locked_locks = []
    locked_directory_identities = {}
    temporary = cwd / ".t"
    temporary_active = False
    temporary_identity = None
    try:
        for lock_path in lock_paths:
            previous_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK, set(_watched_signals())
            )
            try:
                lock = _open_private_lock(lock_path)
                locks.append(lock)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            fcntl.flock(lock.descriptor, fcntl.LOCK_EX)
            locked_locks.append(lock)
            path_status = os.stat(
                lock.path.name,
                dir_fd=lock.parent_descriptor,
                follow_symlinks=False,
            )
            if lock.identity != (path_status.st_dev, path_status.st_ino):
                raise RuntimeError(
                    f"Native Image lock changed while locking: {lock_path}"
                )
            if _directory_identity(lock.path.parent) != lock.parent_identity:
                raise RuntimeError(
                    "Native Image lock directory changed while locking: "
                    f"{lock.path.parent}"
                )
            locked_directory_identities[lock.path.parent] = lock.parent_identity

        cwd_identity = locked_directory_identities[Path(cwd).resolve(strict=True)]
        destination_parent_identity = locked_directory_identities[
            Path(destination.parent).resolve(strict=True)
        ]
        _require_directory_path_identity(
            cwd,
            cwd_identity,
            "Native Image working directory",
        )
        _require_directory_path_identity(
            destination.parent,
            destination_parent_identity,
            "Native Image output directory",
        )
        if os.path.lexists(temporary):
            temporary_status = os.lstat(temporary)
            if (
                not stat.S_ISDIR(temporary_status.st_mode)
                or temporary_status.st_uid != os.geteuid()
                or stat.S_IMODE(temporary_status.st_mode) & 0o077
            ):
                raise RuntimeError(
                    "Native Image scratch path is not a private owned "
                    f"directory: {temporary}"
                )
            raise RuntimeError(
                "Native Image scratch path already exists; refusing to remove: "
                f"{temporary}"
            )
        previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, set(_watched_signals())
        )
        try:
            temporary.mkdir(mode=0o700)
            _require_directory_path_identity(
                cwd,
                cwd_identity,
                "Native Image working directory",
            )
            temporary_identity = _directory_identity(temporary)
            temporary_active = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        yield _LockedTemporaryDirectory(
            path=temporary,
            cwd_identity=cwd_identity,
            destination_parent_identity=destination_parent_identity,
        )
    finally:
        cleanup_error = None
        try:
            if temporary_active and os.path.lexists(temporary):
                _cleanup_tree(
                    temporary,
                    temporary_identity,
                    signal_state,
                    "scratch",
                )
        except BaseException as exc:
            cleanup_error = exc
        finally:
            for lock in reversed(locked_locks):
                fcntl.flock(lock.descriptor, fcntl.LOCK_UN)
            for lock in reversed(locks):
                os.close(lock.descriptor)
                os.close(lock.parent_descriptor)
        if cleanup_error is not None:
            raise cleanup_error


def _run_driver(command, environment):
    watched = _watched_signals()
    process = None
    pending_signals = []
    previous_handlers = {signum: signal.getsignal(signum) for signum in watched}

    def forward(signum, _frame):
        if not pending_signals:
            pending_signals.append(signum)
        if process is not None:
            if process.poll() is not None:
                return
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                if process.poll() is not None:
                    return
            raise _ForwardedSignal(signum)

    for signum in watched:
        signal.signal(signum, forward)
    try:
        try:
            process = subprocess.Popen(
                command,
                env=environment,
                start_new_session=True,
            )
            if pending_signals:
                try:
                    os.killpg(process.pid, pending_signals[0])
                except ProcessLookupError:
                    pass
                raise _ForwardedSignal(pending_signals[0])
            returncode = process.wait()
            if pending_signals:
                return 128 + pending_signals[0]
        except _ForwardedSignal as interrupted:
            for signum in watched:
                signal.signal(signum, signal.SIG_IGN)
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
            return 128 + interrupted.signum
        return 128 - returncode if returncode < 0 else returncode
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def _create_compiler_launcher(temporary, launcher_binary):
    launcher = temporary / "ohos-clang"
    if not _is_elf(launcher_binary):
        raise SystemExit(f"Native Image launcher binary is missing: {launcher_binary}")
    shutil.copy2(launcher_binary, launcher)
    os.chmod(launcher, 0o700)
    return launcher


def main():
    wrapper = Path(__file__).resolve()
    java_home = _java_home(wrapper)
    real_driver = wrapper.with_name("native-image.real")
    if not _is_elf(real_driver):
        raise SystemExit(f"real Native Image driver is missing: {real_driver}")

    arguments = sys.argv[1:]
    for name in SANITIZED_ENVIRONMENT:
        os.environ.pop(name, None)
    os.environ["JAVA_HOME"] = str(java_home)
    environment = os.environ.copy()
    runtime_library_dir = java_home / "lib"
    if (runtime_library_dir / "jspawnhelper").is_file():
        environment["LD_LIBRARY_PATH"] = str(runtime_library_dir)
    if not arguments or (
        len(arguments) == 1 and arguments[0] in INFORMATIONAL_ARGUMENTS
    ):
        raise SystemExit(_run_driver([str(real_driver), *arguments], environment))

    cwd = Path.cwd().resolve()
    compiler = Path("/data/service/hnp/bin/clang")
    support = java_home / "libexec" / "graalvm-ohos"
    header = support / "ohos-native-image-compat.h"
    if (
        not compiler.is_file()
        or not os.access(compiler, os.X_OK)
        or not header.is_file()
    ):
        raise SystemExit(
            f"OpenHarmony Native Image inputs are missing: compiler={compiler}, "
            f"header={header}"
        )
    sys.path.insert(0, str(support))
    from native_image_finalizer import finalize, preflight

    tools = preflight(java_home)
    explicit, output_location = _explicit_output(arguments, cwd)
    if explicit is None:
        raise SystemExit(
            "OpenHarmony Native Image requires an explicit "
            "-o/--output path for transactional finalization"
        )
    _require_safe_destination(explicit, cwd)

    with _signal_exit_guard() as signal_state:
        with _locked_temporary_directory(
            cwd, explicit, signal_state
        ) as locked_temporary:
            temporary = locked_temporary.path
            _require_safe_destination(explicit, cwd)
            _require_directory_path_identity(
                cwd,
                locked_temporary.cwd_identity,
                "Native Image working directory",
            )
            _require_directory_path_identity(
                explicit.parent,
                locked_temporary.destination_parent_identity,
                "Native Image output directory",
            )
            destination_identity = _destination_identity(explicit)
            environment["TMPDIR"] = str(temporary)
            environment["TMPPREFIX"] = str(temporary)
            compiler_launcher = _create_compiler_launcher(
                temporary,
                wrapper.with_suffix(""),
            )
            injected = [
                "-J-XX:ActiveProcessorCount=1",
                "-J-Xmx1024m",
                "-J-Dos.name=Linux",
                f"-J-Djava.io.tmpdir={temporary}",
                "-H:+UnlockExperimentalVMOptions",
                f"-H:CCompilerPath={compiler_launcher}",
                f"-H:CCompilerOption=-include{header}",
                f"-H:CLibraryPath={java_home / 'lib'}",
                "-H:NativeLinkerOption=-l:libg.so",
                "-H:-UnlockExperimentalVMOptions",
            ]

            with _staged_output(
                explicit,
                signal_state,
                locked_temporary.destination_parent_identity,
            ) as staged:
                driver_arguments = _replace_explicit_output(
                    arguments,
                    output_location,
                    staged,
                )
                returncode = _run_driver(
                    [str(real_driver), *driver_arguments, *injected],
                    environment,
                )
                if returncode != 0:
                    raise SystemExit(returncode)

                target = _validate_output(staged)
                target_identity = _destination_identity(target)
                report = finalize(
                    target,
                    java_home,
                    tools=tools,
                    expected_identity=target_identity,
                )
                libg_source = java_home / "lib" / "libg.so"
                with _staged_libg(
                    libg_source,
                    explicit.parent,
                    report["libg_sha256"],
                    signal_state,
                    locked_temporary.destination_parent_identity,
                ) as staged_libg:
                    _commit_output(
                        staged,
                        explicit,
                        destination_identity,
                        staged_libg,
                        report["libg_sha256"],
                        signal_state,
                        report["after_sha256"],
                        locked_temporary.destination_parent_identity,
                    )
                    report["path"] = str(explicit)
            print(f"OHOS_NATIVE_IMAGE_FINALIZED={report['path']}")


if __name__ == "__main__":
    main()
