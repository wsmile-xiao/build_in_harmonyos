#!/usr/bin/env python3
"""Exercise the packaged xmlcatmgr against disposable catalogs only."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deny_file_growth():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))


class Runner:
    def __init__(self, binary):
        self.binary = str(binary)
        self.commands = []
        self.cases = []

    def command(self, mode, catalog, *action):
        require(catalog.is_absolute(), "catalog path must be absolute")
        return ([self.binary] + (["-s"] if mode == "sgml" else []) +
                ["-c", str(catalog)] + list(action))

    def call(self, mode, catalog, *action, limit_file=False):
        command = self.command(mode, catalog, *action)
        started = time.monotonic()
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=8,
                preexec_fn=deny_file_growth if limit_file else None,
                check=False,
            )
            self.commands.append({
                "argv": command, "rc": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "elapsed_s": round(time.monotonic() - started, 3),
                "file_limit_zero": limit_file,
            })
            return result
        except subprocess.TimeoutExpired as error:
            self.commands.append({
                "argv": command, "rc": "timeout", "stdout": str(error.stdout),
                "stderr": str(error.stderr),
                "elapsed_s": round(time.monotonic() - started, 3),
                "file_limit_zero": limit_file,
            })
            raise

    def ok(self, mode, catalog, *action):
        result = self.call(mode, catalog, *action)
        require(result.returncode == 0,
                f"expected success: {action}, rc={result.returncode}, stderr={result.stderr}")
        return result

    def bad(self, mode, catalog, *action, limit_file=False):
        result = self.call(mode, catalog, *action, limit_file=limit_file)
        require(result.returncode == 1,
                f"expected exit 1: {action}, rc={result.returncode}, stderr={result.stderr}")
        return result

    def scenario(self, name, operation):
        try:
            operation()
        except Exception as error:
            self.cases.append({"name": name, "status": "fail",
                               "error": f"{type(error).__name__}: {error}"})
        else:
            self.cases.append({"name": name, "status": "pass"})

    def smoke_options(self):
        for options in (("--version",), ("--help",),
                        ("-s", "--version"), ("--help", "-s")):
            command = [self.binary, *options]
            started = time.monotonic()
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=8, check=False)
            self.commands.append({
                "argv": command, "rc": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "elapsed_s": round(time.monotonic() - started, 3),
            })
            require(result.returncode == 0 and
                    "XML Catalog Manager 2.2" in result.stdout + result.stderr,
                    f"{options} did not identify xmlcatmgr 2.2")

    def lifecycle(self, mode):
        with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
            catalog = Path(directory) / f"{mode} catalog with spaces.cat"
            self.ok(mode, catalog, "create")
            require(catalog.is_file(), "create did not create catalog")
            body = catalog.read_text(encoding="utf-8")
            require(("<?xml" in body and "<catalog" in body) if mode == "xml"
                    else "Created by XML Catalog Manager" in body,
                    "create produced unexpected catalog content")
            self.bad(mode, catalog, "create")

            kind = "public" if mode == "xml" else "PUBLIC"
            identifier = "public id with spaces"
            replacement = "file with spaces.dtd"
            self.ok(mode, catalog, "add", kind, identifier, replacement)
            lookup = self.ok(mode, catalog, "lookup", identifier)
            if mode == "xml":
                require('publicId="public id with spaces"' in lookup.stdout and
                        'uri="file with spaces.dtd"' in lookup.stdout,
                        "XML lookup did not return both attributes")
            else:
                require('PUBLIC "public id with spaces" "file with spaces.dtd"'
                        in lookup.stdout, "SGML lookup returned unexpected entry")
            before = file_hash(catalog)
            self.bad(mode, catalog, "add", kind, identifier, replacement)
            require(file_hash(catalog) == before, "duplicate add changed catalog")

            next_kind = "nextCatalog" if mode == "xml" else "CATALOG"
            next_name = "next catalog with spaces.xml"
            self.ok(mode, catalog, "add", next_kind, next_name)
            self.ok(mode, catalog, "lookup", next_name)
            self.ok(mode, catalog, "remove", kind, identifier)
            self.bad(mode, catalog, "lookup", identifier)
            self.ok(mode, catalog, "remove", next_kind, next_name)
            self.bad(mode, catalog, "remove", kind, identifier)
            self.ok(mode, catalog, "destroy")
            require(not catalog.exists(), "destroy left catalog behind")

    def invalid_arguments(self, mode):
        with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
            catalog = Path(directory) / "invalid arguments catalog.cat"
            self.ok(mode, catalog, "create")
            bad_actions = [
                ("add",), ("remove",), ("lookup",), ("unknown-action",),
            ]
            if mode == "xml":
                bad_actions += [
                    ("add", "group", "group id", "--"),
                    ("add", "nextCatalog", "next.xml", "extra"),
                    ("add", "public", "missing replacement"),
                ]
            else:
                bad_actions += [
                    ("add", "UNKNOWN", "id", "file.dtd"),
                    ("add", "PUBLIC", "missing replacement"),
                ]
            for action in bad_actions:
                before = file_hash(catalog)
                self.bad(mode, catalog, *action)
                require(file_hash(catalog) == before,
                        f"invalid action changed catalog: {action}")
            self.ok(mode, catalog, "destroy")

    def missing_paths(self, mode):
        with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
            root = Path(directory)
            absent = root / "missing catalog.cat"
            self.bad(mode, absent, "lookup", "id")
            self.bad(mode, absent, "add", "public" if mode == "xml" else "PUBLIC",
                     "id", "file.dtd")
            self.bad(mode, root / "missing parent" / "catalog.cat", "create")
            require(not absent.exists(), "failed read or add created catalog")

    def write_failures(self, mode):
        with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
            root = Path(directory)
            fresh = root / "new catalog.cat"
            self.bad(mode, fresh, "create", limit_file=True)
            require(not fresh.exists(), "failed create left partial catalog")
            catalog = root / "existing catalog.cat"
            self.ok(mode, catalog, "create")
            self.bad(mode, catalog, "add",
                     "public" if mode == "xml" else "PUBLIC",
                     "write failure id", "file.dtd", limit_file=True)

    def lock_wait(self, mode):
        with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
            catalog = Path(directory) / "locked catalog.cat"
            self.ok(mode, catalog, "create")
            command = self.command(mode, catalog, "add",
                                   "public" if mode == "xml" else "PUBLIC",
                                   "locked id", "locked file.dtd")
            fd = os.open(catalog, os.O_RDWR)
            process = None
            locked = False
            started = time.monotonic()
            try:
                fcntl.lockf(fd, fcntl.LOCK_EX)
                locked = True
                process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True)
                time.sleep(0.4)
                blocked = process.poll() is None
                fcntl.lockf(fd, fcntl.LOCK_UN)
                locked = False
                stdout, stderr = process.communicate(timeout=8)
                self.commands.append({
                    "argv": command, "rc": process.returncode,
                    "stdout": stdout, "stderr": stderr,
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "parent_lock_held_s": 0.4, "blocked_while_locked": blocked,
                })
                require(blocked, "add completed while another process held the lock")
                require(process.returncode == 0,
                        f"add failed after lock release: rc={process.returncode}, {stderr}")
                self.ok(mode, catalog, "lookup", "locked id")
            finally:
                if locked:
                    fcntl.lockf(fd, fcntl.LOCK_UN)
                os.close(fd)
                if process is not None and process.poll() is None:
                    process.kill()
                    process.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    runner = Runner(args.binary.resolve())
    runner.scenario("smoke_options", runner.smoke_options)
    for mode in ("xml", "sgml"):
        runner.scenario(f"{mode}_lifecycle", lambda mode=mode: runner.lifecycle(mode))
        runner.scenario(f"{mode}_invalid_arguments",
                        lambda mode=mode: runner.invalid_arguments(mode))
        runner.scenario(f"{mode}_missing_paths", lambda mode=mode: runner.missing_paths(mode))
        runner.scenario(f"{mode}_write_failures",
                        lambda mode=mode: runner.write_failures(mode))
        runner.scenario(f"{mode}_lock_wait", lambda mode=mode: runner.lock_wait(mode))
    passed = sum(case["status"] == "pass" for case in runner.cases)
    summary = {"total": len(runner.cases), "passed": passed,
               "failed": len(runner.cases) - passed,
               "cases": runner.cases, "commands": runner.commands}
    (args.report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"xmlcatmgr: {passed}/{len(runner.cases)} scenarios passed; "
          f"{len(runner.commands)} commands recorded")
    for case in runner.cases:
        print(f"{case['status']}: {case['name']}" +
              (f": {case['error']}" if "error" in case else ""))
    return 0 if passed == len(runner.cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
