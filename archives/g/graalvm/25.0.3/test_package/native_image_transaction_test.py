#!/usr/bin/env python3
"""Deterministic fault, signal, and compare-and-swap transaction tests."""

import hashlib
import importlib.util
import errno
import os
import shutil
import signal
import sys
from pathlib import Path


ASSERTIONS = 0


def require(condition, message):
    global ASSERTIONS
    if not condition:
        raise AssertionError(message)
    ASSERTIONS += 1


def load_wrapper(path):
    spec = importlib.util.spec_from_file_location(
        "graalvm_native_image_wrapper_test", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Native Image wrapper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_finalizer(path, wrapper=None):
    wrapper_path = Path(path).resolve()
    candidates = [wrapper_path.parent]
    if wrapper is not None and hasattr(wrapper, "_java_home"):
        try:
            java_home = wrapper._java_home(wrapper_path)
        except RuntimeError:
            pass
        else:
            candidates.append(java_home / "libexec" / "graalvm-ohos")

    module_path = None
    for support in candidates:
        candidate = support / "native_image_finalizer.py"
        if candidate.is_file():
            module_path = candidate
            break
    if module_path is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise RuntimeError(f"cannot load Native Image finalizer from: {searched}")

    sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location(
        "graalvm_native_image_finalizer_test",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Native Image finalizer from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reset_directory(path):
    if os.path.lexists(path):
        shutil.rmtree(path)
    path.mkdir(parents=True)


def test_stage_signal(wrapper, root, signum, label):
    work = root / f"stage-{label}"
    reset_directory(work)
    destination = work / "output"
    real_mkdtemp = wrapper.tempfile.mkdtemp
    state = None
    status = 0

    def injecting_mkdtemp(*args, **kwargs):
        created = real_mkdtemp(*args, **kwargs)
        os.kill(os.getpid(), signum)
        return created

    try:
        with wrapper._signal_exit_guard() as state:
            wrapper.tempfile.mkdtemp = injecting_mkdtemp
            try:
                with wrapper._staged_output(destination, state):
                    raise AssertionError("stage signal did not stop finalization")
            finally:
                wrapper.tempfile.mkdtemp = real_mkdtemp
    except SystemExit as exc:
        status = exc.code

    require(status == 128 + signum, f"wrong {label} stage signal status")
    require(state is not None and state.pending == signum, f"missing {label} signal")
    require(not state.committed, f"{label} stage was incorrectly committed")
    require(not list(work.glob(".*.graalvm-ohos-stage-*")), f"{label} stage leaked")


def test_commit_signal(wrapper, root, signum, signal_label, phase):
    work = root / f"commit-{phase}-{signal_label}"
    reset_directory(work)
    destination = work / "output"
    destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    staged = work / "staged-output"
    staged.write_bytes(b"new-output")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    libg_sha = sha256(staged_libg)
    real_publish = wrapper._rename_noreplace_at
    real_exchange = wrapper._rename_exchange_at

    def injecting_publish(source_fd, source_name, target_fd, target_name):
        result = real_publish(source_fd, source_name, target_fd, target_name)
        if target_name == "libg.so":
            os.kill(os.getpid(), signum)
        return result

    def injecting_exchange(left_fd, left_name, right_fd, right_name):
        if phase == "exchange-before":
            os.kill(os.getpid(), signum)
        result = real_exchange(left_fd, left_name, right_fd, right_name)
        if phase == "exchange-after":
            os.kill(os.getpid(), signum)
        return result

    with wrapper._signal_exit_guard() as state:
        if phase == "sidecar":
            wrapper._rename_noreplace_at = injecting_publish
        else:
            wrapper._rename_exchange_at = injecting_exchange
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                libg_sha,
                state,
                sha256(staged),
            )
        finally:
            wrapper._rename_noreplace_at = real_publish
            wrapper._rename_exchange_at = real_exchange

    require(state.committed, f"{phase} {signal_label} did not commit")
    require(state.pending == signum, f"{phase} {signal_label} was not observed")
    require(destination.read_bytes() == b"new-output", f"{phase} output mismatch")
    require((work / "libg.so").read_bytes() == b"signed-libg", f"{phase} libg mismatch")
    require(
        not list(work.glob(".*.graalvm-ohos-backup-*")),
        f"{phase} backup leaked",
    )


def test_post_finalize_destination_change(wrapper, root):
    work = root / "post-finalize-change"
    reset_directory(work)
    destination = work / "output"
    destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    destination_status = destination.stat()
    staged = work / "staged-output"
    staged.write_bytes(b"finalized-output")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    (work / "libg.so").write_bytes(b"signed-libg")
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"new-output")
    os.utime(
        replacement,
        ns=(destination_status.st_atime_ns, destination_status.st_mtime_ns),
    )
    state = wrapper._SignalExitState()
    real_exchange = wrapper._rename_exchange_at
    real_replace = wrapper.os.replace
    real_fsync_directory = wrapper._fsync_directory_descriptor
    fsync_calls = 0
    replacement_injected = False

    def injecting_exchange(left_fd, left_name, right_fd, right_name):
        nonlocal replacement_injected
        if right_name == destination.name and not replacement_injected:
            real_replace(replacement, destination)
            replacement_injected = True
        return real_exchange(left_fd, left_name, right_fd, right_name)

    def recording_fsync_directory(descriptor):
        nonlocal fsync_calls
        fsync_calls += 1
        return real_fsync_directory(descriptor)

    failed = False
    wrapper._rename_exchange_at = injecting_exchange
    wrapper._fsync_directory_descriptor = recording_fsync_directory
    try:
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
            )
        except RuntimeError as exc:
            failed = "changed during finalization" in str(exc)
    finally:
        wrapper._rename_exchange_at = real_exchange
        wrapper._fsync_directory_descriptor = real_fsync_directory

    require(failed, "post-finalizer destination change was accepted")
    require(replacement_injected, "destination exchange race was not injected")
    require(destination.read_bytes() == b"new-output", "concurrent output changed")
    require(
        (work / "libg.so").read_bytes() == b"signed-libg"
        and fsync_calls >= 1,
        "post-finalizer rollback did not preserve and fsync matching libg.so",
    )
    require(not state.committed, "failed compare-and-swap was marked committed")


def test_post_finalize_stage_file_replacement(wrapper, root):
    work = root / "post-finalize-stage-file-replacement"
    reset_directory(work)
    destination = work / "output"
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    state = wrapper._SignalExitState()
    failure = None

    with wrapper._staged_output(destination, state) as staged:
        staged.write_bytes(b"validated-output")
        finalized_sha = sha256(staged)
        staged.write_bytes(b"tampered-output")
        try:
            wrapper._commit_output(
                staged,
                destination,
                None,
                staged_libg,
                sha256(staged_libg),
                state,
                finalized_sha,
            )
        except RuntimeError as exc:
            failure = exc

    require(
        failure is not None and "finalized Native Image output hash mismatch" in str(failure),
        "post-finalizer stage file replacement was accepted",
    )
    require(not destination.exists(), "tampered stage output was published")
    require(not (work / "libg.so").exists(), "libg.so was published on stage failure")
    require(not state.committed, "stage hash failure was marked committed")


def test_post_finalize_stage_directory_replacement(wrapper, root):
    work = root / "post-finalize-stage-directory-replacement"
    reset_directory(work)
    destination = work / "output"
    original_stage = work / ".output.graalvm-ohos-stage-original"
    original_stage.mkdir(mode=0o700)
    (original_stage / "output").write_bytes(b"validated-output")
    original_identity = wrapper._directory_identity(original_stage)
    finalized_sha = sha256(original_stage / "output")
    staged = wrapper._StagedOutput(original_stage / "output", original_identity)
    kept_stage = work / "kept-original-stage"
    incoming_stage = work / "incoming-stage"
    incoming_stage.mkdir(mode=0o700)
    (incoming_stage / "output").write_bytes(b"validated-output")
    original_stage.rename(kept_stage)
    incoming_stage.rename(original_stage)
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    state = wrapper._SignalExitState()
    failure = None

    try:
        wrapper._commit_output(
            staged,
            destination,
            None,
            staged_libg,
            sha256(staged_libg),
            state,
            finalized_sha,
        )
    except RuntimeError as exc:
        failure = exc

    require(
        failure is not None and "output stage changed after finalization" in str(failure),
        "post-finalizer stage directory replacement was accepted",
    )
    require(not destination.exists(), "replacement stage directory was published")
    require((original_stage / "output").read_bytes() == b"validated-output", "replacement stage changed")
    require((kept_stage / "output").read_bytes() == b"validated-output", "original stage changed")
    require(not state.committed, "stage directory failure was marked committed")


def test_pre_publish_output_stage_directory_replacement(wrapper, root, existing):
    label = "existing" if existing else "new"
    work = root / f"pre-publish-output-stage-directory-replacement-{label}"
    reset_directory(work)
    destination = work / "output"
    if existing:
        destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    original_stage = work / ".output.graalvm-ohos-stage-original"
    original_stage.mkdir(mode=0o700)
    (original_stage / "output").write_bytes(b"validated-output")
    original_identity = wrapper._directory_identity(original_stage)
    staged = wrapper._StagedOutput(original_stage / "output", original_identity)
    replacement_stage = work / "replacement-stage"
    replacement_stage.mkdir(mode=0o700)
    (replacement_stage / "output").write_bytes(b"attacker-output")
    kept_stage = work / "kept-original-stage"
    staged_libg_parent = work / "libg-stage"
    staged_libg_parent.mkdir(mode=0o700)
    staged_libg = staged_libg_parent / "libg.so"
    staged_libg.write_bytes(b"signed-libg")
    state = wrapper._SignalExitState()
    real_noreplace_at = wrapper._rename_noreplace_at
    real_exchange_at = wrapper._rename_exchange_at
    replacement_injected = False
    failure = None

    def maybe_replace_stage(source_fd, source_name, target_fd, target_name):
        nonlocal replacement_injected
        if (
            not replacement_injected
            and source_name == "output"
            and target_name == "output"
        ):
            original_stage.rename(kept_stage)
            replacement_stage.rename(original_stage)
            replacement_injected = True

    def injecting_noreplace_at(source_fd, source_name, target_fd, target_name):
        maybe_replace_stage(source_fd, source_name, target_fd, target_name)
        return real_noreplace_at(source_fd, source_name, target_fd, target_name)

    def injecting_exchange_at(left_fd, left_name, right_fd, right_name):
        maybe_replace_stage(left_fd, left_name, right_fd, right_name)
        return real_exchange_at(left_fd, left_name, right_fd, right_name)

    wrapper._rename_noreplace_at = injecting_noreplace_at
    wrapper._rename_exchange_at = injecting_exchange_at
    try:
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace_at = real_noreplace_at
        wrapper._rename_exchange_at = real_exchange_at

    require(failure is None, f"{label} fd-bound output publish failed: {failure}")
    require(replacement_injected, f"{label} output stage race was not injected")
    require(destination.read_bytes() == b"validated-output", f"{label} attacker output was published")
    require((original_stage / "output").read_bytes() == b"attacker-output", f"{label} replacement stage changed")
    require((work / "libg.so").read_bytes() == b"signed-libg", f"{label} libg.so changed")
    require(state.committed, f"{label} fd-bound output commit was not marked committed")
    if existing:
        require((kept_stage / "output").read_bytes() == b"old-output", "old output was not staged after exchange")
    else:
        require(not (kept_stage / "output").exists(), "original stage output was not moved")


def test_post_publish_destination_replacement(wrapper, root, existing):
    label = "existing" if existing else "new"
    work = root / f"post-publish-replacement-{label}"
    reset_directory(work)
    destination = work / "output"
    if existing:
        destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    libg_target = work / "libg.so"
    libg_target.write_bytes(b"signed-libg")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"concurrent-output")
    replacement_identity = wrapper._destination_identity(replacement)
    state = wrapper._SignalExitState()
    real_fsync_directory = wrapper._fsync_directory_descriptor
    real_replace = wrapper.os.replace
    replacement_injected = False
    failure = None

    def replacing_fsync_directory(descriptor):
        nonlocal replacement_injected
        if not replacement_injected:
            real_replace(replacement, destination)
            replacement_injected = True
        return real_fsync_directory(descriptor)

    wrapper._fsync_directory_descriptor = replacing_fsync_directory
    try:
        try:
            with wrapper._staged_output(destination, state) as staged:
                staged.write_bytes(b"new-output")
                wrapper._commit_output(
                    staged,
                    destination,
                    destination_identity,
                    staged_libg,
                    sha256(staged_libg),
                    state,
                    sha256(staged),
                )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._fsync_directory_descriptor = real_fsync_directory

    stages = list(work.glob(".output.graalvm-ohos-stage-*"))
    require(
        failure is not None
        and str(failure) == "Native Image transaction rollback failed"
        and failure.__cause__ is not None
        and "changed before" in str(failure.__cause__),
        f"{label} post-publish replacement did not fail closed",
    )
    require(replacement_injected, f"{label} post-publish replacement was not injected")
    require(
        destination.read_bytes() == b"concurrent-output",
        f"{label} concurrent output content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(destination), replacement_identity
        ),
        f"{label} concurrent output identity changed",
    )
    require(libg_target.read_bytes() == b"signed-libg", f"{label} libg.so changed")
    require(not state.committed, f"{label} failed commit was marked committed")
    if existing:
        require(
            len(stages) == 1
            and (stages[0] / "output").read_bytes() == b"old-output",
            "existing output recovery stage was not preserved",
        )
    else:
        require(not stages, "new output left an unnecessary recovery stage")
    for stage in stages:
        shutil.rmtree(stage)


def test_exchange_rollback_quarantine_race(wrapper, root):
    work = root / "exchange-rollback-quarantine-race"
    reset_directory(work)
    staged = work / "staged-output"
    staged.write_bytes(b"old-output")
    old_identity = wrapper._destination_identity(staged)
    destination = work / "output"
    destination.write_bytes(b"published-output")
    published_identity = wrapper._destination_identity(destination)
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"concurrent-output")
    replacement_identity = wrapper._destination_identity(replacement)
    state = wrapper._SignalExitState()
    real_noreplace = wrapper._rename_noreplace
    real_replace = wrapper.os.replace
    replacement_injected = False
    failure = None

    def replacing_noreplace(source, target):
        nonlocal replacement_injected
        if not replacement_injected and Path(source) == destination:
            real_replace(replacement, destination)
            replacement_injected = True
        return real_noreplace(source, target)

    wrapper._rename_noreplace = replacing_noreplace
    try:
        try:
            wrapper._exchange_back(
                staged,
                destination,
                old_identity,
                published_identity,
                state,
                "Native Image output",
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace = real_noreplace

    require(
        failure is not None and "changed before rollback" in str(failure),
        "exchange rollback quarantine race did not fail closed",
    )
    require(replacement_injected, "exchange rollback quarantine race was not injected")
    require(
        destination.read_bytes() == b"concurrent-output",
        "exchange rollback changed concurrent output content",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(destination), replacement_identity
        ),
        "exchange rollback changed concurrent output identity",
    )
    require(staged.read_bytes() == b"old-output", "exchange rollback lost old output")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(staged), old_identity
        ),
        "exchange rollback changed old output identity",
    )
    require(work in state.preserved_paths, "exchange rollback stage was not preserved")


def test_noreplace_rollback_check_race(wrapper, root):
    work = root / "noreplace-rollback-check-race"
    reset_directory(work)
    destination = work / "output"
    destination.write_bytes(b"published-output")
    published_identity = wrapper._destination_identity(destination)
    staged = work / "staged-output"
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"concurrent-output")
    replacement_identity = wrapper._destination_identity(replacement)
    state = wrapper._SignalExitState()
    real_noreplace = wrapper._rename_noreplace
    real_replace = wrapper.os.replace
    replacement_injected = False
    failure = None

    def replacing_noreplace(source, target):
        nonlocal replacement_injected
        if not replacement_injected:
            real_replace(replacement, destination)
            replacement_injected = True
        return real_noreplace(source, target)

    wrapper._rename_noreplace = replacing_noreplace
    try:
        try:
            wrapper._move_back_noreplace(
                destination,
                staged,
                published_identity,
                state,
                "Native Image output",
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace = real_noreplace

    require(
        failure is not None and "changed during rollback" in str(failure),
        "noreplace rollback check race did not fail closed",
    )
    require(replacement_injected, "noreplace rollback check race was not injected")
    require(
        destination.read_bytes() == b"concurrent-output",
        "noreplace rollback changed concurrent output content",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(destination), replacement_identity
        ),
        "noreplace rollback changed concurrent output identity",
    )
    require(not staged.exists(), "noreplace rollback retained a moved concurrent output")


def test_pre_publish_libg_stage_directory_replacement(wrapper, root):
    work = root / "pre-publish-libg-stage-directory-replacement"
    reset_directory(work)
    destination = work / "output"
    original_stage = work / ".output.graalvm-ohos-stage-original"
    original_stage.mkdir(mode=0o700)
    (original_stage / "output").write_bytes(b"validated-output")
    staged = wrapper._StagedOutput(
        original_stage / "output",
        wrapper._directory_identity(original_stage),
    )
    original_libg_stage = work / ".libg.so.graalvm-ohos-stage-original"
    original_libg_stage.mkdir(mode=0o700)
    staged_libg = original_libg_stage / "libg.so"
    staged_libg.write_bytes(b"signed-libg")
    replacement_libg_stage = work / "replacement-libg-stage"
    replacement_libg_stage.mkdir(mode=0o700)
    (replacement_libg_stage / "libg.so").write_bytes(b"attacker-libg")
    kept_libg_stage = work / "kept-libg-stage"
    state = wrapper._SignalExitState()
    real_noreplace_at = wrapper._rename_noreplace_at
    replacement_injected = False
    failure = None

    def injecting_noreplace_at(source_fd, source_name, target_fd, target_name):
        nonlocal replacement_injected
        if (
            not replacement_injected
            and source_name == "libg.so"
            and target_name == "libg.so"
        ):
            original_libg_stage.rename(kept_libg_stage)
            replacement_libg_stage.rename(original_libg_stage)
            replacement_injected = True
        return real_noreplace_at(source_fd, source_name, target_fd, target_name)

    wrapper._rename_noreplace_at = injecting_noreplace_at
    try:
        try:
            wrapper._commit_output(
                staged,
                destination,
                None,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace_at = real_noreplace_at

    require(failure is None, f"fd-bound libg publish failed: {failure}")
    require(replacement_injected, "libg stage race was not injected")
    require((work / "libg.so").read_bytes() == b"signed-libg", "attacker libg.so was published")
    require(destination.read_bytes() == b"validated-output", "libg race changed output")
    require((original_libg_stage / "libg.so").read_bytes() == b"attacker-libg", "replacement libg stage changed")
    require(not (kept_libg_stage / "libg.so").exists(), "original staged libg was not moved")
    require(state.committed, "fd-bound libg commit was not marked committed")


def test_output_cleanup_identity_race(wrapper, root):
    work = root / "output-cleanup-identity-race"
    reset_directory(work)
    destination = work / "output"
    state = wrapper._SignalExitState()
    kept = work / "kept-stage"
    incoming = work / "incoming-stage"
    incoming.mkdir(mode=0o700)
    (incoming / "sentinel").write_bytes(b"replacement-stage")
    replacement_identity = wrapper._directory_identity(incoming)
    real_noreplace = wrapper._rename_noreplace
    original_identity = None
    stage_path = None
    replacement_injected = False
    failure = None

    def replacing_noreplace(source, target):
        nonlocal replacement_injected
        if (
            not replacement_injected
            and stage_path is not None
            and Path(source) == stage_path
            and "graalvm-ohos-cleanup" in Path(target).name
        ):
            stage_path.rename(kept)
            incoming.rename(stage_path)
            replacement_injected = True
        return real_noreplace(source, target)

    try:
        wrapper._rename_noreplace = replacing_noreplace
        try:
            with wrapper._staged_output(destination, state) as staged:
                staged.write_bytes(b"original-stage")
                stage_path = staged.parent
                original_identity = wrapper._directory_identity(stage_path)
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace = real_noreplace

    require(
        failure is not None and "output stage path changed before cleanup" in str(failure),
        "output cleanup identity replacement did not fail closed",
    )
    require(replacement_injected, "output cleanup replacement was not injected")
    require(
        (stage_path / "sentinel").read_bytes() == b"replacement-stage",
        "output cleanup deleted replacement stage",
    )
    require(
        wrapper._directory_identity(stage_path) == replacement_identity,
        "output cleanup changed replacement stage identity",
    )
    require(
        (kept / "output").read_bytes() == b"original-stage",
        "output cleanup lost original stage",
    )
    require(
        wrapper._directory_identity(kept) == original_identity,
        "output cleanup changed original stage identity",
    )
    require(not state.committed, "output cleanup failure was marked committed")
    shutil.rmtree(stage_path)
    shutil.rmtree(kept)


def test_scratch_cleanup_identity_race(wrapper, root):
    work = root / "scratch-cleanup-identity-race"
    reset_directory(work)
    destination = work / "output"
    state = wrapper._SignalExitState()
    kept = work / "kept-scratch"
    incoming = work / "incoming-scratch"
    incoming.mkdir(mode=0o700)
    (incoming / "sentinel").write_bytes(b"replacement-scratch")
    scratch_path = work / ".t"
    original_identity = None
    replacement_identity = wrapper._directory_identity(incoming)
    real_noreplace = wrapper._rename_noreplace
    replacement_injected = False
    failure = None

    def replacing_noreplace(source, target):
        nonlocal replacement_injected
        if (
            not replacement_injected
            and Path(source) == scratch_path
            and "graalvm-ohos-cleanup" in Path(target).name
        ):
            scratch_path.rename(kept)
            incoming.rename(scratch_path)
            replacement_injected = True
        return real_noreplace(source, target)

    try:
        wrapper._rename_noreplace = replacing_noreplace
        try:
            with wrapper._locked_temporary_directory(
                work, destination, state
            ) as scratch:
                (scratch / "original").write_bytes(b"original-scratch")
                original_identity = wrapper._directory_identity(scratch)
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._rename_noreplace = real_noreplace

    lock_reacquired = False
    flags = wrapper.os.O_RDONLY
    if hasattr(wrapper.os, "O_NOFOLLOW"):
        flags |= wrapper.os.O_NOFOLLOW
    descriptor = wrapper.os.open(wrapper._lock_path(work), flags)
    try:
        wrapper.fcntl.flock(
            descriptor,
            wrapper.fcntl.LOCK_EX | wrapper.fcntl.LOCK_NB,
        )
        lock_reacquired = True
    finally:
        wrapper.fcntl.flock(descriptor, wrapper.fcntl.LOCK_UN)
        wrapper.os.close(descriptor)

    require(
        failure is not None and "scratch path changed before cleanup" in str(failure),
        "scratch cleanup identity replacement did not fail closed",
    )
    require(replacement_injected, "scratch cleanup replacement was not injected")
    require(
        (scratch_path / "sentinel").read_bytes() == b"replacement-scratch",
        "scratch cleanup deleted replacement directory",
    )
    require(
        wrapper._directory_identity(scratch_path) == replacement_identity,
        "scratch cleanup changed replacement directory identity",
    )
    require(
        (kept / "original").read_bytes() == b"original-scratch",
        "scratch cleanup lost original directory",
    )
    require(
        wrapper._directory_identity(kept) == original_identity,
        "scratch cleanup changed original directory identity",
    )
    require(lock_reacquired, "scratch cleanup failure retained the output lock")
    require(not state.committed, "scratch cleanup failure was marked committed")
    shutil.rmtree(scratch_path)
    shutil.rmtree(kept)


def test_lock_path_canonicalization(wrapper, root):
    work = root / "lock-path-canonicalization"
    reset_directory(work)
    destination = work / "output"
    state = wrapper._SignalExitState()
    lock_path = wrapper._canonical_lock_path(work)

    require(lock_path.parent == work.resolve(), "lock parent was not canonicalized")
    require(lock_path.name == ".graalvm-native-image.lock", "lock basename changed")
    with wrapper._locked_temporary_directory(work, destination, state) as scratch:
        require(scratch == work / ".t", "scratch path changed")
    require(lock_path.is_file() and not lock_path.is_symlink(), "lock is not a real file")


def test_locked_destination_parent_replacement(wrapper, root):
    work = root / "locked-destination-parent-replacement"
    reset_directory(work)
    destination_parent = work / "out"
    destination_parent.mkdir(mode=0o700)
    destination = destination_parent / "output"
    destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    staged = work / "staged-output"
    staged.write_bytes(b"new-output")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    kept_parent = work / "kept-out"
    replacement_parent = work / "replacement-out"
    replacement_parent.mkdir(mode=0o700)
    state = wrapper._SignalExitState()
    failure = None

    with wrapper._locked_temporary_directory(work, destination, state) as locked:
        locked_destination_identity = locked.destination_parent_identity
        destination_parent.rename(kept_parent)
        replacement_parent.rename(destination_parent)
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
                locked.destination_parent_identity,
            )
        except RuntimeError as exc:
            failure = exc

    require(
        failure is not None and "output directory changed after finalization" in str(failure),
        "locked destination parent replacement was accepted",
    )
    require(
        wrapper._directory_identity(kept_parent) == locked_destination_identity,
        "locked destination parent identity was not preserved",
    )
    require(
        wrapper._directory_identity(destination_parent) != locked_destination_identity,
        "replacement destination parent reused locked identity",
    )
    require((kept_parent / "output").read_bytes() == b"old-output", "old output changed")
    require(not destination.exists(), "output was published into replacement parent")
    require(not (destination_parent / "libg.so").exists(), "libg.so was published into replacement parent")
    require(staged.read_bytes() == b"new-output", "stage changed on parent replacement")
    require(not state.committed, "parent replacement failure was marked committed")


class FinalizerCompleted:
    def __init__(self, stdout=""):
        self.stdout = stdout


def install_finalizer_test_doubles(finalizer):
    saved = {
        "preflight": finalizer.preflight,
        "is_elf": finalizer.is_elf,
        "rewrite_elf": finalizer.rewrite_elf,
        "inspect_elf": finalizer.inspect_elf,
        "_codesign_size": finalizer._codesign_size,
        "_run": finalizer._run,
    }

    def fake_run(arguments, _description):
        args = [str(argument) for argument in arguments]
        if "--print-rpath" in args:
            return FinalizerCompleted("$ORIGIN\n")
        if "--remove-section" in args:
            shutil.copy2(args[-2], args[-1])
            return FinalizerCompleted()
        if "sign" in args:
            shutil.copy2(args[args.index("-inFile") + 1], args[args.index("-outFile") + 1])
            return FinalizerCompleted()
        return FinalizerCompleted()

    finalizer.preflight = lambda _java_home, tools=None: {
        "objcopy": "objcopy",
        "patchelf": "patchelf",
        "readelf": "readelf",
        "signer": "signer",
    }
    finalizer.is_elf = lambda path: Path(path).is_file()
    finalizer.rewrite_elf = lambda _path: None
    finalizer.inspect_elf = lambda _path: {
        "needed": ["libg.so"],
        "version_files": [],
        "interpreter": "/lib/ld-musl-aarch64.so.1",
    }
    finalizer._codesign_size = lambda _path, _tools, _scratch: 1
    finalizer._run = fake_run
    return saved


def restore_finalizer_test_doubles(finalizer, saved):
    for name, value in saved.items():
        setattr(finalizer, name, value)


def test_finalizer_regular_stage_replacement(wrapper, finalizer, root):
    work = root / "finalizer-regular-stage-replacement"
    reset_directory(work)
    java_home = work / "java-home"
    (java_home / "lib").mkdir(parents=True)
    (java_home / "lib" / "libg.so").write_bytes(b"libg")
    target = work / "output"
    target.write_bytes(b"original-elf")
    target_identity = wrapper._destination_identity(target)
    replacement = work / "replacement"
    replacement.write_bytes(b"replacement-elf")
    replacement_identity = wrapper._destination_identity(replacement)
    replacement_injected = False
    failure = None

    class Completed:
        def __init__(self, stdout=""):
            self.stdout = stdout

    saved = {
        "preflight": finalizer.preflight,
        "is_elf": finalizer.is_elf,
        "rewrite_elf": finalizer.rewrite_elf,
        "inspect_elf": finalizer.inspect_elf,
        "_codesign_size": finalizer._codesign_size,
        "_run": finalizer._run,
    }

    def fake_run(arguments, _description):
        nonlocal replacement_injected
        args = [str(argument) for argument in arguments]
        if not replacement_injected:
            replacement.replace(target)
            replacement_injected = True
        if "--print-rpath" in args:
            return Completed("$ORIGIN\n")
        if "--remove-section" in args:
            shutil.copy2(args[-2], args[-1])
            return Completed()
        if "sign" in args:
            shutil.copy2(args[args.index("-inFile") + 1], args[args.index("-outFile") + 1])
            return Completed()
        return Completed()

    finalizer.preflight = lambda _java_home, tools=None: {
        "objcopy": "objcopy",
        "patchelf": "patchelf",
        "readelf": "readelf",
        "signer": "signer",
    }
    finalizer.is_elf = lambda path: Path(path).is_file()
    finalizer.rewrite_elf = lambda _path: None
    finalizer.inspect_elf = lambda _path: {
        "needed": ["libg.so"],
        "version_files": [],
        "interpreter": "/lib/ld-musl-aarch64.so.1",
    }
    finalizer._codesign_size = lambda _path, _tools, _scratch: 1
    finalizer._run = fake_run
    try:
        try:
            finalizer.finalize(target, java_home, expected_identity=target_identity)
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        for name, value in saved.items():
            setattr(finalizer, name, value)

    require(
        failure is not None and "output changed before install" in str(failure),
        "finalizer accepted a replaced stage file",
    )
    require(replacement_injected, "finalizer replacement was not injected")
    require(target.read_bytes() == b"replacement-elf", "finalizer changed replacement content")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(target),
            replacement_identity,
        ),
        "finalizer changed replacement identity",
    )
    require(
        not list(work.glob(".output.ohos-finalize-*")),
        "finalizer temporary files leaked after replacement",
    )


def test_finalizer_signed_output_replacement(wrapper, finalizer, root):
    work = root / "finalizer-signed-output-replacement"
    reset_directory(work)
    target = work / "output"
    target.write_bytes(b"original-output")
    signed = work / "signed-output"
    signed.write_bytes(b"signed-output")
    replacement = work / "replacement-signed-output"
    replacement.write_bytes(b"replacement-signed-output")
    target_identity = wrapper._destination_identity(target)
    target_parent_descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    finalizer_target_identity = finalizer._identity_at(
        target_parent_descriptor,
        target.name,
        "Native Image output",
    )
    replacement_identity = wrapper._destination_identity(replacement)
    replacement_injected = False
    failure = None
    saved_exchange = finalizer._rename_exchange_at

    def fake_exchange(left_dir_fd, left_name, right_dir_fd, right_name):
        nonlocal replacement_injected
        if not replacement_injected and left_name == signed.name and right_name == target.name:
            replacement.replace(signed)
            replacement_injected = True
        return saved_exchange(left_dir_fd, left_name, right_dir_fd, right_name)

    finalizer._rename_exchange_at = fake_exchange
    try:
        try:
            finalizer._install_signed_output(
                signed,
                target,
                target_parent_descriptor,
                finalizer_target_identity,
            )
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        finalizer._rename_exchange_at = saved_exchange
        os.close(target_parent_descriptor)

    recovery_paths = list(work.glob("signed-output.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        "finalizer accepted a replaced signed output",
    )
    require(replacement_injected, "signed output replacement was not injected")
    require(target.read_bytes() == b"replacement-signed-output", "replacement target changed")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(target),
            replacement_identity,
        ),
        "replacement target identity changed",
    )
    require(len(recovery_paths) == 1, "old output recovery file was not retained")
    require(recovery_paths[0].read_bytes() == b"original-output", "old output recovery content changed")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        "old output recovery identity changed",
    )
    require(not signed.exists(), "backup path stayed in the cleanup set")


def test_finalizer_rollback_target_replacement(wrapper, finalizer, root):
    work = root / "finalizer-rollback-target-replacement"
    reset_directory(work)
    target = work / "output"
    target.write_bytes(b"original-output")
    signed = work / "signed-output"
    signed.write_bytes(b"signed-output")
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"concurrent-output")
    target_identity = wrapper._destination_identity(target)
    replacement_identity = wrapper._destination_identity(replacement)
    target_parent_descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    finalizer_target_identity = finalizer._identity_at(
        target_parent_descriptor,
        target.name,
        "Native Image output",
    )
    finalizer_signed_identity = finalizer._identity_at(
        target_parent_descriptor,
        signed.name,
        "signed Native Image output",
    )
    failure = None
    try:
        finalizer._rename_exchange_at(
            target_parent_descriptor,
            signed.name,
            target_parent_descriptor,
            target.name,
        )
        replacement.replace(target)
        try:
            finalizer._rollback_signed_exchange(
                target_parent_descriptor,
                signed,
                target,
                finalizer_signed_identity,
                finalizer_target_identity,
            )
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        os.close(target_parent_descriptor)

    recovery_paths = list(work.glob("signed-output.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        "finalizer rollback target replacement was accepted",
    )
    require(target.read_bytes() == b"concurrent-output", "concurrent target changed")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(target),
            replacement_identity,
        ),
        "concurrent target identity changed",
    )
    require(len(recovery_paths) == 1, "old output recovery file was not retained")
    require(recovery_paths[0].read_bytes() == b"original-output", "old output recovery content changed")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        "old output recovery identity changed",
    )
    require(not signed.exists(), "backup path stayed in the cleanup set")


def test_finalizer_rollback_target_identity_error(wrapper, finalizer, root):
    work = root / "finalizer-rollback-target-identity-error"
    reset_directory(work)
    target = work / "output"
    target.write_bytes(b"original-output")
    signed = work / "signed-output"
    signed.write_bytes(b"signed-output")
    replacement = work / "concurrent-output"
    replacement.write_bytes(b"concurrent-output")
    target_identity = wrapper._destination_identity(target)
    replacement_identity = wrapper._destination_identity(replacement)
    target_parent_descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    finalizer_target_identity = finalizer._identity_at(
        target_parent_descriptor,
        target.name,
        "Native Image output",
    )
    finalizer_signed_identity = finalizer._identity_at(
        target_parent_descriptor,
        signed.name,
        "signed Native Image output",
    )
    saved_identity_at = finalizer._identity_at
    failure = None

    def fake_identity_at(parent_descriptor, name, description):
        if name == target.name and description == "installed Native Image output":
            raise finalizer.FinalizeError(
                "installed Native Image output must not be a symlink"
            )
        return saved_identity_at(parent_descriptor, name, description)

    try:
        finalizer._rename_exchange_at(
            target_parent_descriptor,
            signed.name,
            target_parent_descriptor,
            target.name,
        )
        replacement.replace(target)
        finalizer._identity_at = fake_identity_at
        try:
            finalizer._rollback_signed_exchange(
                target_parent_descriptor,
                signed,
                target,
                finalizer_signed_identity,
                finalizer_target_identity,
            )
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        finalizer._identity_at = saved_identity_at
        os.close(target_parent_descriptor)

    recovery_paths = list(work.glob("signed-output.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        "finalizer rollback target identity error was accepted",
    )
    require(target.read_bytes() == b"concurrent-output", "identity-error target changed")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(target),
            replacement_identity,
        ),
        "identity-error target identity changed",
    )
    require(len(recovery_paths) == 1, "identity-error recovery was not retained")
    require(
        recovery_paths[0].read_bytes() == b"original-output",
        "identity-error recovery content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        "identity-error recovery identity changed",
    )
    require(not signed.exists(), "identity-error backup path stayed in the cleanup set")


def test_finalizer_rollback_target_symlink_replacement(wrapper, finalizer, root):
    work = root / "finalizer-rollback-target-symlink-replacement"
    reset_directory(work)
    target = work / "output"
    target.write_bytes(b"original-output")
    signed = work / "signed-output"
    signed.write_bytes(b"signed-output")
    sentinel = work / "sentinel"
    sentinel.write_bytes(b"sentinel")
    replacement = work / "concurrent-output-link"
    try:
        replacement.symlink_to(sentinel.name)
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP):
            return 8
        raise
    target_identity = wrapper._destination_identity(target)
    target_parent_descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    finalizer_target_identity = finalizer._identity_at(
        target_parent_descriptor,
        target.name,
        "Native Image output",
    )
    finalizer_signed_identity = finalizer._identity_at(
        target_parent_descriptor,
        signed.name,
        "signed Native Image output",
    )
    failure = None
    try:
        finalizer._rename_exchange_at(
            target_parent_descriptor,
            signed.name,
            target_parent_descriptor,
            target.name,
        )
        replacement.replace(target)
        try:
            finalizer._rollback_signed_exchange(
                target_parent_descriptor,
                signed,
                target,
                finalizer_signed_identity,
                finalizer_target_identity,
            )
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        os.close(target_parent_descriptor)

    recovery_paths = list(work.glob("signed-output.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        "finalizer rollback target symlink replacement was accepted",
    )
    require(target.is_symlink(), "concurrent target symlink was removed")
    require(os.readlink(target) == sentinel.name, "concurrent target symlink changed")
    require(sentinel.read_bytes() == b"sentinel", "concurrent symlink referent changed")
    require(len(recovery_paths) == 1, "old output symlink-race recovery was not retained")
    require(
        recovery_paths[0].read_bytes() == b"original-output",
        "old output symlink-race recovery content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        "old output symlink-race recovery identity changed",
    )
    require(not signed.exists(), "symlink-race backup path stayed in the cleanup set")
    return 0


def test_finalizer_post_install_target_replacement(wrapper, finalizer, root, symlink):
    label = "symlink" if symlink else "regular"
    work = root / f"finalizer-post-install-target-replacement-{label}"
    reset_directory(work)
    java_home = work / "java-home"
    (java_home / "lib").mkdir(parents=True)
    (java_home / "lib" / "libg.so").write_bytes(b"libg")
    target = work / "output"
    target.write_bytes(b"original-output")
    target_identity = wrapper._destination_identity(target)
    sentinel = work / "sentinel"
    replacement = work / "concurrent-output"
    if symlink:
        sentinel.write_bytes(b"sentinel")
        try:
            replacement.symlink_to(sentinel.name)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP):
                return 9
            raise
    else:
        replacement.write_bytes(b"concurrent-output")
        replacement_identity = wrapper._destination_identity(replacement)

    saved = install_finalizer_test_doubles(finalizer)
    saved["_install_signed_output"] = finalizer._install_signed_output
    replacement_injected = False
    failure = None

    def fake_install_signed_output(signed, target_path, parent_descriptor, identity):
        nonlocal replacement_injected
        signed_sha = saved["_install_signed_output"](
            signed,
            target_path,
            parent_descriptor,
            identity,
        )
        replacement.replace(target)
        replacement_injected = True
        return signed_sha

    finalizer._install_signed_output = fake_install_signed_output
    try:
        try:
            finalizer.finalize(target, java_home, expected_identity=target_identity)
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        restore_finalizer_test_doubles(finalizer, saved)

    recovery_paths = list(work.glob(".output.ohos-finalize-*.signed.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        f"post-install {label} target replacement was accepted",
    )
    require(replacement_injected, f"post-install {label} replacement was not injected")
    if symlink:
        require(target.is_symlink(), "post-install target symlink was removed")
        require(os.readlink(target) == sentinel.name, "post-install target symlink changed")
        require(sentinel.read_bytes() == b"sentinel", "post-install symlink referent changed")
    else:
        require(target.read_bytes() == b"concurrent-output", "post-install target changed")
        require(
            wrapper._same_preserved_identity(
                wrapper._destination_identity(target),
                replacement_identity,
            ),
            "post-install target identity changed",
        )
    require(len(recovery_paths) == 1, f"post-install {label} recovery was not retained")
    require(
        recovery_paths[0].read_bytes() == b"original-output",
        f"post-install {label} recovery content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        f"post-install {label} recovery identity changed",
    )
    require(
        not list(work.glob(".output.ohos-finalize-*.signed")),
        f"post-install {label} signed backup stayed in the cleanup set",
    )
    return 0


def test_finalizer_post_install_directory_fsync_failure(wrapper, finalizer, root):
    work = root / "finalizer-post-install-directory-fsync-failure"
    reset_directory(work)
    java_home = work / "java-home"
    (java_home / "lib").mkdir(parents=True)
    (java_home / "lib" / "libg.so").write_bytes(b"libg")
    target = work / "output"
    target.write_bytes(b"original-output")
    target_identity = wrapper._destination_identity(target)

    saved = install_finalizer_test_doubles(finalizer)
    saved["_install_signed_output"] = finalizer._install_signed_output
    saved["_fsync_directory_descriptor"] = finalizer._fsync_directory_descriptor
    post_install = False
    fsync_injected = False
    failure = None

    def fake_install_signed_output(signed, target_path, parent_descriptor, identity):
        nonlocal post_install
        signed_sha = saved["_install_signed_output"](
            signed,
            target_path,
            parent_descriptor,
            identity,
        )
        post_install = True
        return signed_sha

    def fake_fsync_directory_descriptor(descriptor):
        nonlocal fsync_injected
        if post_install and not fsync_injected:
            fsync_injected = True
            raise OSError(errno.EIO, "injected post-install fsync failure")
        return saved["_fsync_directory_descriptor"](descriptor)

    finalizer._install_signed_output = fake_install_signed_output
    finalizer._fsync_directory_descriptor = fake_fsync_directory_descriptor
    try:
        try:
            finalizer.finalize(target, java_home, expected_identity=target_identity)
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        restore_finalizer_test_doubles(finalizer, saved)

    recovery_paths = list(work.glob(".output.ohos-finalize-*.signed.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        "post-install directory fsync failure was accepted",
    )
    require(fsync_injected, "post-install directory fsync failure was not injected")
    require(target.read_bytes() == b"original-output", "post-install fsync changed target")
    require(len(recovery_paths) == 1, "post-install fsync recovery was not retained")
    require(
        recovery_paths[0].read_bytes() == b"original-output",
        "post-install fsync recovery content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        "post-install fsync recovery identity changed",
    )
    require(
        not list(work.glob(".output.ohos-finalize-*.signed")),
        "post-install fsync signed backup stayed in the cleanup set",
    )


def test_finalizer_post_install_fsync_replacement(wrapper, finalizer, root, symlink):
    label = "symlink" if symlink else "regular"
    work = root / f"finalizer-post-install-fsync-replacement-{label}"
    reset_directory(work)
    java_home = work / "java-home"
    (java_home / "lib").mkdir(parents=True)
    (java_home / "lib" / "libg.so").write_bytes(b"libg")
    target = work / "output"
    target.write_bytes(b"original-output")
    target_identity = wrapper._destination_identity(target)
    sentinel = work / "sentinel"
    replacement = work / "same-byte-concurrent-output"
    if symlink:
        sentinel.write_bytes(b"original-output")
        try:
            replacement.symlink_to(sentinel.name)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP):
                return 9
            raise
    else:
        replacement.write_bytes(b"original-output")
        replacement_identity = wrapper._destination_identity(replacement)

    saved = install_finalizer_test_doubles(finalizer)
    saved["_install_signed_output"] = finalizer._install_signed_output
    saved["_fsync_directory_descriptor"] = finalizer._fsync_directory_descriptor
    post_install = False
    replacement_injected = False
    failure = None

    def fake_install_signed_output(signed, target_path, parent_descriptor, identity):
        nonlocal post_install
        signed_sha = saved["_install_signed_output"](
            signed,
            target_path,
            parent_descriptor,
            identity,
        )
        post_install = True
        return signed_sha

    def fake_fsync_directory_descriptor(descriptor):
        nonlocal replacement_injected
        if post_install and not replacement_injected:
            replacement.replace(target)
            replacement_injected = True
        return saved["_fsync_directory_descriptor"](descriptor)

    finalizer._install_signed_output = fake_install_signed_output
    finalizer._fsync_directory_descriptor = fake_fsync_directory_descriptor
    try:
        try:
            finalizer.finalize(target, java_home, expected_identity=target_identity)
        except finalizer.FinalizeError as exc:
            failure = exc
    finally:
        restore_finalizer_test_doubles(finalizer, saved)

    recovery_paths = list(work.glob(".output.ohos-finalize-*.signed.ohos-recovery-*"))
    require(
        failure is not None and "previous output retained" in str(failure),
        f"post-install fsync {label} replacement was accepted",
    )
    require(
        replacement_injected,
        f"post-install fsync {label} replacement was not injected",
    )
    if symlink:
        require(target.is_symlink(), "post-install fsync target symlink was removed")
        require(
            os.readlink(target) == sentinel.name,
            "post-install fsync target symlink changed",
        )
        require(
            sentinel.read_bytes() == b"original-output",
            "post-install fsync symlink referent changed",
        )
    else:
        require(
            target.read_bytes() == b"original-output",
            "post-install fsync same-byte target content changed",
        )
        require(
            wrapper._same_preserved_identity(
                wrapper._destination_identity(target),
                replacement_identity,
            ),
            "post-install fsync same-byte target identity changed",
        )
    require(
        len(recovery_paths) == 1,
        f"post-install fsync {label} recovery was not retained",
    )
    require(
        recovery_paths[0].read_bytes() == b"original-output",
        f"post-install fsync {label} recovery content changed",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(recovery_paths[0]),
            target_identity,
        ),
        f"post-install fsync {label} recovery identity changed",
    )
    require(
        not list(work.glob(".output.ohos-finalize-*.signed")),
        f"post-install fsync {label} signed backup stayed in the cleanup set",
    )
    return 0


def test_finalizer_signed_output_install(wrapper, finalizer, root):
    work = root / "finalizer-signed-output-install"
    reset_directory(work)
    target = work / "output"
    target.write_bytes(b"original-output")
    signed = work / "signed-output"
    signed.write_bytes(b"signed-output")
    target_identity = wrapper._destination_identity(target)
    signed_identity = wrapper._destination_identity(signed)
    target_parent_descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    finalizer_target_identity = finalizer._identity_at(
        target_parent_descriptor,
        target.name,
        "Native Image output",
    )
    try:
        installed_sha = finalizer._install_signed_output(
            signed,
            target,
            target_parent_descriptor,
            finalizer_target_identity,
        )
    finally:
        os.close(target_parent_descriptor)

    require(installed_sha == signed_identity.sha256, "installed signed output hash mismatch")
    require(target.read_bytes() == b"signed-output", "signed output was not installed")
    require(signed.read_bytes() == b"original-output", "original output was not retained")
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(target),
            signed_identity,
        ),
        "installed signed output identity was not preserved",
    )
    require(
        wrapper._same_preserved_identity(
            wrapper._destination_identity(signed),
            target_identity,
        ),
        "retained original output identity was not preserved",
    )


def test_post_commit_fsync_failure(wrapper, root, existing):
    label = "existing" if existing else "new"
    work = root / f"post-commit-fsync-{label}"
    reset_directory(work)
    destination = work / "output"
    expected_output = b"old-output" if existing else None
    if expected_output is not None:
        destination.write_bytes(expected_output)
    destination_identity = wrapper._destination_identity(destination)
    libg_source = work / "libg-source"
    libg_source.write_bytes(b"signed-libg")
    state = wrapper._SignalExitState()
    real_fsync_directory = wrapper._fsync_directory_descriptor
    real_noreplace = wrapper._rename_noreplace_at
    real_exchange = wrapper._rename_exchange_at
    fsync_calls = 0
    target_replaced = False
    failure_injected = False
    failure = None

    def observing_noreplace(source_fd, source_name, target_fd, target_name):
        nonlocal target_replaced
        result = real_noreplace(source_fd, source_name, target_fd, target_name)
        if target_name == destination.name and not target_replaced:
            target_replaced = True
        return result

    def observing_exchange(left_fd, left_name, right_fd, right_name):
        nonlocal target_replaced
        result = real_exchange(left_fd, left_name, right_fd, right_name)
        if right_name == destination.name and not target_replaced:
            target_replaced = True
        return result

    def injecting_fsync_directory(descriptor):
        nonlocal failure_injected, fsync_calls
        fsync_calls += 1
        if target_replaced and not failure_injected:
            failure_injected = True
            raise OSError("injected post-commit directory fsync failure")
        return real_fsync_directory(descriptor)

    wrapper._fsync_directory_descriptor = injecting_fsync_directory
    wrapper._rename_noreplace_at = observing_noreplace
    wrapper._rename_exchange_at = observing_exchange
    try:
        with wrapper._staged_output(destination, state) as staged:
            staged.write_bytes(b"new-output")
            with wrapper._staged_libg(
                libg_source,
                work,
                sha256(libg_source),
                state,
            ) as staged_libg:
                wrapper._commit_output(
                    staged,
                    destination,
                    destination_identity,
                    staged_libg,
                    sha256(staged_libg),
                    state,
                    sha256(staged),
                )
    except OSError as exc:
        failure = exc
    finally:
        wrapper._fsync_directory_descriptor = real_fsync_directory
        wrapper._rename_noreplace_at = real_noreplace
        wrapper._rename_exchange_at = real_exchange

    actual_output = destination.read_bytes() if destination.exists() else None
    require(
        str(failure) == "injected post-commit directory fsync failure",
        f"{label} output did not surface the injected fsync failure",
    )
    require(failure_injected, f"{label} post-commit failure was not injected")
    require(not state.committed, f"{label} failed commit was marked committed")
    require(actual_output == expected_output, f"{label} output rollback mismatch")
    require(
        (actual_output is None and destination_identity is None)
        or wrapper._same_preserved_identity(
            wrapper._destination_identity(destination), destination_identity
        ),
        f"{label} output metadata identity was not restored",
    )
    require(not (work / "libg.so").exists(), f"{label} libg.so leaked")
    require(
        not list(work.glob(".*.graalvm-ohos-stage-*")),
        f"{label} stage leaked",
    )
    require(
        not list(work.glob(".*.graalvm-ohos-backup-*")),
        f"{label} backup leaked",
    )


def test_existing_libg_replacement(wrapper, root):
    work = root / "existing-libg-replacement"
    reset_directory(work)
    destination = work / "output"
    destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    staged = work / "staged-output"
    staged.write_bytes(b"new-output")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    libg_target = work / "libg.so"
    libg_target.write_bytes(b"signed-libg")
    replacement = work / "concurrent-libg"
    replacement.write_bytes(b"changed-libg")
    state = wrapper._SignalExitState()
    real_fsync_directory = wrapper._fsync_directory_descriptor
    real_exchange = wrapper._rename_exchange_at
    real_replace = wrapper.os.replace
    fsync_calls = 0
    target_replaced = False
    libg_replaced = False
    failure = None

    def observing_exchange(left_fd, left_name, right_fd, right_name):
        nonlocal target_replaced
        result = real_exchange(left_fd, left_name, right_fd, right_name)
        if right_name == destination.name and not target_replaced:
            target_replaced = True
        return result

    def replacing_fsync_directory(descriptor):
        nonlocal fsync_calls, libg_replaced
        fsync_calls += 1
        if target_replaced and not libg_replaced:
            real_replace(replacement, libg_target)
            libg_replaced = True
        return real_fsync_directory(descriptor)

    wrapper._fsync_directory_descriptor = replacing_fsync_directory
    wrapper._rename_exchange_at = observing_exchange
    try:
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._fsync_directory_descriptor = real_fsync_directory
        wrapper._rename_exchange_at = real_exchange

    require(
        failure is not None and "libg.so changed during commit" in str(failure),
        "concurrent existing libg.so replacement was accepted",
    )
    require(libg_replaced, "existing libg.so replacement was not injected")
    require(destination.read_bytes() == b"old-output", "old output was not restored")
    require(libg_target.read_bytes() == b"changed-libg", "concurrent libg.so changed")
    require(not state.committed, "failed existing libg.so commit was marked committed")
    require(not list(work.glob(".*.graalvm-ohos-stage-*")), "libg CAS stage leaked")
    require(not list(work.glob(".*.graalvm-ohos-backup-*")), "libg CAS backup leaked")


def test_existing_libg_untrusted_mode(wrapper, root):
    work = root / "existing-libg-untrusted-mode"
    reset_directory(work)
    destination = work / "output"
    destination.write_bytes(b"old-output")
    destination_identity = wrapper._destination_identity(destination)
    staged = work / "staged-output"
    staged.write_bytes(b"new-output")
    staged_libg = work / "staged-libg"
    staged_libg.write_bytes(b"signed-libg")
    libg_target = work / "libg.so"
    libg_target.write_bytes(b"signed-libg")
    state = wrapper._SignalExitState()
    failure = None
    real_destination_identity_at = wrapper._destination_identity_at

    def injecting_destination_identity_at(directory_fd, name, path):
        identity = real_destination_identity_at(directory_fd, name, path)
        if Path(path) == libg_target and identity is not None:
            return identity.__class__(
                device=identity.device,
                inode=identity.inode,
                size=identity.size,
                mtime_ns=identity.mtime_ns,
                ctime_ns=identity.ctime_ns,
                mode=identity.mode | 0o002,
                uid=identity.uid,
                gid=identity.gid,
                links=identity.links,
                sha256=identity.sha256,
            )
        return identity

    wrapper._destination_identity_at = injecting_destination_identity_at
    try:
        try:
            wrapper._commit_output(
                staged,
                destination,
                destination_identity,
                staged_libg,
                sha256(staged_libg),
                state,
                sha256(staged),
            )
        except RuntimeError as exc:
            failure = exc
    finally:
        wrapper._destination_identity_at = real_destination_identity_at

    require(
        failure is not None and "writable by others" in str(failure),
        "untrusted existing libg.so mode was accepted",
    )
    require(destination.read_bytes() == b"old-output", "untrusted libg changed output")
    require(libg_target.read_bytes() == b"signed-libg", "untrusted libg content changed")
    require(not state.committed, "untrusted libg failure was marked committed")
    require(not list(work.glob(".*.graalvm-ohos-stage-*")), "untrusted libg stage leaked")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} WRAPPER WORK")
    wrapper = load_wrapper(Path(sys.argv[1]))
    root = Path(sys.argv[2])
    reset_directory(root)
    signals = (
        (signal.SIGHUP, "hup"),
        (signal.SIGINT, "int"),
        (signal.SIGTERM, "term"),
    )

    for signum, label in signals:
        test_stage_signal(wrapper, root, signum, label)
    for phase in ("sidecar", "exchange-before", "exchange-after"):
        for signum, label in signals:
            test_commit_signal(wrapper, root, signum, label, phase)
    test_post_finalize_destination_change(wrapper, root)

    if ASSERTIONS != 62:
        raise AssertionError(f"unexpected assertion count: {ASSERTIONS}")
    print(f"NATIVE_IMAGE_TRANSACTION_SIGNAL_ASSERTIONS={ASSERTIONS}/{ASSERTIONS}")

    before_output_cas = ASSERTIONS
    test_post_finalize_stage_file_replacement(wrapper, root)
    test_post_finalize_stage_directory_replacement(wrapper, root)
    for existing in (False, True):
        test_pre_publish_output_stage_directory_replacement(wrapper, root, existing)
    for existing in (False, True):
        test_post_publish_destination_replacement(wrapper, root, existing)
    test_exchange_rollback_quarantine_race(wrapper, root)
    test_noreplace_rollback_check_race(wrapper, root)
    output_cas_assertions = ASSERTIONS - before_output_cas
    if output_cas_assertions != 49:
        raise AssertionError(
            f"unexpected output CAS assertion count: {output_cas_assertions}"
        )
    print(
        "NATIVE_IMAGE_OUTPUT_CAS_ASSERTIONS="
        f"{output_cas_assertions}/{output_cas_assertions}"
    )

    before_cleanup_cas = ASSERTIONS
    test_output_cleanup_identity_race(wrapper, root)
    test_scratch_cleanup_identity_race(wrapper, root)
    test_lock_path_canonicalization(wrapper, root)
    test_locked_destination_parent_replacement(wrapper, root)
    cleanup_cas_assertions = ASSERTIONS - before_cleanup_cas
    if cleanup_cas_assertions != 27:
        raise AssertionError(
            f"unexpected cleanup CAS assertion count: {cleanup_cas_assertions}"
        )
    print(
        "NATIVE_IMAGE_CLEANUP_CAS_ASSERTIONS="
        f"{cleanup_cas_assertions}/{cleanup_cas_assertions}"
    )

    before_finalizer_cas = ASSERTIONS
    finalizer = load_finalizer(Path(sys.argv[1]), wrapper)
    test_finalizer_regular_stage_replacement(wrapper, finalizer, root)
    test_finalizer_signed_output_replacement(wrapper, finalizer, root)
    test_finalizer_rollback_target_replacement(wrapper, finalizer, root)
    test_finalizer_rollback_target_identity_error(wrapper, finalizer, root)
    finalizer_symlink_skips = 0
    finalizer_symlink_skips += test_finalizer_rollback_target_symlink_replacement(
        wrapper,
        finalizer,
        root,
    )
    test_finalizer_post_install_target_replacement(wrapper, finalizer, root, False)
    finalizer_symlink_skips += test_finalizer_post_install_target_replacement(
        wrapper,
        finalizer,
        root,
        True,
    )
    test_finalizer_post_install_directory_fsync_failure(wrapper, finalizer, root)
    test_finalizer_post_install_fsync_replacement(wrapper, finalizer, root, False)
    finalizer_symlink_skips += test_finalizer_post_install_fsync_replacement(
        wrapper,
        finalizer,
        root,
        True,
    )
    test_finalizer_signed_output_install(wrapper, finalizer, root)
    finalizer_cas_assertions = ASSERTIONS - before_finalizer_cas
    expected_finalizer_cas = 81 - finalizer_symlink_skips
    if finalizer_cas_assertions != expected_finalizer_cas:
        raise AssertionError(
            f"unexpected finalizer CAS assertion count: {finalizer_cas_assertions}"
        )
    print(
        "NATIVE_IMAGE_FINALIZER_CAS_ASSERTIONS="
        f"{finalizer_cas_assertions}/{finalizer_cas_assertions}"
    )
    print(
        "NATIVE_IMAGE_FINALIZER_SYMLINK_SKIPPED_ASSERTIONS="
        f"{finalizer_symlink_skips}"
    )

    before_rollback = ASSERTIONS
    for existing in (False, True):
        test_post_commit_fsync_failure(wrapper, root, existing)
    rollback_assertions = ASSERTIONS - before_rollback
    if rollback_assertions != 16:
        raise AssertionError(
            f"unexpected rollback assertion count: {rollback_assertions}"
        )
    print(
        "NATIVE_IMAGE_TRANSACTION_ROLLBACK_ASSERTIONS="
        f"{rollback_assertions}/{rollback_assertions}"
    )

    before_libg_cas = ASSERTIONS
    test_pre_publish_libg_stage_directory_replacement(wrapper, root)
    test_existing_libg_replacement(wrapper, root)
    test_existing_libg_untrusted_mode(wrapper, root)
    libg_cas_assertions = ASSERTIONS - before_libg_cas
    if libg_cas_assertions != 19:
        raise AssertionError(
            f"unexpected libg CAS assertion count: {libg_cas_assertions}"
        )
    print(
        "NATIVE_IMAGE_LIBG_CAS_ASSERTIONS="
        f"{libg_cas_assertions}/{libg_cas_assertions}"
    )


if __name__ == "__main__":
    main()
