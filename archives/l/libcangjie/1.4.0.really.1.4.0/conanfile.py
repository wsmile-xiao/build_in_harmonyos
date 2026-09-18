#!/usr/bin/env python3
"""Conan recipe for libcangjie 1.4.0.really.1.4.0 on OpenHarmony PC.

libcangjie is a C library implementing the Cangjie input method.
Upstream uses the Meson build system and depends only on sqlite3.
The database (data/table.txt -> cangjie.db) is built by the
libcangjie-dbbuilder auxiliary tool during the Meson build.

Build strategy (follows libdicom/1.3.0 verified pattern):
  - tool_requires meson/1.11.0 from ohpcd (no worker-global meson on PATH)
  - MesonToolchain generates conan_meson_cross.ini; PkgConfigDeps makes the
    sqlite package visible to meson's dependency('sqlite3') lookup
    (sqlite recipe ships sqlite.pc, meson looks for sqlite3.pc, so an alias
    copy is created in the generators folder)
  - upstream test suite (meson test, 4 test binaries) runs in build() on the
    build host (native build for OHOS runs on the same aarch64 device),
    counts parsed from the meson summary
  - shared_library('cangjie', version 3.1.0) installs
    libcangjie.so.3.1.0 plus symlink aliases; HMDFS has no reliable
    symlinks so aliases are materialized as real copies (rm -f && cp)
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class LibcangjieConan(ConanFile):
    name = "libcangjie"
    version = "1.4.0.really.1.4.0"
    description = "C library implementing the Cangjie input method"
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.freedesktop.org/cangjie/libcangjie"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcangjie requires a POSIX-like target (Linux or OHOS), "
                "not %s" % self.settings.os
            )

    def requirements(self):
        self.requires("sqlite/3.53.3", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(
                    "Failed to download libcangjie source from %s: %s" % (url, error)
                )
        raise ConanInvalidConfiguration(
            "Unable to download libcangjie source from all mirrors"
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        # sqlite recipe generates sqlite.pc, meson looks for sqlite3.pc.
        gen = self.generators_folder
        src = os.path.join(gen, "sqlite.pc")
        dst = os.path.join(gen, "sqlite3.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            shutil.copy2(src, dst)
            self.output.info("aliased sqlite.pc -> sqlite3.pc for meson")

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.generate()
        self._inject_archive_tools()

    def _meson_environment(self):
        environment = Environment()
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)

        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p.strip() for p in ld_path.split(":") if p.strip()]
        if "/system/lib64" not in parts:
            parts.append("/system/lib64")
        environment.define("LD_LIBRARY_PATH", ":".join(parts))
        return environment

    def _inject_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (
            os.path.join(bindir, "llvm-ar") if bindir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )
        ninja = executables.get("ninja") or (
            os.path.join(bindir, "ninja") if bindir else ""
        )

        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insertion = "[binaries]\n"
            if ar and "\nar =" not in content:
                insertion += "ar = %r\n" % ar
            if ranlib and "ranlib =" not in content:
                insertion += "ranlib = %r\n" % ranlib
            if ninja and "ninja =" not in content:
                insertion += "ninja = %r\n" % ninja
            if insertion == "[binaries]\n":
                continue
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        with self._meson_environment().vars(self).apply():
            native_file = os.path.join(
                self.generators_folder, "conan_meson_native.ini"
            )
            self._run_meson(
                'meson setup --native-file "%s" "%s" "%s" --prefix=/'
                % (native_file, self.build_folder, self.source_folder)
            )
            self._run_meson('meson compile -C "%s" -j1' % self.build_folder)
            self._run_upstream_tests()

    def _run_meson(self, command, ignore_errors=False):
        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c") or ""
            candidate = (
                os.path.join(os.path.dirname(compiler), "ninja")
                if os.sep in compiler else ""
            )
            ninja = candidate if candidate and os.path.isfile(candidate) else ""
        if not ninja:
            ninja = shutil.which("ninja") or ""
        if ninja:
            self.run('NINJA="%s" %s' % (ninja, command), ignore_errors=ignore_errors)
        else:
            self.run(command, ignore_errors=ignore_errors)

    def _run_upstream_tests(self):
        log_path = os.path.join(self.build_folder, "meson_test.log")
        test_cmd = (
            'TEMP="%s" TMPDIR="%s" meson test -v -C "%s" '
            "--no-rebuild --print-errorlogs > \"%s\" 2>&1"
            % (self.build_folder, self.build_folder, self.build_folder, log_path)
        )
        self._run_meson(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-30:]:
            self.output.info(line)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        passed = ok
        gate_ok = (
            executed > 0 and fail == 0 and skipped == 0
            and timeout == 0 and not_run == 0
        )
        ut_status = "passed" if gate_ok else "failed"
        ut_result = {
            "status": ut_status,
            "framework": "meson",
            "command": test_cmd,
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": fail,
            "skipped": skipped,
        }
        # Persist for cache-hit rounds: `conan create` skips build() when the
        # binary is cached ("Already installed!"), so a marker printed only
        # here disappears. package() ships this JSON into res/ and
        # test_package re-emits it on EVERY run.
        result_path = os.path.join(self.build_folder, "hmbs_upstream.json")
        try:
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(ut_result, handle, ensure_ascii=False)
            self.output.info(
                "persisted upstream test result to %s" % result_path
            )
        except Exception as exc:
            self.output.warning("persist upstream result failed: %s" % exc)
        upstream_msg = (
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(ut_result, ensure_ascii=False)
        )
        print(upstream_msg, flush=True)
        self.output.info(upstream_msg)
        if ut_status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: executed=%d failed=%d "
                "skipped=%d timeout=%d not_run=%d"
                % (executed, fail, skipped, timeout, not_run)
            )

    def package(self):
        with self._meson_environment().vars(self).apply():
            self._run_meson(
                'meson install -C "%s" --destdir "%s" --no-rebuild'
                % (self.build_folder, self.package_folder)
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._materialize_shared_aliases()
        # Ship the persisted upstream result so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT even when conan skips build() on a
        # cached binary.
        hmbs_json = os.path.join(self.build_folder, "hmbs_upstream.json")
        if os.path.isfile(hmbs_json):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "hmbs_upstream.json",
                 self.build_folder, res_dir, keep_path=False)
        else:
            self.output.warning(
                "hmbs_upstream.json not found in build folder; "
                "package will lack upstream evidence"
            )

    def _materialize_shared_aliases(self):
        library_dir = os.path.join(self.package_folder, "lib")
        if not self.options.shared:
            static_lib = os.path.join(library_dir, "libcangjie.a")
            if not os.path.isfile(static_lib):
                raise ConanException(
                    "installed libcangjie static object is missing: %s"
                    % static_lib
                )
            return
        source = os.path.join(library_dir, "libcangjie.so.3.1.0")
        aliases = (
            os.path.join(library_dir, "libcangjie.so.3"),
            os.path.join(library_dir, "libcangjie.so"),
        )
        if not os.path.isfile(source) or os.path.islink(source):
            raise ConanException(
                "installed libcangjie shared object is missing: %s" % source
            )
        for alias in aliases:
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copy2(source, alias)

    def package_info(self):
        self.cpp_info.libs = ["cangjie"]
        self.cpp_info.requires = ["sqlite::sqlite"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "cangjie")]
        self.cpp_info.set_property("cmake_file_name", "libcangjie")
        self.cpp_info.set_property("cmake_target_name", "libcangjie::cangjie")
        self.cpp_info.set_property("pkg_config_name", "cangjie")
