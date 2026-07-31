#!/usr/bin/env python3
"""Run libffi's registered DejaGNU configurations without runtest."""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import dataclasses
import datetime as dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from collections import Counter


TARGET_TRIPLET = "aarch64-unknown-linux-ohos"
EXPECTED_ARCHIVE_SHA256 = (
    "f3a3082a23b37c293a4fcd1053147b371f2ff91fa7ea1b2a52e335676bac82dc"
)
EXPECTED_CONFIG_COUNTS = {
    "libffi.bhaible": 161,
    "libffi.call": 72,
    "libffi.closures": 99,
    "libffi.complex": 28,
    "libffi.go": 2,
    "libffi.threads": 1,
}
EXPECTED_DIRECTIVES = {"do", "options", "output"}

DIRECTIVE_RE = re.compile(r"\bdg-([A-Za-z0-9_-]+)\b")
DO_RE = re.compile(
    r"\{\s*dg-do\s+(preprocess|compile|assemble|link|run)"
    r"(?:\s+\{\s*(target|xfail)\s+([^{}]+?)\s*\})?\s*\}"
)
OPTIONS_RE = re.compile(
    r"\{\s*dg-options\s+(?:\"((?:\\.|[^\"\\])*)\"|([^\s{}]+))"
    r"(?:\s+\{\s*target\s+([^{}]+?)\s*\})?\s*\}"
)
OUTPUT_RE = re.compile(
    r"\{\s*dg-output\s+\"((?:\\.|[^\"\\])*)\""
    r"(?:\s+\{\s*(target|xfail)\s+([^{}]+?)\s*\})?\s*\}"
)
BHAIBLE_LOOP_RE = re.compile(
    r"set\s+tlist\s+\[lsort\s+\[glob\s+-nocomplain\s+--\s+"
    r"\$srcdir/\$subdir/([A-Za-z0-9_.+-]+)\]\]\s*"
    r"for\s+\{set\s+i\s+(\d+)\}\s+\{\$i\s+<\s+(\d+)\}\s+"
    r"\{incr\s+i\}",
    re.MULTILINE,
)


@dataclasses.dataclass(frozen=True)
class TestConfig:
    category: str
    source: Path
    variant: str
    action: str
    extra_flags: tuple[str, ...]
    output_pattern: str | None


@dataclasses.dataclass(frozen=True)
class TestRun:
    ordinal: int
    config: TestConfig
    optimization: str

    @property
    def name(self) -> str:
        rel = f"{self.config.category}/{self.config.source.name}"
        variant = f"[{self.config.variant}]" if self.config.variant else ""
        return f"{rel}{variant} {self.optimization}"

    @property
    def slug(self) -> str:
        raw = f"{self.config.category}-{self.config.source.stem}"
        if self.config.variant:
            raw += f"-{self.config.variant}"
        raw += f"-{self.optimization.lstrip('-')}"
        clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
        return f"{self.ordinal:04d}-{clean}"


@dataclasses.dataclass(frozen=True)
class ParsedSource:
    action: str
    extra_flags: tuple[str, ...]
    output_pattern: str | None
    expected_xfail: bool
    directive_counts: dict[str, int]
    selector_count: int


@dataclasses.dataclass(frozen=True)
class SourceManifest:
    file_count: int
    byte_count: int
    sha256: str
    lines: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_archive_manifest(
    bundle: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    root_name: str,
) -> SourceManifest:
    entries: list[dict[str, object]] = []
    byte_count = 0
    for member in members:
        if not member.isfile():
            continue
        member_path = PurePosixPath(member.name)
        if len(member_path.parts) < 2 or member_path.parts[0] != root_name:
            raise ValueError(f"unexpected official archive file: {member.name}")
        stream = bundle.extractfile(member)
        if stream is None:
            raise ValueError(f"cannot read official archive member: {member.name}")
        digest = hashlib.sha256()
        size = 0
        with stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        if size != member.size:
            raise ValueError(f"official archive member size mismatch: {member.name}")
        byte_count += size
        entries.append(
            {
                "path": PurePosixPath(*member_path.parts[1:]).as_posix(),
                "sha256": digest.hexdigest(),
                "size": size,
            }
        )
    entries.sort(
        key=lambda entry: (str(entry["path"]).casefold(), str(entry["path"]))
    )
    lines = [
        json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n"
        for entry in entries
    ]
    encoded = "".join(lines).encode("utf-8")
    return SourceManifest(
        file_count=len(lines),
        byte_count=byte_count,
        sha256=hashlib.sha256(encoded).hexdigest(),
        lines=tuple(lines),
    )


@contextlib.contextmanager
def verified_archive_source(archive: Path, work_root: Path):
    if not archive.is_file():
        raise FileNotFoundError(f"missing official source archive: {archive}")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("official source archive SHA256 mismatch")
    work_root.mkdir(parents=True, exist_ok=True)
    extraction_root = None
    for _ in range(16):
        candidate = work_root / f"libffi-official-source-{secrets.token_hex(8)}"
        previous_umask = os.umask(0o022)
        try:
            candidate.mkdir(mode=0o755)
        except FileExistsError:
            continue
        finally:
            os.umask(previous_umask)
        extraction_root = candidate
        break
    if extraction_root is None:
        raise FileExistsError("cannot allocate a unique official-source directory")
    try:
        probe = extraction_root / ".write-probe"
        probe.write_bytes(b"ok\n")
        probe.unlink()
        with tarfile.open(archive, mode="r:gz") as bundle:
            members = bundle.getmembers()
            seen: set[str] = set()
            roots: set[str] = set()
            for member in members:
                normalized = member.name.rstrip("/")
                member_path = PurePosixPath(normalized)
                canonical = member_path.as_posix()
                if (
                    not normalized
                    or "\\" in normalized
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or normalized != canonical
                    or canonical in seen
                ):
                    raise ValueError(f"unsafe or duplicate archive member: {member.name}")
                if not (member.isfile() or member.isdir()):
                    raise ValueError(f"unsupported archive member type: {member.name}")
                seen.add(canonical)
                roots.add(member_path.parts[0])
            if roots != {"libffi-3.5.2"}:
                raise ValueError(f"unexpected official archive roots: {sorted(roots)}")
            manifest = build_archive_manifest(bundle, members, "libffi-3.5.2")
            bundle.extractall(extraction_root, filter="data")
        source_root = extraction_root / "libffi-3.5.2"
        yield source_root, manifest
    finally:
        shutil.rmtree(extraction_root)


def tcl_double_quoted(value: str) -> str:
    result: list[str] = []
    index = 0
    translations = {
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
    }
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            result.append(char)
            index += 1
            continue
        next_char = value[index + 1]
        result.append(translations.get(next_char, next_char))
        index += 2
    return "".join(result)


def selector_matches(selector: str) -> bool:
    patterns = selector.split()
    if patterns == ["gccbug"]:
        return False
    return any(fnmatch.fnmatchcase(TARGET_TRIPLET, pattern) for pattern in patterns)


def parse_source(source: Path) -> ParsedSource:
    text = source.read_text(encoding="utf-8")
    directive_counts = Counter(DIRECTIVE_RE.findall(text))
    unexpected = set(directive_counts) - EXPECTED_DIRECTIVES
    if unexpected:
        raise ValueError(f"{source}: unsupported directives: {sorted(unexpected)}")

    matches = {
        "do": list(DO_RE.finditer(text)),
        "options": list(OPTIONS_RE.finditer(text)),
        "output": list(OUTPUT_RE.finditer(text)),
    }
    for name in EXPECTED_DIRECTIVES:
        if len(matches[name]) != directive_counts[name]:
            raise ValueError(
                f"{source}: parsed {len(matches[name])}/{directive_counts[name]} "
                f"dg-{name} directives"
            )
    applicable_actions: list[str] = []
    expected_xfail = False
    for do_match in matches["do"]:
        selector_type = do_match.group(2)
        selector = do_match.group(3)
        if selector_type == "target" and not selector_matches(selector):
            continue
        applicable_actions.append(do_match.group(1))
        if selector_type == "xfail" and selector_matches(selector):
            expected_xfail = True
    if len(set(applicable_actions)) > 1:
        raise ValueError(f"{source}: conflicting active dg-do actions")
    if matches["do"] and not applicable_actions:
        raise ValueError(f"{source}: no dg-do action applies to {TARGET_TRIPLET}")
    action = applicable_actions[0] if applicable_actions else "compile"

    options: list[str] = []
    for match in matches["options"]:
        selector = match.group(3)
        if selector is not None and not selector_matches(selector):
            continue
        raw = match.group(1) if match.group(1) is not None else match.group(2)
        options.extend(shlex.split(tcl_double_quoted(raw)))

    output_parts: list[str] = []
    output_expected_xfail = False
    for match in matches["output"]:
        selector_type = match.group(2)
        selector = match.group(3)
        if selector_type == "target" and not selector_matches(selector):
            continue
        if selector_type == "xfail" and selector_matches(selector):
            output_expected_xfail = True
        output_parts.append(tcl_double_quoted(match.group(1)))

    output_pattern = None
    if output_parts:
        output_pattern = "".join(output_parts).replace("\n", r"\r?\n")
        re.compile(output_pattern)
    selector_count = (
        sum(match.group(2) is not None for match in matches["do"])
        + sum(match.group(3) is not None for match in matches["options"])
        + sum(match.group(2) is not None for match in matches["output"])
    )
    return ParsedSource(
        action=action,
        extra_flags=tuple(options),
        output_pattern=output_pattern,
        expected_xfail=expected_xfail or output_expected_xfail,
        directive_counts=dict(directive_counts),
        selector_count=selector_count,
    )


def discover_bhaible_ranges(bhaible: Path) -> list[tuple[Path, range]]:
    definition = bhaible / "bhaible.exp"
    text = definition.read_text(encoding="utf-8")
    matches = list(BHAIBLE_LOOP_RE.finditer(text))
    source_occurrences = len(re.findall(r"(?m)^\s*set\s+tlist\b", text))
    loop_occurrences = len(re.findall(r"(?m)^\s*for\s+\{set\s+i\b", text))
    if not matches or len(matches) != source_occurrences or len(matches) != loop_occurrences:
        raise ValueError(
            f"{definition}: parsed {len(matches)} source/loop registrations, "
            f"found {source_occurrences} sources and {loop_occurrences} loops"
        )

    ranges: list[tuple[Path, range]] = []
    filenames: set[str] = set()
    for match in matches:
        filename = match.group(1)
        start = int(match.group(2))
        stop = int(match.group(3))
        if filename in filenames or start < 1 or stop <= start:
            raise ValueError(f"{definition}: invalid DGTEST registration for {filename}")
        source = bhaible / filename
        marker_values = {
            int(value)
            for value in re.findall(
                r"\bDGTEST\s*==\s*(\d+)", source.read_text(encoding="utf-8")
            )
        }
        expected_values = set(range(start, stop))
        if marker_values != expected_values:
            raise ValueError(
                f"{source}: DGTEST source markers do not match bhaible.exp "
                f"range {start}..{stop - 1}"
            )
        filenames.add(filename)
        ranges.append((source, range(start, stop)))
    return ranges


def discover_configs(source_root: Path) -> tuple[list[TestConfig], dict[str, object]]:
    testsuite = source_root / "testsuite"
    if not testsuite.is_dir():
        raise FileNotFoundError(f"missing testsuite: {testsuite}")

    configs: list[TestConfig] = []
    parsed_sources: dict[Path, ParsedSource] = {}

    def parsed(source: Path) -> ParsedSource:
        if source not in parsed_sources:
            parsed_sources[source] = parse_source(source)
        return parsed_sources[source]

    bhaible = testsuite / "libffi.bhaible"
    warning_flags = (
        "-Wno-unused-variable",
        "-Wno-unused-parameter",
        "-Wno-uninitialized",
    )
    bhaible_ranges = discover_bhaible_ranges(bhaible)
    for source, dgtests in bhaible_ranges:
        directives = parsed(source)
        if (
            directives.action != "run"
            or directives.output_pattern is not None
            or directives.expected_xfail
        ):
            raise ValueError(f"unexpected bhaible directives in {source}")
        for dgtest in dgtests:
            configs.append(
                TestConfig(
                    category="libffi.bhaible",
                    source=source,
                    variant=f"DGTEST={dgtest}",
                    action="run",
                    extra_flags=(
                        f"-DDGTEST={dgtest}",
                        *warning_flags,
                        *directives.extra_flags,
                    ),
                    output_pattern=None,
                )
            )

    group_patterns = {
        "libffi.call": ("*.c", "*.cc"),
        "libffi.closures": ("*.c", "*.cc"),
        "libffi.complex": ("*.c", "*.cc"),
        "libffi.go": ("*.c", "*.cc"),
        "libffi.threads": ("*.c",),
    }
    for category, patterns in group_patterns.items():
        group_dir = testsuite / category
        sources = sorted({path for pattern in patterns for path in group_dir.glob(pattern)})
        for source in sources:
            directives = parsed(source)
            if directives.expected_xfail:
                raise ValueError(f"unexpected active xfail for {TARGET_TRIPLET}: {source}")
            configs.append(
                TestConfig(
                    category=category,
                    source=source,
                    variant="",
                    action=directives.action,
                    extra_flags=directives.extra_flags,
                    output_pattern=directives.output_pattern,
                )
            )

    counts = Counter(config.category for config in configs)
    if dict(counts) != EXPECTED_CONFIG_COUNTS:
        raise ValueError(f"configuration count mismatch: {dict(counts)}")
    if len(configs) != 363:
        raise ValueError(f"expected 363 configurations, found {len(configs)}")
    actions = Counter(config.action for config in configs)
    if actions != {"run": 362, "compile": 1}:
        raise ValueError(f"unexpected action counts: {dict(actions)}")
    directive_totals: Counter[str] = Counter()
    for item in parsed_sources.values():
        directive_totals.update(item.directive_counts)
    details: dict[str, object] = {
        "registered_source_count": len(parsed_sources),
        "directive_occurrences": dict(sorted(directive_totals.items())),
        "selector_occurrence_count": sum(
            item.selector_count for item in parsed_sources.values()
        ),
        "bhaible_ranges": [
            {
                "source": source.relative_to(testsuite).as_posix(),
                "first": values.start,
                "last": values.stop - 1,
                "count": len(values),
            }
            for source, values in bhaible_ranges
        ],
    }
    return configs, details


def expand_runs(configs: list[TestConfig]) -> list[TestRun]:
    runs: list[TestRun] = []
    ordinal = 1
    for config in configs:
        for optimization in ("-O0", "-O2"):
            runs.append(TestRun(ordinal, config, optimization))
            ordinal += 1
    if len(runs) != 726:
        raise ValueError(f"expected 726 runs, found {len(runs)}")
    return runs


def run_command(
    command: list[str], cwd: Path, env: dict[str, str], timeout: int
) -> tuple[int | None, bytes, float, str | None]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return completed.returncode, completed.stdout, time.monotonic() - started, None
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        if exc.stderr:
            output += exc.stderr
        return None, output, time.monotonic() - started, f"timeout after {timeout}s"


def write_bytes(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    return sha256_file(path)


def prune_compile_output(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").replace("\r", "")
    patterns = (
        r"(^|\n)[^\n]*linker input file unused since linking not done",
        r"(^|\n)[^\n]*file path prefix [^\n]* never used",
        r"(^|\n)(?:ld\.so: warning:[^\n]*\n?)+",
        r"(^|\n)[^\n]*unable to perform all requested operations",
        r"(^|\n)[^\n]*warning: .* has a LOAD segment with RWX permissions",
        r"(^|\n)(?:cache|shared):INFO:[^\n]*",
    )
    for pattern in patterns:
        text = re.sub(pattern, lambda match: "\n" if match.group(1) == "\n" else "", text)
    text = re.sub(r"\n+", "\n", text)
    return re.sub(r"^\n+", "", text)


def build_compile_command(
    test: TestRun,
    source_root: Path,
    build_root: Path,
    library: Path,
    artifact: Path,
    compiler: str,
    native_host: bool = False,
) -> list[str]:
    host_diagnostic_options = (
        ["-Wno-unused-but-set-variable", "-Wno-psabi"] if native_host else []
    )
    command = [
        compiler,
        *host_diagnostic_options,
        "-W",
        "-Wall",
        *test.config.extra_flags,
        test.optimization,
        f"-I{build_root / 'include'}",
        f"-I{source_root / 'include'}",
        f"-I{build_root}",
    ]
    if test.config.action == "compile":
        command.extend(["-S", str(test.config.source), "-o", str(artifact)])
    elif test.config.action == "run":
        command.extend(
            [
                str(test.config.source),
                str(library),
                "-lpthread",
                "-o",
                str(artifact),
            ]
        )
    else:
        raise ValueError(f"unsupported action {test.config.action}: {test.name}")
    return command


def run_one(
    test: TestRun,
    source_root: Path,
    build_root: Path,
    output_root: Path,
    tools: dict[str, str],
    library: Path,
    native_host: bool,
) -> dict[str, object]:
    case_dir = output_root / "cases" / test.slug
    case_dir.mkdir(parents=True)
    tmp_dir = case_dir / "tmp"
    tmp_dir.mkdir()
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_dir)
    env["TMPPREFIX"] = str(tmp_dir / "shell")

    compiler = tools["clang++"] if test.config.source.suffix == ".cc" else tools["clang"]
    artifact = case_dir / ("test.exe" if test.config.action == "run" else "test.s")
    command = build_compile_command(
        test,
        source_root,
        build_root,
        library,
        artifact,
        compiler,
        native_host,
    )

    compile_rc, compile_output, compile_seconds, compile_error = run_command(
        command, case_dir, env, 180
    )
    compile_hash = write_bytes(case_dir / "compile.log", compile_output)
    pruned_compile_output = prune_compile_output(compile_output)
    pruned_compile_hash = write_bytes(
        case_dir / "compile-pruned.log", pruned_compile_output.encode("utf-8")
    )
    output_checked = (
        test.config.action == "run" and test.config.output_pattern is not None
    )
    result: dict[str, object] = {
        "ordinal": test.ordinal,
        "name": test.name,
        "category": test.config.category,
        "source": str(test.config.source.relative_to(source_root)),
        "variant": test.config.variant,
        "optimization": test.optimization,
        "action": test.config.action,
        "compile_command": shlex.join(command),
        "compile_returncode": compile_rc,
        "compile_seconds": round(compile_seconds, 6),
        "compile_log_sha256": compile_hash,
        "compile_pruned_log_sha256": pruned_compile_hash,
        "compile_excess_output": pruned_compile_output != "",
        "compile_error": compile_error,
        "output_pattern": test.config.output_pattern if output_checked else None,
        "output_checked": output_checked,
        "status": "ERROR",
    }
    if compile_rc != 0 or not artifact.is_file() or pruned_compile_output != "":
        result["status"] = "TIMEOUT" if compile_error else "FAIL"
        (case_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result

    result["artifact_sha256"] = sha256_file(artifact)
    if test.config.action == "compile":
        result["status"] = "PASS"
        (case_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result

    if native_host:
        result["signing_mode"] = "not_required_native_host"
        result["signed_artifact_sha256"] = result["artifact_sha256"]
        artifact.chmod(0o755)
    else:
        clean = case_dir / "test.codesign-clean"
        signed = case_dir / "test.signed"
        sign_commands = [
            [tools["llvm-objcopy"], "--remove-section", ".codesign", str(artifact), str(clean)],
            [
                tools["binary-sign-tool"],
                "sign",
                "-inFile",
                str(clean),
                "-outFile",
                str(signed),
                "-selfSign",
                "1",
            ],
        ]
        sign_log = bytearray()
        sign_seconds = 0.0
        sign_rc: int | None = 0
        sign_error: str | None = None
        for sign_command in sign_commands:
            sign_log.extend(("$ " + shlex.join(sign_command) + "\n").encode("utf-8"))
            sign_rc, command_output, seconds, sign_error = run_command(
                sign_command, case_dir, env, 60
            )
            sign_seconds += seconds
            sign_log.extend(command_output)
            if sign_rc != 0:
                break
        result["sign_commands"] = [shlex.join(item) for item in sign_commands]
        result["sign_returncode"] = sign_rc
        result["sign_seconds"] = round(sign_seconds, 6)
        result["sign_error"] = sign_error
        result["sign_log_sha256"] = write_bytes(case_dir / "sign.log", bytes(sign_log))
        if sign_rc != 0 or not signed.is_file():
            result["status"] = "TIMEOUT" if sign_error else "FAIL"
            (case_dir / "result.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            return result

        os.replace(signed, artifact)
        clean.unlink(missing_ok=True)
        artifact.chmod(0o755)
        result["signed_artifact_sha256"] = sha256_file(artifact)

    run_rc, run_output, run_seconds, run_error = run_command(
        [str(artifact)], case_dir, env, 120
    )
    result["run_command"] = str(artifact)
    result["run_returncode"] = run_rc
    result["run_seconds"] = round(run_seconds, 6)
    result["run_error"] = run_error
    result["run_log_sha256"] = write_bytes(case_dir / "run.log", run_output)
    output_text = run_output.decode("utf-8", errors="replace")
    pattern_match = True
    if test.config.output_pattern is not None:
        pattern_match = re.search(test.config.output_pattern, output_text) is not None
    result["output_pattern_match"] = pattern_match
    if run_rc == 0 and pattern_match:
        result["status"] = "PASS"
    elif run_error:
        result["status"] = "TIMEOUT"
    else:
        result["status"] = "FAIL"
    (case_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def find_tools(args: argparse.Namespace) -> dict[str, str]:
    expected = {
        "clang": args.clang,
        "clang++": args.clangxx,
        "llvm-objcopy": args.objcopy,
        "binary-sign-tool": args.signer,
    }
    required = {"clang", "clang++"} if args.native_host else set(expected)
    for name, value in expected.items():
        if name not in required:
            continue
        if value is None:
            raise ValueError(f"full execution requires --{name}")
        if not os.access(value, os.X_OK):
            raise FileNotFoundError(f"missing executable {name}: {value}")
    return {name: str(value) for name, value in expected.items() if value is not None}


def execute(
    args: argparse.Namespace,
    archive: Path,
    source_root: Path,
    source_manifest: SourceManifest,
) -> int:
    configs, discovery_details = discover_configs(source_root)
    runs = expand_runs(configs)
    discovery = {
        "execution_environment": "native_host" if args.native_host else "ohos_target",
        "target_triplet": None if args.native_host else TARGET_TRIPLET,
        "host_machine": platform.machine() if args.native_host else None,
        "source_origin": "verified official archive extraction",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_manifest_file_count": source_manifest.file_count,
        "source_manifest_byte_count": source_manifest.byte_count,
        "source_manifest_sha256": source_manifest.sha256,
        "configuration_count": len(configs),
        "configuration_counts": dict(Counter(item.category for item in configs)),
        "configuration_actions": dict(Counter(item.action for item in configs)),
        "execution_count": len(runs),
        "execution_actions": dict(Counter(item.config.action for item in runs)),
        "optimizations": ["-O0", "-O2"],
        "output_checked_configurations": sum(
            item.action == "run" and item.output_pattern is not None for item in configs
        ),
        "output_checked_executions": sum(
            item.config.action == "run" and item.config.output_pattern is not None
            for item in runs
        ),
        **discovery_details,
    }
    if discovery["output_checked_configurations"] != 104:
        raise ValueError(
            "expected 104 run configurations with output patterns, found "
            f"{discovery['output_checked_configurations']}"
        )
    if args.discovery_only:
        print(json.dumps(discovery, indent=2, sort_keys=True))
        return 0

    if args.jobs < 1 or args.jobs > 32:
        raise ValueError("--jobs must be in the range 1..32")
    build_root = (args.build or args.root / "build").resolve()
    output_root = (args.output or args.root / "official-tests").resolve()
    library = build_root / ".libs" / "libffi.a"
    if args.expected_libffi_sha256 is None:
        raise ValueError("full execution requires --expected-libffi-sha256")
    expected_library_sha256 = args.expected_libffi_sha256.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_library_sha256):
        raise ValueError("--expected-libffi-sha256 must be 64 lowercase hex digits")
    if sha256_file(library) != expected_library_sha256:
        raise ValueError("libffi.a SHA256 mismatch")
    feature_header = (build_root / "include" / "ffitarget.h").read_text(
        encoding="utf-8"
    )
    required_features = (
        "#define FFI_CLOSURES 1",
        "#define FFI_GO_CLOSURES 1",
        "#define FFI_TARGET_HAS_COMPLEX_TYPE",
    )
    for feature in required_features:
        if feature not in feature_header:
            raise ValueError(f"required upstream test feature is disabled: {feature}")
    tools = find_tools(args)
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_root}")
    output_root.mkdir(parents=True)
    (output_root / "cases").mkdir()
    source_manifest_path = output_root / "source-manifest.jsonl"
    source_manifest_path.write_bytes("".join(source_manifest.lines).encode("utf-8"))
    if sha256_file(source_manifest_path) != source_manifest.sha256:
        raise AssertionError("written source manifest SHA256 mismatch")
    (output_root / "discovery.json").write_text(
        json.dumps(discovery, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    environment = {
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version,
        "jobs": args.jobs,
        "root": str(args.root.resolve()),
        "source": str(source_root),
        "build": str(build_root),
        "output": str(output_root),
        "source_archive": str(archive),
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_manifest_sha256": source_manifest.sha256,
        "libffi_a_sha256": sha256_file(library),
        "expected_libffi_a_sha256": expected_library_sha256,
        "tools": tools,
    }
    (output_root / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "RUNNING").write_text(
        f"pid={os.getpid()}\nstarted_at={environment['started_at']}\n", encoding="ascii"
    )

    results: list[dict[str, object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_map = {
            executor.submit(
                run_one,
                item,
                source_root,
                build_root,
                output_root,
                tools,
                library,
                args.native_host,
            ): item
            for item in runs
        }
        completed_count = 0
        for future in concurrent.futures.as_completed(future_map):
            item = future_map[future]
            try:
                result = future.result()
            except Exception as exc:  # Preserve a terminal record for every run.
                result = {
                    "ordinal": item.ordinal,
                    "name": item.name,
                    "category": item.config.category,
                    "source": str(item.config.source.relative_to(source_root)),
                    "variant": item.config.variant,
                    "optimization": item.optimization,
                    "action": item.config.action,
                    "status": "ERROR",
                    "exception": repr(exc),
                }
                case_dir = output_root / "cases" / item.slug
                case_dir.mkdir(parents=True, exist_ok=True)
                (case_dir / "result.json").write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            results.append(result)
            completed_count += 1
            if result["status"] != "PASS" or completed_count % 25 == 0:
                print(
                    f"[{completed_count:03d}/726] {result['status']} {result['name']}",
                    flush=True,
                )

    results.sort(key=lambda item: int(item["ordinal"]))
    manifest_path = output_root / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in results),
        encoding="utf-8",
    )
    status_counts = Counter(str(item["status"]) for item in results)
    logical_configs: dict[str, list[str]] = {}
    for item in results:
        variant = f"[{item['variant']}]" if item.get("variant") else ""
        key = f"{item['category']}/{Path(str(item['source'])).name}{variant}"
        logical_configs.setdefault(key, []).append(str(item["status"]))
    logical_status = {
        key: "PASS" if len(statuses) == 2 and statuses == ["PASS", "PASS"] else "FAIL"
        for key, statuses in logical_configs.items()
    }
    configuration_status_counts = Counter(logical_status.values())
    category_status = {
        category: dict(
            Counter(
                str(item["status"])
                for item in results
                if item["category"] == category
            )
        )
        for category in EXPECTED_CONFIG_COUNTS
    }
    summary = {
        **discovery,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status_counts": dict(status_counts),
        "configuration_status_counts": dict(configuration_status_counts),
        "category_status": category_status,
        "manifest_sha256": sha256_file(manifest_path),
        "all_passed": (
            status_counts == {"PASS": 726}
            and configuration_status_counts == {"PASS": 363}
        ),
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    passed = bool(summary["all_passed"])
    (output_root / "RUNNING").unlink(missing_ok=True)
    (output_root / "terminal-status.txt").write_text(
        f"status={'PASS' if passed else 'FAIL'}\n"
        "phase=complete\n"
        f"rc={0 if passed else 1}\n"
        f"upstream={'PASS' if passed else 'FAIL'}\n"
        f"summary_sha256={sha256_file(summary_path)}\n",
        encoding="ascii",
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/storage/Users/currentUser/tmp/libffi-3.5.2"),
    )
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--expected-libffi-sha256")
    parser.add_argument("--clang")
    parser.add_argument("--clangxx")
    parser.add_argument("--objcopy")
    parser.add_argument("--signer")
    parser.add_argument("--native-host", action="store_true")
    parser.add_argument("--discovery-only", action="store_true")
    args = parser.parse_args()

    args.root = args.root.resolve()
    archive = (args.archive or args.root / "libffi-3.5.2.tar.gz").resolve()
    with verified_archive_source(archive, args.root) as (source_root, source_manifest):
        return execute(args, archive, source_root, source_manifest)


if __name__ == "__main__":
    raise SystemExit(main())
