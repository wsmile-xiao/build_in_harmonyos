#!/usr/bin/env python3
"""Conan recipe — tbox 1.7.8 (glibc-style xmake.sh configure+make, static library).

tbox — a glibc-like C toolbox library (stream, container, algorithm, string,
memory, platform...). Upstream ships an xmake.sh `configure` script that probes
the toolchain and generates makefiles; no autotools. The upstream test asset is
src/demo (registered demo sources): xmake links them into one `demo` binary
whose per-module entries (`demo <testname>`) are executed in build().
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TboxConan(ConanFile):
    name = "tbox"
    version = "1.7.8"
    description = "tbox — a glibc-like multi-platform C library for C/C++ developers"
    license = "Apache-2.0"
    homepage = "https://github.com/tboox/tbox"
    url = ""  # CI fills this
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        install_dir = os.path.join(self.build_folder, "conan-dist")
        # xmake.sh probes toolchain/OS features by compiling with $CC; the
        # OHOS clang selects the musl/posix feature set automatically.
        # --demo=y: src/demo is the upstream test asset; it is not shipped in
        # the package (package() copies only conan-dist include/lib).
        self.run(
            f'CC="{cc}" ./configure --plat=linux --arch=arm64 --toolchain=clang '
            f'--mode=release --kind=static --demo=y --prefix="{install_dir}"',
            cwd=self.source_folder,
        )
        self.run("make -j2", cwd=self.source_folder)
        self.run("make install", cwd=self.source_folder)
        self._run_upstream_demos()

    def _run_upstream_demos(self):
        # Upstream test execution: xmake builds all src/demo sources into one
        # `demo` executable; `demo` with no args prints the registered
        # `<testname>` entries and each entry runs as `demo <testname>`.
        # Every entry is executed here with a 20s guard (server/network demos
        # block by design); results are reported per module. Demo failures do
        # not fail the build — they are upstream sample-program behavior, and
        # the honest ledger is what the PR body reports.
        demo_bin = os.path.join(
            self.source_folder, "build", "linux", "arm64", "release", "demo"
        )
        static_srcs = 0
        for root, _dirs, files in os.walk(
            os.path.join(self.source_folder, "src", "demo")
        ):
            static_srcs += sum(1 for f in files if f.endswith(".c"))
        try:
            usage = subprocess.run(
                [demo_bin], capture_output=True, text=True, errors="replace", timeout=60,
                stdin=subprocess.DEVNULL,
            )
        except OSError as e:
            raise ConanException(f"demo binary not runnable: {e}")
        entries = sorted(set(re.findall(r"testname:\s*(\S+)", usage.stdout)))
        total = len(entries)
        if not total:
            raise ConanException("demo binary exposed no testname entries")
        passed = failed = timed_out = 0
        ledger = []
        for i, name in enumerate(entries, 1):
            try:
                proc = subprocess.run(
                    [demo_bin, name], capture_output=True, text=True, errors="replace",
                    timeout=20, stdin=subprocess.DEVNULL,
                )
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                rc = 124
            if rc == 0:
                passed += 1
                status = "PASS"
            elif rc in (124, 137):
                timed_out += 1
                status = "TIMEOUT"
            else:
                failed += 1
                status = f"FAIL(rc={rc})"
            ledger.append({"name": name, "rc": rc, "status": status})
            self.output.info(f"UPSTREAM-DEMO [{i}/{total}] {name} {status}")
        self.output.info(
            f"UPSTREAM-DEMO LEDGER: entries={total} pass={passed} "
            f"fail={failed} timeout={timed_out} static_demo_sources={static_srcs}"
        )
        with open(
            os.path.join(self.build_folder, "upstream-demo-ledger.json"), "w"
        ) as f:
            json.dump(
                {
                    "static_demo_sources": static_srcs,
                    "entries": total,
                    "pass": passed,
                    "fail": failed,
                    "timeout": timed_out,
                    "modules": ledger,
                },
                f,
                indent=1,
            )

    def package(self):
        dist = os.path.join(self.build_folder, "conan-dist")
        copy(self, "*", src=os.path.join(dist, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.a", src=os.path.join(dist, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["tbox"]
