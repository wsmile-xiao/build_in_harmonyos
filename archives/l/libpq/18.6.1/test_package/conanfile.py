#!/usr/bin/env python3
"""Conan consumer test for libpq 18.6.1.

按 psycopg2 / psycopg-c 的方式消费：先跑包里的 bin/pg_config 问出
--includedir / --libdir，再用**它答的路径**编译 test.c 链接 -lpq（不用 conan
cpp_info 直接喂，否则 pg_config 坏了也测不出来）。build() 里同时核对：
  - `pg_config --version` == "PostgreSQL 18.6"；
  - --includedir / --libdir 与 cpp_info 指向同一目录（pg_config 按自身 bin/
    位置重定位 --prefix=/ 的编译期路径，装到哪都要答对）；
  - --includedir 下有 18.6.1 补的 pg_config.h 与 libpq/libpq-fs.h；
  - --includedir-server / --pkgincludedir 非空（psycopg2 setup.py 对空值直接抛）。
运行探针验证：
  - 新补的头能 include 且 PG_VERSION_NUM 与运行期 PQlibVersion() 一致；
  - PQlibVersion() 版本契约 == 180006；
  - PQconninfoParse URI → conninfo 字段解析（对齐上游 t/001_uri.pl）；
  - PQconnectdb 失败路径干净返回 CONNECTION_BAD（无需 PostgreSQL 服务端）。
test() 里除跑探针外再真 exec 一次 `pg_config --version`（bin 的代码签名以
「能被 exec」为准，不看 .codesign 段在不在）。
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libpq"].cpp_info
        pg_config = self._pg_config_path(dep)
        answers = self._query_pg_config(pg_config)
        self._check_pg_config_answers(answers, dep)
        cc = self._c_compiler()
        # -I/-L 只取 pg_config 的答案：与 psycopg2 setup.py / psycopg_c
        # psycopg_build_ext.py 的做法逐字相同。
        rpath = f"-Wl,-rpath,{answers['libdir']}"
        command = [
            cc, "test.c", "-o", "test_probe",
            "-I" + answers["includedir"], "-L" + answers["libdir"], "-lpq", rpath,
        ]
        serialized = (
            subprocess.list2cmdline(command)
            if str(self.settings.os) == "Windows"
            else shlex.join(command)
        )
        self.run(serialized)
        if str(self.settings.os) == "OHOS":
            self._sign_elf(Path(self.build_folder, "test_probe"))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_probe", env="conanrun")
        pg_config = self._pg_config_path(self.dependencies["libpq"].cpp_info)
        self.run(shlex.join([pg_config, "--version"]), env="conanrun")

    # ---- pg_config 消费面 ----------------------------------------------------

    _PG_CONFIG_QUERIES = (
        "version", "includedir", "libdir", "includedir-server", "pkgincludedir",
    )

    @staticmethod
    def _pg_config_path(dep):
        if not dep.bindirs:
            raise ConanInvalidConfiguration("libpq cpp_info declares no bindirs")
        pg_config = Path(dep.bindirs[0], "pg_config")
        if not pg_config.is_file():
            raise ConanInvalidConfiguration(
                f"libpq package ships no bin/pg_config: {pg_config}"
            )
        return str(pg_config)

    def _query_pg_config(self, pg_config):
        answers = {}
        for query in self._PG_CONFIG_QUERIES:
            result = subprocess.run(
                [pg_config, f"--{query}"], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise ConanException(
                    f"pg_config --{query} failed rc={result.returncode}: "
                    f"{result.stderr.strip()}"
                )
            value = result.stdout.strip()
            if not value:
                raise ConanException(f"pg_config --{query} printed nothing")
            self.output.info(f"pg_config --{query} = {value}")
            answers[query] = value
        return answers

    @staticmethod
    def _check_pg_config_answers(answers, dep):
        if answers["version"] != "PostgreSQL 18.6":
            raise ConanException(
                f"pg_config --version reports {answers['version']!r}, "
                "expected 'PostgreSQL 18.6'"
            )
        expected = {
            "includedir": Path(dep.includedirs[0]).resolve(),
            "libdir": Path(dep.libdirs[0]).resolve(),
        }
        for query, want in expected.items():
            got = Path(answers[query]).resolve()
            if got != want:
                raise ConanException(
                    f"pg_config --{query} = {got} but the package's "
                    f"{query} is {want} (relocation broken)"
                )
        includedir = Path(answers["includedir"])
        for header in ("libpq-fe.h", "pg_config.h", "libpq/libpq-fs.h",
                       "postgres_ext.h"):
            if not Path(includedir, header).is_file():
                raise ConanException(
                    f"{header} is missing under pg_config --includedir"
                )
        if not Path(answers["libdir"], "libpq.so").is_file():
            raise ConanException("libpq.so is missing under pg_config --libdir")
        for query in ("includedir-server", "pkgincludedir"):
            if not answers[query].startswith(answers["includedir"]):
                raise ConanException(
                    f"pg_config --{query} = {answers[query]} does not live "
                    f"under --includedir {answers['includedir']}"
                )

    def _sign_elf(self, executable):
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS consumer ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        compiler_path = self._c_compiler()
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        resolved = shutil.which(compiler) if compiler else None
        if not resolved:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return resolved
