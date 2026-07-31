#!/usr/bin/env python3
"""Validate libffi's official-archive test discovery and fail-closed gates."""

from __future__ import annotations

import argparse
import ast
import copy
import io
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import shlex
import subprocess
import sys
import tarfile
import tempfile

import run_upstream_tests as upstream


MUTATION_MEMBER = "libffi-3.5.2/testsuite/libffi.call/align_mixed.c"


def replace_exact_root(content: str, old: str, new: str, expected: int) -> str:
    actual = content.count(old)
    if actual != expected:
        raise ValueError(f"expected {expected} roots, found {actual}")
    result = content.replace(old, new)
    if old in result:
        raise AssertionError("root replacement residue")
    return result


def assert_recipe_regeneration_gate(recipe: Path) -> None:
    tree = ast.parse(recipe.read_text(encoding="utf-8"), filename=str(recipe))
    expected = {
        "MAKE=make",
        "AUTOCONF=true",
        "AUTOHEADER=true",
        "AUTOMAKE=true",
        "ACLOCAL=true",
    }
    gate_values: set[str] = set()
    guarded_calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_no_autotools_regeneration"
                for target in node.targets
            ) and isinstance(node.value, (ast.Tuple, ast.List)):
                gate_values = {
                    element.value
                    for element in node.value.elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                }
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr not in {"make", "install"}:
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "args"
                    and isinstance(keyword.value, ast.Call)
                    and isinstance(keyword.value.func, ast.Attribute)
                    and keyword.value.func.attr == "_autotools_make_args"
                ):
                    guarded_calls.add(node.func.attr)
    if not expected.issubset(gate_values):
        raise AssertionError(
            f"recipe is missing regeneration gates: {sorted(expected - gate_values)}"
        )
    if not any(
        isinstance(node, ast.Constant) and node.value == 946684800
        for node in ast.walk(tree)
    ):
        raise AssertionError("recipe is missing the deterministic release timestamp baseline")
    source_text = recipe.read_text(encoding="utf-8")
    if "source_root = Path(self.source_folder).as_posix().rstrip" not in source_text:
        raise AssertionError("recipe does not bind make guards to native Makefile paths")
    if "PurePosixPath(relative).as_posix()" not in source_text:
        raise AssertionError("recipe does not preserve release target filename case")
    if 'return ["--environment-overrides"] + [' not in source_text:
        raise AssertionError("recipe does not give the recursive tool environment priority")
    representative = PureWindowsPath(
        r"E:\HarmonyPC\validation\libffi-3.5.2\representative\configure"
    )
    drive = representative.drive.rstrip(":").lower()
    makefile_target = f"/{drive}/" + "/".join(representative.parts[1:])
    if makefile_target != (
        "/e/HarmonyPC/validation/libffi-3.5.2/representative/configure"
    ):
        raise AssertionError("representative E-drive Makefile path mismatch")
    if 'f"--old-file={build_root}/config.status"' not in source_text:
        raise AssertionError("recipe must protect the configured config.status")
    if source_text.count("with self._autotools_environment().apply():") != 2:
        raise AssertionError("build and install must apply the recursive tool environment")
    if 'environment.define("MAKEFLAGS", "--environment-overrides")' not in source_text:
        raise AssertionError("recipe does not propagate path guards through recursive make")
    if 'environment.define("MAKE", "make " + " ".join(self._autotools_make_args()))' not in source_text:
        raise AssertionError("recipe does not bind recursive make to all path guards")
    expected_counts = {
        "config.status": 13,
        "Makefile": 11,
        "include/Makefile": 11,
        "testsuite/Makefile": 11,
        "man/Makefile": 11,
        "doc/Makefile": 11,
    }
    for relative, count in expected_counts.items():
        token = f'"{relative}": {count}'
        if token not in source_text:
            raise AssertionError(f"recipe is missing configured path count {token}")
    old_root = "/e/example/source"
    new_root = "E:/example/source"
    exact = "\n".join([old_root] * 11)
    if replace_exact_root(exact, old_root, new_root, 11).count(new_root) != 11:
        raise AssertionError("exact configured path replacement failed")
    for mutated in ("\n".join([old_root] * 10), "\n".join([old_root] * 12)):
        try:
            replace_exact_root(mutated, old_root, new_root, 11)
        except ValueError:
            pass
        else:
            raise AssertionError("configured path count mutation was accepted")
    if "if self._source_content_digest() != source_digest:" not in source_text:
        raise AssertionError("recipe does not preserve source content around normalization")
    shell = shutil.which("sh")
    if shell is None:
        raise AssertionError("sh is required for recursive make command validation")
    bad_make = subprocess.run(
        [shell, "-n"],
        input=(
            "test -f fficonfig.h || "
            "C:/Program Files (x86)/w64devkit/bin/make.exe stamp-h1\n"
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    good_make = subprocess.run(
        [shell, "-n"],
        input="test -f fficonfig.h || make stamp-h1\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if bad_make.returncode == 0 or good_make.returncode != 0:
        raise AssertionError("recursive make shell binding negative case did not hold")
    child_check = (
        "test \"$MAKE\" = make && test \"$AUTOCONF\" = true && "
        "test \"$AUTOHEADER\" = true && test \"$AUTOMAKE\" = true && "
        "test \"$ACLOCAL\" = true"
    )
    nested_command = f"{shlex.quote(shell)} -c {shlex.quote(child_check)}"
    clean_environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"MAKE", "AUTOCONF", "AUTOHEADER", "AUTOMAKE", "ACLOCAL"}
    }
    missing_environment = subprocess.run(
        [shell, "-c", nested_command],
        env=clean_environment,
        capture_output=True,
        check=False,
    )
    recursive_environment = dict(clean_environment)
    recursive_environment.update(
        {
            "MAKE": "make",
            "AUTOCONF": "true",
            "AUTOHEADER": "true",
            "AUTOMAKE": "true",
            "ACLOCAL": "true",
        }
    )
    inherited_environment = subprocess.run(
        [shell, "-c", nested_command],
        env=recursive_environment,
        capture_output=True,
        check=False,
    )
    if missing_environment.returncode == 0 or inherited_environment.returncode != 0:
        raise AssertionError("recursive tool environment inheritance case did not hold")
    make = shutil.which("make")
    if make is None:
        raise AssertionError("make is required for recursive override validation")
    with tempfile.TemporaryDirectory(prefix="libffi-make-env-validation-") as make_tmp:
        make_root = Path(make_tmp)
        (make_root / "Makefile").write_text(
            "AUTOCONF=from-parent-makefile\n"
            "all:\n"
            "\t$(MAKE) -f child.mk check\n",
            encoding="ascii",
        )
        (make_root / "child.mk").write_text(
            "AUTOCONF=from-child-makefile\n"
            "check: $(CURDIR)/generated\n"
            "\t@test \"$(AUTOCONF)\" = true\n"
            "$(CURDIR)/generated:\n"
            "\t@false\n",
            encoding="ascii",
        )
        make_environment = dict(clean_environment)
        make_environment.update({"MAKE": "make", "AUTOCONF": "true"})
        make_without_override = subprocess.run(
            [make, "-f", "Makefile"],
            cwd=make_root,
            env=make_environment,
            capture_output=True,
            check=False,
        )
        guarded_environment = dict(make_environment)
        guarded_environment["MAKEFLAGS"] = "--environment-overrides"
        guarded_environment["MAKE"] = (
            "make --environment-overrides "
            f"--old-file={make_root.as_posix()}/generated"
        )
        make_with_override = subprocess.run(
            [make, "-f", "Makefile"],
            cwd=make_root,
            env=guarded_environment,
            capture_output=True,
            check=False,
        )
        if make_without_override.returncode == 0 or make_with_override.returncode != 0:
            raise AssertionError(
                "recursive make environment override case did not hold: "
                f"without={make_without_override.returncode} "
                f"with={make_with_override.returncode} "
                f"stderr={make_with_override.stderr!r}"
            )
    if guarded_calls != {"make", "install"}:
        raise AssertionError(
            f"recipe must guard make and install, found {sorted(guarded_calls)}"
        )
    build_method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "build"
    )
    refresh_lines = [
        node.lineno
        for node in ast.walk(build_method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_refresh_generated_timestamps"
    ]
    configure_lines = [
        node.lineno
        for node in ast.walk(build_method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "configure"
    ]
    if len(refresh_lines) != 1 or len(configure_lines) != 1:
        raise AssertionError("recipe must prepare timestamps once before one configure")
    if refresh_lines[0] >= configure_lines[0]:
        raise AssertionError("timestamp preparation must run before configure")


def rewrite_archive(source: Path, destination: Path, mutation: str) -> None:
    found = False
    with tarfile.open(source, mode="r:gz") as incoming:
        with tarfile.open(destination, mode="w:gz") as outgoing:
            for original in incoming.getmembers():
                if original.name == MUTATION_MEMBER and mutation == "missing":
                    found = True
                    continue
                member = copy.copy(original)
                if original.isfile():
                    extracted = incoming.extractfile(original)
                    if extracted is None:
                        raise AssertionError(f"cannot read archive member {original.name}")
                    data = extracted.read()
                    if original.name == MUTATION_MEMBER and mutation == "changed":
                        found = True
                        data += b"\n/* archive binding mutation */\n"
                        member.size = len(data)
                    outgoing.addfile(member, io.BytesIO(data))
                else:
                    outgoing.addfile(member)
            if mutation == "added":
                found = True
                data = b"/* unregistered archive member */\n"
                member = tarfile.TarInfo(
                    "libffi-3.5.2/testsuite/libffi.call/archive_binding_added.c"
                )
                member.mode = 0o644
                member.size = len(data)
                outgoing.addfile(member, io.BytesIO(data))
    if not found:
        raise AssertionError(f"mutation target was not found for {mutation}")


def run_runner(runner: Path, root: Path, archive: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(runner),
            "--root",
            str(root),
            "--archive",
            str(archive),
            "--discovery-only",
            *extra,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_archive_rejected(
    runner: Path, root: Path, archive: Path, label: str
) -> None:
    completed = run_runner(runner, root, archive)
    combined = completed.stdout + completed.stderr
    if completed.returncode == 0:
        raise AssertionError(f"{label}: mutated archive was accepted")
    if "official source archive SHA256 mismatch" not in combined:
        raise AssertionError(f"{label}: unexpected failure: {combined}")
    if "configuration_count" in completed.stdout:
        raise AssertionError(f"{label}: discovery ran before archive rejection")


def write_named_archive(destination: Path, member_name: str) -> None:
    with tarfile.open(destination, mode="w:gz") as bundle:
        root = tarfile.TarInfo("libffi-3.5.2/")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        bundle.addfile(root)
        data = b"archive path validation\n"
        member = tarfile.TarInfo(member_name)
        member.mode = 0o644
        member.size = len(data)
        bundle.addfile(member, io.BytesIO(data))


def assert_member_name_rejected(root: Path, member_name: str, label: str) -> None:
    archive = root / f"path-{label}.tar.gz"
    write_named_archive(archive, member_name)
    original_hash = upstream.EXPECTED_ARCHIVE_SHA256
    upstream.EXPECTED_ARCHIVE_SHA256 = upstream.sha256_file(archive)
    try:
        try:
            with upstream.verified_archive_source(archive, root / "path-work"):
                raise AssertionError(f"{label}: invalid member name was accepted")
        except ValueError as error:
            if "unsafe or duplicate archive member" not in str(error):
                raise AssertionError(f"{label}: unexpected failure: {error}") from error
    finally:
        upstream.EXPECTED_ARCHIVE_SHA256 = original_hash


def assert_static_archive_binding(root: Path) -> None:
    source_root = root / "link-source"
    build_root = root / "link-build"
    library_dir = build_root / ".libs"
    source_root.mkdir()
    library_dir.mkdir(parents=True)
    source = source_root / "binding.c"
    source.write_text("int main(void) { return 0; }\n", encoding="ascii")
    library = library_dir / "libffi.a"
    library.write_bytes(b"verified static archive\n")
    (library_dir / "libffi.so").write_bytes(b"shadow shared library\n")
    test = upstream.TestRun(
        ordinal=1,
        config=upstream.TestConfig(
            category="libffi.call",
            source=source,
            variant="",
            action="run",
            extra_flags=(),
            output_pattern=None,
        ),
        optimization="-O0",
    )
    command = upstream.build_compile_command(
        test,
        source_root,
        build_root,
        library,
        root / "binding.exe",
        "clang",
    )
    if command.count(str(library)) != 1:
        raise AssertionError(f"verified static archive is not linked exactly once: {command}")
    if "-lffi" in command or any(value.startswith("-L") for value in command):
        raise AssertionError(f"linker search could select the shadow shared library: {command}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--runner",
        type=Path,
        default=Path(__file__).with_name("run_upstream_tests.py"),
    )
    args = parser.parse_args()
    archive = args.archive.resolve()
    runner = args.runner.resolve()
    assert_recipe_regeneration_gate(runner.with_name("conanfile.py"))

    with tempfile.TemporaryDirectory(prefix="libffi-runner-validation-") as temporary:
        root = Path(temporary)
        positive = run_runner(runner, root, archive)
        if positive.returncode != 0:
            raise AssertionError(positive.stdout + positive.stderr)
        discovery = json.loads(positive.stdout)
        expected = {
            "configuration_count": 363,
            "configuration_actions": {"compile": 1, "run": 362},
            "directive_occurrences": {"do": 204, "options": 11, "output": 336},
            "execution_actions": {"compile": 2, "run": 724},
            "execution_count": 726,
            "registered_source_count": 204,
            "selector_occurrence_count": 38,
            "source_manifest_byte_count": 5628496,
            "source_manifest_file_count": 455,
            "source_manifest_sha256": (
                "d775c2f867e93855e49efcf4017ebbcbece546eb1b5fe94ada54634687351f5c"
            ),
            "source_archive_sha256": (
                "f3a3082a23b37c293a4fcd1053147b371f2ff91fa7ea1b2a52e335676bac82dc"
            ),
            "source_origin": "verified official archive extraction",
        }
        for key, value in expected.items():
            if discovery.get(key) != value:
                raise AssertionError(
                    f"official discovery mismatch for {key}: {discovery.get(key)!r}"
                )
        for mutation in ("changed", "missing", "added"):
            mutated = root / f"{mutation}.tar.gz"
            rewrite_archive(archive, mutated, mutation)
            assert_archive_rejected(runner, root, mutated, mutation)

        wrong_hash = root / "wrong-hash.tar.gz"
        wrong_hash.write_bytes(archive.read_bytes() + b"archive-hash-mutation")
        assert_archive_rejected(runner, root, wrong_hash, "wrong-hash")

        source_argument = run_runner(runner, root, archive, "--source", str(root))
        if source_argument.returncode == 0 or "unrecognized arguments" not in (
            source_argument.stdout + source_argument.stderr
        ):
            raise AssertionError("the removed --source input was unexpectedly accepted")

        member_name_cases = {
            "dot": "libffi-3.5.2/testsuite/./alias.c",
            "double-separator": "libffi-3.5.2/testsuite//alias.c",
            "parent": "libffi-3.5.2/../../archive-path-outside",
            "backslash": "libffi-3.5.2\\..\\archive-path-outside",
        }
        for label, member_name in member_name_cases.items():
            assert_member_name_rejected(root, member_name, label)
        assert_static_archive_binding(root)
        if (root / "archive-path-outside").exists():
            raise AssertionError("archive member escaped the extraction directory")

        if list(root.rglob("libffi-official-source-*")):
            raise AssertionError("temporary official-source extraction was not cleaned")

    print(
        "PASS official_archive=1 member_mutations=3 hash_gate=1 "
        "external_source_rejected=1 member_names=4 static_archive_binding=1 "
        "autotools_regeneration_gate=2 makefile_path_binding=9 "
        "recursive_make_binding=1 recursive_make_environment=1 discovery=363/726"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
