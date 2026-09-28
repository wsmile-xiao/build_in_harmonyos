#!/usr/bin/env python3
"""Prepare private, signed OHOS libraries for the VTK CTest and consumer runs."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import http.client
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

from conan.errors import ConanException


EXTERNAL_DATA_DOWNLOAD_ATTEMPTS = 3
EXTERNAL_DATA_DOWNLOAD_TIMEOUT = 300


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_runtime(conanfile):
    """Record a new directory; repeated builds never inherit old runtime files."""
    configured = conanfile.conf.get("user.vtk:runtime_root", default="")
    if configured:
        root = Path(configured)
    else:
        # HiShell's shared Documents volume removes executable mode bits on
        # copied libraries. Its application-private files directory permits
        # signed executable mappings. Other OHOS runners use their temp area.
        app_files = Path("/data/storage/el2/base/haps/entry/files")
        root = (app_files if app_files.is_dir() else Path(tempfile.gettempdir())) / "vtk-runtime"
    root.mkdir(parents=True, exist_ok=True)
    prefix = Path(tempfile.mkdtemp(prefix="vtk-9.3.0-", dir=str(root)))
    directory = prefix / "lib"
    directory.mkdir()
    record = Path(conanfile.build_folder) / "vtk-runtime-path.txt"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(str(directory), encoding="utf-8")
    conanfile.output.info("Private VTK test runtime: %s" % directory)
    return directory


def runtime_directory(conanfile):
    record = Path(conanfile.build_folder) / "vtk-runtime-path.txt"
    return Path(record.read_text(encoding="utf-8"))


def stage_runtime(conanfile, source_directory):
    """Copy and sign libraries without altering the source/package manifest."""
    source = Path(source_directory).resolve()
    directory = runtime_directory(conanfile).resolve()
    if source == directory or source in directory.parents:
        raise ConanException("Private runtime overlaps the source library directory")
    if directory.name != source.name:
        raise ConanException("Private runtime must preserve the library directory name")
    source_share = source.parent / "share"
    if source_share == directory.parent or source_share in directory.parent.parents:
        raise ConanException("Private runtime overlaps the source resource directory")
    signer = shutil.which("binary-sign-tool")
    objcopy = shutil.which("llvm-objcopy")
    if not signer or not objcopy:
        raise ConanException("OHOS runtime tests require binary-sign-tool and llvm-objcopy on PATH")
    libraries = sorted(source.glob("libvtk*.so*"))
    if not libraries:
        raise ConanException("No VTK shared libraries in %s" % source)
    records = []
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=str(directory)) as staging_name:
        staging = Path(staging_name)
        for library in libraries:
            if not library.resolve().is_file():
                raise ConanException("Invalid VTK library: %s" % library)
            with library.open("rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanException("VTK runtime input is not ELF: %s" % library)
            target = staging / library.name
            source_hash = _sha256(library)
            shutil.copyfile(library, target)
            if _sha256(target) != source_hash:
                raise ConanException("VTK runtime copy differs: %s" % library.name)
            records.append({"name": library.name, "source_sha256": source_hash})

        def sign(record):
            target = staging / record["name"]
            signed = target.with_name(target.name + ".signed")
            commands = ([objcopy, "--remove-section", ".codesign", str(target)],
                        [signer, "sign", "-inFile", str(target), "-outFile", str(signed),
                         "-selfSign", "1"])
            record["commands"] = []
            for command in commands:
                completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
                record["commands"].append({"argv": command, "exit_code": completed.returncode,
                                           "stdout": completed.stdout, "stderr": completed.stderr})
                if completed.returncode:
                    raise ConanException("Runtime command failed (%s): %s\nstdout: %s\nstderr: %s" %
                                         (completed.returncode, shlex.join(command),
                                          completed.stdout, completed.stderr))
            os.replace(signed, target)
            target.chmod(0o755)
            record["runtime_sha256"] = _sha256(target)
            if _sha256(source / record["name"]) != record["source_sha256"]:
                raise ConanException("Source library changed while staging: %s" % record["name"])

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(sign, records))
        # Publish each complete signed file with a rename. Executable mappings
        # can reject overwriting their inode while permitting replacement.
        for record in records:
            os.replace(staging / record["name"], directory / record["name"])
    # Resource lookup is relative to the loaded library, including PROJ's
    # ../share/vtk-9.3/proj/proj.db. Preserve the installed/build-tree layout.
    resources = []
    if source_share.is_dir():
        for resource in sorted(source_share.rglob("*")):
            if not resource.is_file():
                continue
            relative = resource.relative_to(source.parent)
            target = directory.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            before = _sha256(resource)
            with tempfile.NamedTemporaryFile(dir=str(target.parent), delete=False) as stream:
                temporary = Path(stream.name)
            try:
                shutil.copyfile(resource, temporary)
                if _sha256(temporary) != before or _sha256(resource) != before:
                    raise ConanException("Runtime resource copy differs: %s" % relative)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
            resources.append({"path": relative.as_posix(), "sha256": before})
    test_output = source.parent / "Testing" / "Temporary"
    mirrored_test_output = None
    if test_output.is_dir():
        # The upstream locator test searches this standard build-tree landmark
        # from the loaded library. Create a fresh writable output directory;
        # previous test outputs are not copied into the new runtime.
        mirrored_test_output = directory.parent / "Testing" / "Temporary"
        mirrored_test_output.mkdir(parents=True, exist_ok=True)
    report = {"source": str(source), "runtime": str(directory), "files": records,
              "resources": resources,
              "test_output_directory": str(mirrored_test_output) if mirrored_test_output else None}
    (Path(conanfile.build_folder) / "vtk-runtime-manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    conanfile.output.info("[PASS] copied and signed %d private VTK libraries" % len(records))


def ctest_command(build_folder):
    """Use the CTest paired with the configuring CMake, including HNP installs."""
    for line in (Path(build_folder) / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("CMAKE_CTEST_COMMAND:INTERNAL="):
            return line.split("=", 1)[1]
    command = shutil.which("ctest")
    if not command:
        raise ConanException("The configuring CMake installation did not provide CTest")
    return command


def stage_external_data(conanfile):
    """Fill VTK's official object store using the generated data target plan.

    The OHOS CMake 4.1 build rejects file(RENAME ... NO_REPLACE), including
    on its private filesystem. Python os.replace works there. Data contents
    and test registration are unchanged; CMake still materializes the inputs.
    """
    build = Path(conanfile.build_folder)
    source = Path(conanfile.source_folder).resolve()
    cache = {}
    for line in (build / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("//", "#")) and "=" in line and ":" in line:
            key, value = line.split("=", 1)
            cache[key.split(":", 1)[0]] = value
    store = Path(cache["VTK_DATA_STORE"])
    generator = cache["CMAKE_GENERATOR"]
    if "Ninja" in generator:
        # List every rule even after VTKData is up to date. A dry run alone
        # would omit cached objects and shrink the audit manifest on reuse.
        command = [cache["CMAKE_MAKE_PROGRAM"], "-C", str(build),
                   "-t", "commands", "VTKData"]
    elif "Makefiles" in generator:
        command = [cache["CMAKE_COMMAND"], "--build", str(build),
                   "--target", "VTKData", "--", "-B", "-n"]
    else:
        raise ConanException("OHOS ExternalData preparation requires Ninja or Makefiles")
    conanfile.output.info("[STEP] list required upstream data: %s" % shlex.join(command))
    plan = subprocess.run(command, capture_output=True, text=True)
    (build / "upstream-data-plan.txt").write_text(plan.stdout, encoding="utf-8")
    if plan.returncode:
        raise ConanException("VTKData dry run failed (%s): %s\n%s" %
                             (plan.returncode, plan.stdout, plan.stderr))
    objects = {}
    for line in plan.stdout.splitlines():
        if "-DExternalData_ACTION=fetch" not in line:
            continue
        values = {}
        for token in shlex.split(line):
            if token.startswith("-D") and "=" in token:
                key, value = token[2:].split("=", 1)
                values[key] = value
        name = Path(values["name"])
        for extension in values["exts"].split("+"):
            link = Path(str(name) + extension).resolve()
            if not link.is_relative_to(source):
                raise ConanException("ExternalData content link is outside the source tree: %s" % link)
            algorithm = extension.lstrip(".").lower()
            if algorithm not in ("md5", "sha1", "sha256", "sha512"):
                raise ConanException("Unsupported ExternalData hash: %s" % extension)
            expected = link.read_text(encoding="ascii").strip().lower()
            length = hashlib.new(algorithm).digest_size * 2
            if len(expected) != length or any(c not in "0123456789abcdef" for c in expected):
                raise ConanException("Invalid ExternalData content hash: %s" % link)
            key = (algorithm, expected)
            objects.setdefault(key, []).append(link.relative_to(source).as_posix())

    def fetch(item):
        (algorithm, expected), links = item
        target = store / algorithm.upper() / expected
        target.parent.mkdir(parents=True, exist_ok=True)
        record = {"algorithm": algorithm, "hash": expected, "links": links}

        def digest_file(path):
            digest = hashlib.new(algorithm)
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()

        if target.is_file() and digest_file(target) == expected:
            record.update(status="verified-cache", size=target.stat().st_size)
            return record
        urls = ["https://data.kitware.com/api/v1/file/hashsum/%s/%s/download" %
                (algorithm.upper(), expected),
                "https://vtk.org/files/ExternalData/%s/%s" % (algorithm.upper(), expected)]
        errors = []
        for url in urls:
            for attempt in range(1, EXTERNAL_DATA_DOWNLOAD_ATTEMPTS + 1):
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(prefix="vtk-data-", dir=str(target.parent),
                                                     delete=False) as output:
                        temporary = Path(output.name)
                        with urllib.request.urlopen(
                                url, timeout=EXTERNAL_DATA_DOWNLOAD_TIMEOUT) as response:
                            shutil.copyfileobj(response, output, length=1024 * 1024)
                    actual = digest_file(temporary)
                    if actual != expected:
                        raise ValueError("download hash differs: %s" % actual)
                    os.replace(temporary, target)
                    record.update(status="downloaded", url=url, size=target.stat().st_size)
                    if errors:
                        record["attempts"] = errors
                    return record
                except Exception as exc:
                    errors.append({"url": url, "attempt": attempt, "error": str(exc)})
                    if isinstance(exc, urllib.error.HTTPError):
                        retryable = exc.code in (408, 429) or 500 <= exc.code < 600
                    else:
                        retryable = isinstance(exc, (urllib.error.URLError, TimeoutError,
                                                    ConnectionError, http.client.IncompleteRead))
                    if not retryable or attempt == EXTERNAL_DATA_DOWNLOAD_ATTEMPTS:
                        break
                    time.sleep(2 * attempt)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        record.update(status="failed", attempts=errors)
        return record

    records = []
    conanfile.output.info("[STEP] verify %d required ExternalData objects" % len(objects))
    error = None
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = {executor.submit(fetch, item): item for item in sorted(objects.items())}
            for future in as_completed(pending):
                try:
                    record = future.result()
                except Exception as exc:
                    (algorithm, expected), links = pending[future]
                    record = {"algorithm": algorithm, "hash": expected, "links": links,
                              "status": "failed", "error": str(exc)}
                records.append(record)
                if len(records) % 50 == 0 or len(records) == len(objects):
                    conanfile.output.info("ExternalData progress: %d/%d" % (len(records), len(objects)))
    except BaseException as exc:
        error = str(exc)
        raise
    finally:
        records.sort(key=lambda record: (record["algorithm"], record["hash"]))
        failed = [record for record in records if record["status"] == "failed"]
        report = {"plan_command": command, "object_count": len(objects),
                  "completed": len(records), "incomplete": len(objects) - len(records),
                  "failed": len(failed), "error": error, "objects": records}
        (build / "upstream-data-manifest.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failed:
        for record in failed:
            conanfile.output.error(
                "ExternalData failed: %s:%s (%s) details=%s" %
                (record["algorithm"], record["hash"], ",".join(record["links"]),
                 json.dumps(record.get("attempts", record.get("error")), ensure_ascii=True)))
        raise ConanException("ExternalData verification failed for %d objects; see upstream-data-manifest.json" % len(failed))
    conanfile.output.info("[PASS] %d upstream data objects verified" % len(records))
