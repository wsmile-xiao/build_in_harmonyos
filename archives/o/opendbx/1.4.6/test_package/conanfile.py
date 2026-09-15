#!/usr/bin/env python3
"""Conan consumer test for OpenDBX 1.4.6.

Builds two contract executables against the installed package and runs
them: test_opendbx (C API, libopendbx) and test_opendbxplus (C++ API,
libopendbxplus). Both run without a database server.

Also builds and runs test_upstream_sqlite3: the runnable subset of the
upstream odbxtest suite (sqlite3 file backend, no server) against a temp
file through the installed libopendbx + libsqlite3backend.so, providing
the HMBS_UPSTREAM_TEST_RESULT evidence. The other eight upstream backends
need live database servers and cannot run here (see MANIFEST.yml).
"""

import os
import glob
import json
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


TEST_PROGRAMS = (
    ("test_opendbx", "test_opendbx.c", "c", ["opendbx"]),
    ("test_opendbxplus", "test_opendbxplus.cpp", "cpp", ["opendbxplus", "opendbx"]),
)

# Upstream sqlite3 file-backend regression (offline subset of odbxtest).
# Built and run separately from the contract programs above so the
# HMBS_TEST_PACKAGE_RESULT count (2) and the HMBS_UPSTREAM_TEST_RESULT
# count (1) stay independent.
UPSTREAM_PROGRAM = ("test_upstream_sqlite3", "test_upstream_sqlite3.c", "c", ["opendbx"])


class OpendbxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # 真机 /tmp 只读：编译器临时文件改走可写目录。
        writable = self._writable_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = writable
        dep = self.dependencies["opendbx"]
        package_folder = dep.package_folder
        include_dirs = self._absolute_paths(
            package_folder, dep.cpp_info.includedirs or ["include"]
        )
        lib_dirs = self._absolute_paths(package_folder, dep.cpp_info.libdirs or ["lib"])

        for name, source, lang, libs in TEST_PROGRAMS:
            output = os.path.join(self.build_folder, self._exe_name(name))
            command = [self._compiler(lang), os.path.join(self.source_folder, source)]
            command.append("-std=c++14" if lang == "cpp" else "-std=c11")
            command.extend("-I{}".format(path) for path in include_dirs)
            command.extend("-L{}".format(path) for path in lib_dirs)
            if lib_dirs and self.settings.os in ("Linux", "OHOS"):
                command.append("-Wl,-rpath,{}".format(lib_dirs[0]))
            command.extend("-l{}".format(lib) for lib in libs)
            command.extend("-l{}".format(lib) for lib in (dep.cpp_info.system_libs or []))
            command.extend(["-o", output])
            self.run(shlex.join(command), env="conanbuild")

        # Upstream sqlite3 regression smoke, same link recipe as the C
        # contract program (installed libopendbx; backend is dlopened at
        # runtime, needs no extra link libs here).
        name, source, lang, libs = UPSTREAM_PROGRAM
        output = os.path.join(self.build_folder, self._exe_name(name))
        command = [self._compiler(lang), os.path.join(self.source_folder, source)]
        command.append("-std=c11")
        command.extend("-I{}".format(path) for path in include_dirs)
        command.extend("-L{}".format(path) for path in lib_dirs)
        if lib_dirs and self.settings.os in ("Linux", "OHOS"):
            command.append("-Wl,-rpath,{}".format(lib_dirs[0]))
        command.extend("-l{}".format(lib) for lib in libs)
        command.extend("-l{}".format(lib) for lib in (dep.cpp_info.system_libs or []))
        command.extend(["-o", output])
        self.run(shlex.join(command), env="conanbuild")

    def test(self):
        if not can_run(self):
            raise ConanException("opendbx target consumers are not runnable")
        runtime_dir = None
        passed_count = 0
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="opendbx-test-", dir=self._writable_tmpdir()
                )
                self.output.info(
                    "[HMBS tmp] test TMPDIR=%s HMBS_TMPDIR=%s"
                    % (
                        os.environ.get("TMPDIR"),
                        os.environ.get("HMBS_TMPDIR"),
                    )
                )
            for name, _source, _lang, _libs in TEST_PROGRAMS:
                executable = os.path.join(self.build_folder, self._exe_name(name))
                if runtime_dir is not None:
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(executable, staged)
                    self._sign_ohos_elf(staged)
                    executable = staged
                self.run('"{}"'.format(executable), env="conanrun")
                passed_count += 1
            tp_marker = {
                "executed": True,
                "passed": passed_count == len(TEST_PROGRAMS),
                "command": "test_opendbx && test_opendbxplus",
                "discovered": len(TEST_PROGRAMS),
                "passedCount": passed_count,
            }
            print(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker),
                flush=True,
            )
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker)
            )
            # Runnable subset of the upstream odbxtest suite: sqlite3 file
            # backend needs no server (upstream runs the same path as
            # `odbxtest -b sqlite3backend -h <dir> -d <file>`). The other
            # eight backends need live database servers with per-site
            # credentials (Gentoo RESTRICTs them as interactive-only) and
            # cannot run here; they are documented in MANIFEST.yml/notes.md
            # instead of being faked. Any failure below raises and fails
            # the test package -- never silently skipped.
            dep_pkg = self.dependencies["opendbx"].package_folder
            backend_cands = sorted(
                glob.glob(
                    os.path.join(dep_pkg, "lib", "opendbx", "libsqlite3backend.so*")
                )
            )
            backend_src = self._select_backend_source(dep_pkg, backend_cands)
            upstream_dir = tempfile.mkdtemp(
                prefix="opendbx-upstream-",
                dir=self._writable_tmpdir()
                if str(self.settings.os) == "OHOS"
                else None,
            )
            try:
                # odbx_init() takes a backend NAME, not a file path: it
                # dlopens "lib<name>backend.so" via LD_LIBRARY_PATH plus the
                # compiled LIBPATH (//lib/opendbx, absent on the test
                # machine). Passing the absolute .so path makes it mangle
                # the argument into lib<abspath>backend.so and fail with
                # rc=-6. So stage the real backend file under its bare
                # soname into a writable dir, put that dir on
                # LD_LIBRARY_PATH, and pass the name "sqlite3" -- the same
                # name upstream uses (`odbxtest -b sqlite3backend` maps to
                # the sqlite3 backend). The staged copy is signed on OHOS
                # like the test executables, since dlopened .so files are
                # subject to the same code-signing enforcement.
                stage_dir = (
                    runtime_dir if runtime_dir is not None else upstream_dir
                )
                staged_backend = os.path.join(stage_dir, "libsqlite3backend.so")
                # 按字节复制为裸 soname 真实文件：不跟随悬空链的 realpath，
                # 不建软链；copyfile 会跟随有效软链复制字节，悬空链已在
                # _select_backend_source 排除。
                with open(backend_src, "rb") as src_handle:
                    backend_data = src_handle.read()
                if len(backend_data) == 0 or backend_data[:4] != b"\x7fELF":
                    raise ConanException(
                        "opendbx sqlite3 backend source is not a non-empty ELF: "
                        + backend_src
                    )
                with open(staged_backend, "wb") as dst_handle:
                    dst_handle.write(backend_data)
                if runtime_dir is not None:
                    self._sign_ohos_elf(staged_backend)
                ld_prev = os.environ.get("LD_LIBRARY_PATH")
                os.environ["LD_LIBRARY_PATH"] = (
                    stage_dir + (os.pathsep + ld_prev if ld_prev else "")
                )
                up_name, _up_src, _up_lang, _up_libs = UPSTREAM_PROGRAM
                up_exe = os.path.join(self.build_folder, self._exe_name(up_name))
                if runtime_dir is not None:
                    staged_up = os.path.join(runtime_dir, up_name)
                    shutil.copy2(up_exe, staged_up)
                    self._sign_ohos_elf(staged_up)
                    up_exe = staged_up
                up_cmd = '"{}" "{}" "{}"'.format(
                    up_exe, upstream_dir + os.sep, "sqlite3"
                )
                self.output.info(
                    "upstream sqlite3 regression: backend=sqlite3 "
                    "LD_LIBRARY_PATH={} workdir={}".format(
                        stage_dir, upstream_dir
                    )
                )
                self.run(up_cmd, env="conanrun")
            finally:
                shutil.rmtree(upstream_dir, ignore_errors=True)
            upstream_marker = {
                "status": "passed",
                "framework": "odbxtest-sqlite3-file",
                "command": "test_upstream_sqlite3 <tmpdir> sqlite3 "
                "(CREATE/INSERT/SELECT/DROP via installed libopendbx, offline)",
                "discovered": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            print(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker),
                flush=True,
            )
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker)
            )
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def _select_backend_source(self, dep_pkg, backend_cands):
        """从包内后端链选出可复制的真实 ELF 源，不用悬空链的 realpath。

        真机证据：包内 lib/opendbx/libsqlite3backend.so 为悬空软链时，
        realpath 指向缺失的 libsqlite3backend.so.1.2.0，copy2 报
        FileNotFoundError。本方法按裸 soname 优先、版本链随后排序，
        用 os.path.isfile（跟随软链，悬空返回 False）逐个试读前 4 字节
        ELF 魔数，第一个非空 ELF 即为源；全是悬空/空文件时抛带目录清单
        的 ConanException 而非 FileNotFoundError。不断言、不跳过。
        """
        backend_dir = os.path.join(dep_pkg, "lib", "opendbx")
        try:
            listing = sorted(os.listdir(backend_dir))
        except OSError:
            listing = []
        self.output.info(
            "backend candidates: {} dir: {}".format(backend_cands, listing)
        )
        if not backend_cands:
            raise ConanException(
                "opendbx sqlite3 backend not found in package lib/opendbx "
                "(expected libsqlite3backend.so from --with-backends=sqlite3) "
                "dir: {}".format(listing)
            )
        ordered = sorted(
            backend_cands,
            key=lambda p: (0 if p.endswith("libsqlite3backend.so") else 1, len(p)),
        )
        for cand in ordered:
            # 悬空软链 isfile 为 False，直接跳过。
            if not os.path.isfile(cand):
                continue
            try:
                with open(cand, "rb") as handle:
                    magic = handle.read(4)
                if magic != b"\x7fELF":
                    continue
                if os.path.getsize(cand) <= 0:
                    continue
            except OSError:
                continue
            self.output.info("selected backend source: {}".format(cand))
            return cand
        raise ConanException(
            "opendbx sqlite3 backend chain has no readable ELF "
            "(all dangling or empty) candidates: {} dir: {}".format(
                backend_cands, listing
            )
        )

    def _writable_tmpdir(self):
        """复用 hmbs 注入的可写临时目录，绝不直写只读 /tmp。"""
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    continue
                return value
        fallback = os.path.join(self.build_folder or os.getcwd(), "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _compiler(self, key):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        fallback = "clang++" if key in ("cpp", "cxx") else "clang"
        command = compilers.get(key) or fallback
        return self._resolve_command(command, fallback)

    def _resolve_command(self, command, fallback):
        basename = os.path.basename(command)
        for candidate in (
            command,
            shutil.which(basename) or "",
            os.path.join("/data/service/hnp/bin", basename),
            shutil.which(fallback) or "",
        ):
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return fallback

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = "{}.signed".format(path)
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("signed consumer has invalid .codesign: " + path)
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    @staticmethod
    def _absolute_paths(base, paths):
        result = []
        for path in paths:
            result.append(path if os.path.isabs(path) else os.path.join(base, path))
        return result

    @staticmethod
    def _exe_name(name):
        return name + ".exe" if os.name == "nt" else name
