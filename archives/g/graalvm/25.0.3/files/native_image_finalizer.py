#!/data/service/hnp/bin/python3
"""Finalize a Native Image executable for relocation on OpenHarmony."""

import argparse
import ctypes
import errno
import hashlib
import json
import os
import shutil
import subprocess
import stat
from pathlib import Path

from elf_rewriter import NAME_REWRITES, inspect_elf, is_elf, rewrite_elf


DEFAULT_TOOLS = {
    "objcopy": "/data/service/hnp/bin/llvm-objcopy",
    "patchelf": "/data/service/hnp/bin/patchelf",
    "readelf": "/data/service/hnp/bin/llvm-readelf",
    "signer": "/data/service/hnp/bin/binary-sign-tool",
}
RENAME_NOREPLACE = 1
RENAME_EXCHANGE = 2
SANITIZED_ENVIRONMENT = {
    "JAVA_TOOL_OPTIONS",
    "JDK_JAVA_OPTIONS",
    "LD_LIBRARY_PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "_JAVA_OPTIONS",
}


class FinalizeError(RuntimeError):
    pass


def _run(arguments, description):
    environment = os.environ.copy()
    for name in SANITIZED_ENVIRONMENT:
        environment.pop(name, None)
    completed = subprocess.run(
        [str(argument) for argument in arguments],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise FinalizeError(
            f"{description} failed with {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    return completed


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_fd(descriptor):
    digest = hashlib.sha256()
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest()


def _fsync_file(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_descriptor(descriptor):
    os.fsync(descriptor)


def _fsync_directory(path):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _file_identity_from_status(status, sha256=None):
    if not stat.S_ISREG(status.st_mode):
        raise FinalizeError("Native Image output is not a regular file")
    return {
        "device": status.st_dev,
        "inode": status.st_ino,
        "size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
        "ctime_ns": status.st_ctime_ns,
        "mode": status.st_mode,
        "uid": status.st_uid,
        "gid": status.st_gid,
        "links": status.st_nlink,
        "sha256": sha256,
    }


def _expected_identity_tuple(identity):
    if identity is None:
        return None
    if isinstance(identity, dict):
        return (
            identity["device"],
            identity["inode"],
            identity["size"],
            identity["mtime_ns"],
            identity["ctime_ns"],
            identity["mode"],
            identity["uid"],
            identity["gid"],
            identity["links"],
            identity.get("sha256"),
        )
    return (
        identity.device,
        identity.inode,
        identity.size,
        identity.mtime_ns,
        identity.ctime_ns,
        identity.mode,
        identity.uid,
        identity.gid,
        identity.links,
        identity.sha256,
    )


def _identity_tuple(identity):
    return (
        identity["device"],
        identity["inode"],
        identity["size"],
        identity["mtime_ns"],
        identity["ctime_ns"],
        identity["mode"],
        identity["uid"],
        identity["gid"],
        identity["links"],
        identity.get("sha256"),
    )


def _copy_fd_to_path(source_descriptor, target):
    os.lseek(source_descriptor, 0, os.SEEK_SET)
    with os.fdopen(os.dup(source_descriptor), "rb") as source:
        with Path(target).open("wb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
    _fsync_file(target)


def _open_target_descriptor(target_input, expected_identity=None):
    target_input = Path(target_input)
    if target_input.is_symlink():
        raise FinalizeError(f"Native Image output must not be a symlink: {target_input}")
    parent = target_input.parent.resolve(strict=True)
    target = parent / target_input.name
    parent_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        parent_flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        parent_flags |= os.O_CLOEXEC
    parent_descriptor = os.open(parent, parent_flags)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = None
    try:
        path_status = os.stat(
            target.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(path_status.st_mode):
            raise FinalizeError(f"Native Image output must not be a symlink: {target}")
        descriptor = os.open(target.name, flags, dir_fd=parent_descriptor)
        descriptor_status = os.fstat(descriptor)
        if (
            descriptor_status.st_dev,
            descriptor_status.st_ino,
        ) != (
            path_status.st_dev,
            path_status.st_ino,
        ):
            raise FinalizeError(f"Native Image output changed while opening: {target}")
        before_sha = _sha256_fd(descriptor)
        after_status = os.fstat(descriptor)
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
            getattr(descriptor_status, field) != getattr(after_status, field)
            for field in stable_fields
        ):
            raise FinalizeError(f"Native Image output changed while hashing: {target}")
        identity = _file_identity_from_status(after_status, before_sha)
        expected = _expected_identity_tuple(expected_identity)
        if expected is not None and _identity_tuple(identity) != expected:
            raise FinalizeError(f"Native Image output changed after wrapper validation: {target}")
        return target, parent_descriptor, descriptor, identity
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)
        raise


def _identity_at(parent_descriptor, name, description):
    status = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if stat.S_ISLNK(status.st_mode):
        raise FinalizeError(f"{description} must not be a symlink")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    try:
        before = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (status.st_dev, status.st_ino):
            raise FinalizeError(f"{description} changed while opening")
        digest = _sha256_fd(descriptor)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_mode,
            before.st_uid,
            before.st_gid,
            before.st_nlink,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_mode,
            after.st_uid,
            after.st_gid,
            after.st_nlink,
        ):
            raise FinalizeError(f"{description} changed while hashing")
        return _file_identity_from_status(after, digest)
    finally:
        os.close(descriptor)


def _renameat2(source, target, flags, source_dir_fd=-100, target_dir_fd=-100):
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, "renameat2", None)
    if function is None:
        raise FinalizeError("Native Image finalizer requires renameat2")
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
    raise OSError(error, os.strerror(error), target)


def _rename_exchange_at(left_dir_fd, left_name, right_dir_fd, right_name):
    _renameat2(left_name, right_name, RENAME_EXCHANGE, left_dir_fd, right_dir_fd)


def _same_identity(left, right):
    return _identity_tuple(left) == _identity_tuple(right)


def _preserved_identity_tuple(identity):
    return (
        identity["device"],
        identity["inode"],
        identity["size"],
        identity["mtime_ns"],
        identity["mode"],
        identity["uid"],
        identity["gid"],
        identity["links"],
        identity.get("sha256"),
    )


def _same_preserved_identity(left, right):
    return _preserved_identity_tuple(left) == _preserved_identity_tuple(right)


def _recovery_path(path):
    for counter in range(1000):
        candidate = path.with_name(
            f"{path.name}.ohos-recovery-{os.getpid()}-{counter}"
        )
        if not os.path.lexists(candidate):
            return candidate
    raise FinalizeError(f"cannot allocate Native Image recovery path for {path}")


def _cleanup_path(path):
    for counter in range(1000):
        candidate = path.with_name(
            f"{path.name}.ohos-cleanup-{os.getpid()}-{counter}"
        )
        if not os.path.lexists(candidate):
            return candidate
    raise FinalizeError(f"cannot allocate Native Image cleanup path for {path}")


def _rename_new_at(parent_descriptor, source, destination):
    _renameat2(
        source.name,
        destination.name,
        RENAME_NOREPLACE,
        parent_descriptor,
        parent_descriptor,
    )


def _restore_renamed_path(parent_descriptor, held, original):
    try:
        _rename_new_at(parent_descriptor, held, original)
    except OSError:
        return False
    _fsync_directory_descriptor(parent_descriptor)
    return True


def _move_preserved_identity(
    parent_descriptor,
    source,
    destination,
    expected_identity,
    description,
):
    try:
        _rename_new_at(parent_descriptor, source, destination)
    except OSError as exc:
        raise FinalizeError(
            f"{description} could not be retained at {destination}"
        ) from exc
    try:
        retained = _identity_at(
            parent_descriptor,
            destination.name,
            f"retained {description}",
        )
    except (FinalizeError, OSError) as exc:
        _restore_renamed_path(parent_descriptor, destination, source)
        raise FinalizeError(
            f"{description} retained identity is not trusted: {destination}"
        ) from exc
    if not _same_preserved_identity(retained, expected_identity):
        _restore_renamed_path(parent_descriptor, destination, source)
        raise FinalizeError(f"{description} recovery identity mismatch: {destination}")
    _fsync_directory_descriptor(parent_descriptor)


def _cleanup_temporary(parent_descriptor, temporary, expected_identity, description):
    if expected_identity is None or not os.path.lexists(temporary):
        return
    try:
        cleanup = _cleanup_path(temporary)
        _rename_new_at(parent_descriptor, temporary, cleanup)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return
        return
    try:
        current = _identity_at(parent_descriptor, cleanup.name, f"cleanup {description}")
    except (FinalizeError, OSError):
        _restore_renamed_path(parent_descriptor, cleanup, temporary)
        return
    if not _same_preserved_identity(current, expected_identity):
        _restore_renamed_path(parent_descriptor, cleanup, temporary)
        return
    try:
        os.unlink(cleanup.name, dir_fd=parent_descriptor)
    except OSError:
        return
    try:
        _fsync_directory_descriptor(parent_descriptor)
    except OSError:
        return


def _retain_recovery(parent_descriptor, source, expected_identity, description):
    current = _identity_at(parent_descriptor, source.name, description)
    if not _same_preserved_identity(current, expected_identity):
        raise FinalizeError(f"{description} changed before recovery: {source}")
    recovery = _recovery_path(source)
    _move_preserved_identity(
        parent_descriptor,
        source,
        recovery,
        expected_identity,
        description,
    )
    return recovery


def _rollback_signed_exchange(parent_descriptor, signed, target, signed_identity, target_identity):
    current_signed = _identity_at(
        parent_descriptor,
        signed.name,
        "Native Image backup",
    )
    if not _same_preserved_identity(current_signed, target_identity):
        raise FinalizeError(
            f"Native Image output changed during install and cannot be restored safely: {target}"
        )
    try:
        current_target = _identity_at(
            parent_descriptor,
            target.name,
            "installed Native Image output",
        )
    except (FinalizeError, OSError) as exc:
        recovery = _retain_recovery(
            parent_descriptor,
            signed,
            target_identity,
            "Native Image backup",
        )
        raise FinalizeError(
            "Native Image output changed during install; "
            f"previous output retained at {recovery}: {target}"
        ) from exc
    if not _same_preserved_identity(current_target, signed_identity):
        recovery = _retain_recovery(
            parent_descriptor,
            signed,
            target_identity,
            "Native Image backup",
        )
        raise FinalizeError(
            "Native Image output changed during install; "
            f"previous output retained at {recovery}: {target}"
        )
    _rename_exchange_at(parent_descriptor, target.name, parent_descriptor, signed.name)
    restored_target = _identity_at(
        parent_descriptor,
        target.name,
        "restored Native Image output",
    )
    retained_signed = _identity_at(
        parent_descriptor,
        signed.name,
        "retained signed Native Image output",
    )
    if not _same_preserved_identity(restored_target, current_signed):
        raise FinalizeError(f"Native Image output rollback target mismatch: {target}")
    if not _same_preserved_identity(retained_signed, current_target):
        raise FinalizeError(f"Native Image signed backup rollback mismatch: {signed}")


def _retain_post_install_backup(parent_descriptor, signed, target, target_identity, cause):
    recovery = _retain_recovery(
        parent_descriptor,
        signed,
        target_identity,
        "Native Image backup",
    )
    raise FinalizeError(
        "Native Image post-install verification failed; "
        f"previous output retained at {recovery}: {target}"
    ) from cause


def _install_signed_output(signed, target, parent_descriptor, target_identity):
    current = _identity_at(parent_descriptor, target.name, "Native Image output")
    if not _same_identity(current, target_identity):
        raise FinalizeError(f"Native Image output changed before install: {target}")
    signed_identity = _identity_at(
        parent_descriptor,
        signed.name,
        "signed Native Image output",
    )
    _rename_exchange_at(parent_descriptor, signed.name, parent_descriptor, target.name)
    try:
        installed = _identity_at(
            parent_descriptor,
            target.name,
            "installed Native Image output",
        )
        backup = _identity_at(parent_descriptor, signed.name, "Native Image backup")
        if not _same_preserved_identity(installed, signed_identity):
            raise FinalizeError(f"signed Native Image output changed during install: {signed}")
        if not _same_preserved_identity(backup, target_identity):
            raise FinalizeError(f"Native Image output changed during install: {target}")
    except BaseException:
        try:
            _rollback_signed_exchange(
                parent_descriptor,
                signed,
                target,
                signed_identity,
                target_identity,
            )
        finally:
            raise
    return signed_identity["sha256"]


def _codesign_size(path, tools, scratch):
    sections = _run(
        [tools["readelf"], "-SW", path], f"inspect signature for {path}"
    ).stdout
    matches = [
        line for line in sections.splitlines() if ".codesign" in line.split()
    ]
    if len(matches) != 1:
        raise FinalizeError(f"{path} has {len(matches)} .codesign sections")
    dump = Path(f"{scratch}.codesign")
    inspect = Path(f"{scratch}.codesign-inspect")
    for temporary in (dump, inspect):
        if os.path.lexists(temporary):
            temporary.unlink()
    try:
        shutil.copy2(path, inspect)
        _run(
            [tools["objcopy"], "--dump-section", f".codesign={dump}", inspect],
            f"dump signature for {path}",
        )
        if not dump.is_file() or dump.stat().st_size <= 0:
            raise FinalizeError(f"{path} has an empty .codesign section")
        return dump.stat().st_size
    finally:
        for temporary in (dump, inspect):
            if os.path.lexists(temporary):
                temporary.unlink()


def preflight(java_home, tools=None):
    java_home = Path(java_home).resolve()
    tools = dict(DEFAULT_TOOLS if tools is None else tools)
    missing_names = sorted(set(DEFAULT_TOOLS) - set(tools))
    if missing_names:
        raise FinalizeError(
            f"OpenHarmony finalizer tool keys are missing: {missing_names}"
        )
    missing_tools = [
        path
        for path in tools.values()
        if not os.path.isfile(path) or not os.access(path, os.X_OK)
    ]
    if missing_tools:
        raise FinalizeError(
            f"OpenHarmony finalizer tools are missing: {missing_tools}"
        )
    libg_source = java_home / "lib" / "libg.so"
    if not is_elf(libg_source):
        raise FinalizeError(f"private libg.so is missing: {libg_source}")
    return tools


def finalize(target, java_home, tools=None, expected_identity=None):
    target, target_parent_descriptor, target_descriptor, target_identity = (
        _open_target_descriptor(target, expected_identity)
    )
    java_home = Path(java_home).resolve()
    tools = preflight(java_home, tools)
    libg_source = java_home / "lib" / "libg.so"
    mode = target_identity["mode"] & 0o777 or 0o755
    stem = target.parent / f".{target.name}.ohos-finalize-{os.getpid()}"
    unsigned = Path(f"{stem}.unsigned")
    clean = Path(f"{stem}.clean")
    signed = Path(f"{stem}.signed")
    temporaries = (unsigned, clean, signed)
    temporary_identities = {}
    for temporary in temporaries:
        if os.path.lexists(temporary):
            os.close(target_descriptor)
            os.close(target_parent_descriptor)
            raise FinalizeError(
                f"Native Image temporary path already exists: {temporary}"
            )

    before_sha = target_identity["sha256"]
    libg_sha = _sha256(libg_source)
    libg_codesign_size = _codesign_size(libg_source, tools, stem)
    try:
        _copy_fd_to_path(target_descriptor, unsigned)
        temporary_identities[unsigned] = _identity_at(
            target_parent_descriptor,
            unsigned.name,
            "unsigned Native Image temporary",
        )
        if not is_elf(unsigned):
            raise FinalizeError(f"Native Image output is not a regular ELF: {target}")
        rewrite_elf(unsigned)
        _run(
            [tools["patchelf"], "--force-rpath", "--set-rpath", "$ORIGIN", unsigned],
            "set relocatable Native Image RPATH",
        )
        _run(
            [tools["objcopy"], "--remove-section", ".codesign", unsigned, clean],
            "remove stale Native Image signature",
        )
        temporary_identities[clean] = _identity_at(
            target_parent_descriptor,
            clean.name,
            "clean Native Image temporary",
        )
        _run(
            [
                tools["signer"],
                "sign",
                "-inFile",
                clean,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            "sign Native Image output",
        )
        if not is_elf(signed):
            raise FinalizeError("signer did not produce an ELF output")
        os.chmod(signed, mode)
        temporary_identities[signed] = _identity_at(
            target_parent_descriptor,
            signed.name,
            "signed Native Image temporary",
        )

        info = inspect_elf(signed)
        stale = sorted(
            (set(info["needed"]) | set(info["version_files"])) & set(NAME_REWRITES)
        )
        if stale:
            raise FinalizeError(f"Native Image retains GNU references: {stale}")
        if info["interpreter"] not in (None, "/lib/ld-musl-aarch64.so.1"):
            raise FinalizeError(
                f"Native Image has an unexpected interpreter: {info['interpreter']}"
            )
        if "libg.so" not in info["needed"]:
            raise FinalizeError("Native Image output does not depend on libg.so")
        rpath = _run(
            [tools["patchelf"], "--print-rpath", signed],
            "read finalized Native Image RPATH",
        ).stdout.strip()
        if rpath != "$ORIGIN":
            raise FinalizeError(f"Native Image RPATH is not relocatable: {rpath}")
        codesign_size = _codesign_size(signed, tools, stem)

        _fsync_file(signed)
        signed_sha = _install_signed_output(
            signed,
            target,
            target_parent_descriptor,
            target_identity,
        )
        try:
            installed = _identity_at(
                target_parent_descriptor,
                target.name,
                "installed Native Image output",
            )
            if not _same_preserved_identity(installed, temporary_identities[signed]):
                raise FinalizeError(
                    f"installed Native Image output changed after install: {target}"
                )
            _fsync_directory_descriptor(target_parent_descriptor)
            committed = _identity_at(
                target_parent_descriptor,
                target.name,
                "committed Native Image output",
            )
            if not _same_preserved_identity(committed, temporary_identities[signed]):
                raise FinalizeError(
                    f"committed Native Image output changed after install: {target}"
                )
            after_sha = committed["sha256"]
            if after_sha != signed_sha:
                raise FinalizeError("installed Native Image hash mismatch")
        except (FinalizeError, OSError) as exc:
            _retain_post_install_backup(
                target_parent_descriptor,
                signed,
                target,
                target_identity,
                exc,
            )
        temporary_identities[signed] = target_identity
        report = {
            "schema": 1,
            "path": str(target),
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "libg_sha256": libg_sha,
            "libg_codesign_size": libg_codesign_size,
            "interpreter": info["interpreter"],
            "needed": info["needed"],
            "rpath": rpath,
            "codesign_size": codesign_size,
        }
        return report
    finally:
        os.close(target_descriptor)
        try:
            for temporary in temporaries:
                _cleanup_temporary(
                    target_parent_descriptor,
                    temporary,
                    temporary_identities.get(temporary),
                    f"Native Image temporary {temporary.name}",
                )
        finally:
            os.close(target_parent_descriptor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("java_home")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = finalize(args.target, args.java_home)
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        Path(args.report).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
