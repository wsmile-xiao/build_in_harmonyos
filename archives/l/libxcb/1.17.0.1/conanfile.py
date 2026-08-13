#!/usr/bin/env python3
"""Conan recipe for libxcb 1.17.0.

X protocol C-language binding library (XCB) — the low-level C interface
to the X Window System protocol, intended as a replacement for Xlib.
Pure Autotools release tarball (pregenerated configure + Makefile.in),
so no autoreconf/automake is needed at build time.

This recipe inherits the complete OHOS adaptation validated for libxcb
1.16 (archives/l/libxcb/1.16, status=published) and lifts it to 1.17.0:
  * --build/--host GNU triplets derived from Conan settings, normalised
    to aarch64-unknown-linux-ohos so libtool keeps shared-library support.
  * config.sub + configure patches (E205/E002) declared in conandata.yml,
    matching the 1.16 hunks (upstream tarball layout is unchanged).
  * CK_FORK=no + TMPDIR-aware build env for the HAVE_CHECK-gated test suite.
  * xcb-present.pc.in xcb-dri3 Requires.private fix for check-pc-requires.
  * Recipe-local pkg-config shim: upstream configure probes xcb-proto's
    xcbincludedir/pythondir custom variables that Conan's generated
    xcb-proto.pc does not carry; the shim restores them.
  * Conan env .sh PATH bootstrap + compiler fallback: official CI workers
    expose a minimal base PATH and may not carry /data/service/hnp/bin/clang,
    so generated conanbuild*.sh / conan_toolchain.cmake are patched before
    Autotools/CMake helpers run.
  * xorgproto exported as a transitive header component (libxau/libxdmcp/
    libice/xtrans Xorg recipe pattern).

1.16 -> 1.17.0 deltas relevant to the build:
  - upstream now requires xcb-proto >= 1.17.0 (already the version in
    archives/x/xcb-proto, so no recipe change);
  - libxau bumped to 1.0.12 (the version xcb-util-renderutil/0.3.10 and
    the current libxau archive use; 1.16 used 1.0.11 which is still
    available but superseded).
"""

import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


# Extension libraries produced by libxcb (from src/Makefile.am LIBADD lists).
# xcb is the umbrella pkg-config module; each extension also installs its
# own <ext>.pc.in that configure substitutes. Consumers link the ones they
# use; package_info() declares them all so cpp_info propagates the full
# surface. This list matches the 1.16 recipe exactly (upstream layout
# unchanged in 1.17.0).
EXTENSION_LIBS = (
    "composite",
    "damage",
    "dbe",
    "dpms",
    "dri2",
    "dri3",
    "glx",
    "present",
    "randr",
    "record",
    "render",
    "res",
    "screensaver",
    "shape",
    "shm",
    "sync",
    "xf86dri",
    "xfixes",
    "xinerama",
    "xinput",
    "xkb",
    "xtest",
    "xv",
    "xvmc",
)


class LibxcbConan(ConanFile):
    name = "libxcb"
    # R37: 制品仓已存在 libxcb/1.17.0（upstream main 依赖链配方 86ec94ec5），
    # cnb.cool 不支持同版本多 revision 并存 → 适配修复必须递增版本号后缀。
    version = "1.17.0.1"
    description = "X protocol C-language binding library"
    license = "MIT"
    homepage = "https://xcb.freedesktop.org/"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxcb supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # 1.16 used libxau/1.0.11; bump to 1.0.12 — the current archive
        # and the version xcb-util-renderutil/0.3.10 already consumes.
        self.requires("libxau/1.0.12")
        self.requires("libxdmcp/1.1.5")

    def build_requirements(self):
        self.tool_requires("xcb-proto/1.17.0")
        # check/0.15.2 is a test_requires: the HAVE_CHECK-gated tests/
        # check_all suite links it but libxcb's runtime ABI does not carry
        # libcheck as a consumer dependency.
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-devel-docs")
        tc.configure_args.append("--with-doxygen=no")
        if str(self.settings.os) == "OHOS":
            # The project OHOS Conan profile maps to a linux-ohos GNU
            # triplet. Upstream's config.sub needs the companion patch in
            # this recipe (patches/0001) to accept it.
            build_triplet = self._gnu_triplet(self.settings_build)
            host_triplet = self._gnu_triplet(self.settings)
            tc.configure_args.append(f"--build={build_triplet}")
            tc.configure_args.append(f"--host={host_triplet}")
            # Automake's dependency-tracking step renames the compiler's
            # dep file (.deps/*.Tpo -> *.Po) with `mv`; on the restricted
            # OHOS FS that rename fails in the tests dir with "mv: No such
            # file or directory" (make Error 127). The dep files are build
            # metadata only, so disable dependency tracking: the compile
            # rules become plain `$(COMPILE) -c -o $@ $<` and the tests
            # still build and run unchanged.
            tc.configure_args.append("--disable-dependency-tracking")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
            self._add_dependency_flags(tc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        build_env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            # Check by default forks each test case into a child process
            # and uses socket IPC for result reporting. OHOS restricts
            # the temp/IPC locations Check uses, so run cases in-process.
            build_env.define("CK_FORK", "no")
            shell = self._resolve_shell()
            self._patch_conan_env_scripts(shell)
            build_env.define("CONFIG_SHELL", shell)
            build_env.define("SHELL", shell)
            for variable, tool in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                build_env.define(variable, self._resolve_ohos_tool(tool))
            # No pkg-config package is published in ohpcd. Upstream
            # configure probes xcb-proto's custom xcbincludedir/pythondir
            # variables that Conan's generated xcb-proto.pc omits, so the
            # recipe supplies a shim that answers those queries.
            build_env.define("PKG_CONFIG", self._write_pkg_config_shim())
            self._add_runtime_library_paths(build_env)

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            autotools.configure()
            autotools.make()
            if can_run(self):
                # tests/Makefile.am gates check_all on HAVE_CHECK, set by
                # PKG_CHECK_MODULES(CHECK, [check >= 0.9.4]). With check
                # in test_requires, make check compiles and runs the full
                # START_TEST suite (xcb_parse_display, xcb_simple, etc.)
                # against the freshly built libxcb.la. Run it through
                # subprocess so the harness output is captured, echoed to
                # the log, and parsed into the HMBS_UPSTREAM_TEST_RESULT
                # evidence marker (make check alone exits 0 even when the
                # HAVE_CHECK-gated suite is silently skipped).
                self._run_upstream_make_check()
            else:
                self.output.warning(
                    "Skipping upstream make check because the target cannot run on this host."
                )

    def _run_upstream_make_check(self):
        """Run upstream `make check` and emit the HMBS_UPSTREAM_TEST_RESULT
        evidence marker.

        tests/Makefile.am declares TESTS = check-pc-requires plus the
        HAVE_CHECK-gated check_all (libcheck START_TEST suite). The automake
        test harness prints a summary block at the end:

            # TOTAL: N
            # PASS:  N
            # SKIP:  0
            # XFAIL: 0
            # FAIL:  0
            # XPASS: 0
            # ERROR: 0

        We capture that output, echo it to the log, parse the summary, and
        emit the marker with the real framework numbers. Any FAIL/ERROR or
        non-zero exit marks the run failed and raises, so conan create
        fails honestly — the numbers are never hardcoded.
        """
        make_bin = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        # -j1 matches the conan-managed invocation (tools.build:jobs=1,
        # as injected by HMBS) that previously ran `make check` green on
        # this host; the parallel default build is what exercised the
        # dependency-tracking `mv` race in the tests dir.
        check_cmd = [make_bin, "-j1", "check"]
        check_env = os.environ.copy()
        if str(self.settings.os) == "OHOS":
            # The preflight PATH exposes no standalone coreutils, and the
            # toybox shell (/system/bin/sh) cannot resolve them either
            # ("rm: inaccessible or not found", attempt 31166): toybox
            # applet symlinks live under /system/bin, a directory that
            # configure/make all never need but the automake check harness
            # does (the check_all link rule opens with `@rm -f check_all`;
            # libtool and the test driver use rm/mv as well). Prepending
            # /system/bin to THIS env dict works where the earlier
            # os.environ PATH shims did not: the dict is handed to make
            # verbatim, so conan build-env re-application cannot strip it.
            system_bin = "/system/bin"
            if os.path.isdir(system_bin):
                check_env["PATH"] = system_bin + os.pathsep + check_env.get("PATH", "")
            if not shutil.which("rm", path=check_env.get("PATH", "")):
                self.output.warning(
                    "No rm executable on make-check PATH: "
                    + check_env.get("PATH", "")
                )
        proc = subprocess.run(
            check_cmd,
            cwd=self.build_folder,
            env=check_env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if output:
            self.output.info("upstream `make check` output:\n" + output)

        summary = self._parse_make_check_summary(output)
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        skipped = summary["skipped"]
        executed = total - skipped
        ok = proc.returncode == 0 and failed == 0 and executed > 0
        marker = {
            "status": "passed" if ok else "failed",
            "framework": "automake",
            "command": "make -j1 check",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # The HMBS_UPSTREAM_TEST_RESULT marker itself is emitted by the
        # test_package stage (which always runs), reading this summary from
        # the package — a later preflight may reuse the cached binary and
        # skip build(), so a build()-only marker would vanish from the log
        # and hmbs would judge the upstream tests as never executed.
        summary_path = os.path.join(self.build_folder, "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False)
        self.output.info("upstream test summary written: " + summary_path)
        if not ok:
            raise ConanException(
                "upstream make check failed "
                f"(exit {proc.returncode}): {json.dumps(marker)}"
            )

    def _parse_make_check_summary(self, output):
        """Parse the automake test-harness summary from `make check` output.

        `make check` is recursive: each subdir with TESTS prints its own
        '# TOTAL:/# PASS:/...' block (libxcb emits one in tests/ for
        check_all and one at top level for check-pc-requires). All blocks
        are summed so the counts cover the whole upstream suite — taking
        only the last block undercounts (e.g. 1 instead of 2). Falls back
        to counting 'PASS:'/'FAIL:'/'SKIP:'/'ERROR:' result lines when no
        summary block is present. Returns a dict with
        total/passed/failed/skipped counts.
        """
        totals = re.findall(r"^# TOTAL:\s*(\d+)\s*$", output, re.MULTILINE)
        if totals:
            def _sum(pattern):
                hits = re.findall(pattern, output, re.MULTILINE)
                return sum(int(hit) for hit in hits)

            total = sum(int(value) for value in totals)
            passed = _sum(r"^# PASS:\s*(\d+)\s*$") + _sum(r"^# XPASS:\s*(\d+)\s*$")
            failed = _sum(r"^# FAIL:\s*(\d+)\s*$") + _sum(r"^# ERROR:\s*(\d+)\s*$")
            skipped = _sum(r"^# SKIP:\s*(\d+)\s*$") + _sum(r"^# XFAIL:\s*(\d+)\s*$")
            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
        passed = len(re.findall(r"^PASS:\s+", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL:\s+", output, re.MULTILINE))
        skipped = len(re.findall(r"^SKIP:\s+", output, re.MULTILINE))
        errored = len(re.findall(r"^ERROR:\s+", output, re.MULTILINE))
        return {
            "total": passed + failed + skipped + errored,
            "passed": passed,
            "failed": failed + errored,
            "skipped": skipped,
        }

    def package(self):
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # The HMBS runtime `install` helper (HMBS_INSTALL, detected by
            # configure as the BSD-compatible install) silently rejects
            # multi-source invocations with exit 64 (EX_USAGE). automake's
            # install-data rules call `install -c -m 644` with many sources
            # at once for man pages (install-libmanDATA failed with
            # "Error 64" on the device), headers and *.pc files. Libraries
            # install fine because libtool drives `install` one source at a
            # time, so run install-exec only and copy the data files with
            # Conan copy() (single-file copies, no install helper involved).
            autotools.make(
                target="install-exec", args=[f"DESTDIR={self.package_folder}"]
            )
            self._install_data_files()
        else:
            autotools.install()
        self._patch_libtool_libdir()
        # Carry the upstream make-check summary into the package so the
        # test_package stage can emit HMBS_UPSTREAM_TEST_RESULT even when a
        # later preflight reuses the cached binary (build() skipped). See
        # _run_upstream_make_check() for how the summary is produced.
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            copy(
                self,
                "upstream_test_summary.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _install_data_files(self):
        # Mirrors what automake's install-data rules would install, copied
        # directly so the constrained `install` helper is never invoked with
        # multiple sources. All headers land flat in include/xcb/ (automake
        # strips the xcb/ build-dir prefix to the basename), matching the
        # upstream layout consumed via <xcb/xcb.h>.
        include_xcb = os.path.join(self.package_folder, "include", "xcb")
        for header in ("xcb.h", "xcbext.h", "xcb_windefs.h"):
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "src"),
                dst=include_xcb,
                keep_path=False,
            )
        # Headers generated by xcb-proto's c_client.py land FLAT in the
        # build src dir (EXTSOURCES are plain basenames, see src/Makefile.am:
        # EXTHEADERS = EXTSOURCES:.c=.h), not under a xcb/ subdir. They are
        # installed by upstream with their basename into include/xcb/, which
        # is how consumers resolve <xcb/bigreq.h> etc.
        generated = os.path.join(self.build_folder, "src")
        if os.path.isdir(generated):
            copy(self, "*.h", src=generated, dst=include_xcb, keep_path=False)
        copy(
            self,
            "*.pc",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
            keep_path=False,
        )
        man3 = os.path.join(self.package_folder, "share", "man", "man3")
        for man_source in (
            os.path.join(self.build_folder, "src", "man"),
            os.path.join(self.build_folder, "man"),
        ):
            if os.path.isdir(man_source):
                copy(self, "*.3", src=man_source, dst=man3, keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libxcb")
        self.cpp_info.set_property("cmake_target_name", "libxcb::libxcb")
        self.cpp_info.set_property("pkg_config_name", "xcb")

        core = self.cpp_info.components["xcb"]
        core.libs = ["xcb"]
        core.requires = [
            "libxau::libxau",
            "libxdmcp::libxdmcp",
            "xorgproto::xorgproto",
        ]
        core.set_property("cmake_target_name", "libxcb::xcb")
        core.set_property("pkg_config_name", "xcb")
        if str(self.settings.os) in ("Linux", "OHOS"):
            core.system_libs = ["pthread"]

        for extension in EXTENSION_LIBS:
            component = self.cpp_info.components[extension]
            component.libs = [f"xcb-{extension}"]
            component.requires = ["xcb"]
            component.set_property("cmake_target_name", f"libxcb::{extension}")
            component.set_property("pkg_config_name", f"xcb-{extension}")

    def _patch_libtool_libdir(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def _resolve_ohos_tool(self, tool):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in ("c", "cpp"):
            compiler_command = compilers.get(compiler)
            if not compiler_command:
                continue
            compiler_path = str(compiler_command).split()[0].strip("\"'")
            candidate = os.path.join(os.path.dirname(compiler_path), tool)
            if os.path.exists(candidate):
                return candidate
        return shutil.which(tool) or tool

    def _gnu_triplet(self, settings):
        compiler = settings.get_safe("compiler")
        triplet = _get_gnu_triplet(
            str(settings.os),
            str(settings.arch),
            str(compiler) if compiler else None,
        )
        if str(settings.os) == "OHOS":
            system = triplet["system"]
            if not system.startswith("linux-"):
                system = f"linux-{system}"
            return f"{triplet['machine']}-unknown-{system}"
        return triplet["triplet"]

    def _resolve_shell(self):
        # Prefer a non-default shell path: GNU make direct-execs simple
        # recipe commands (skipping the shell) only when the Makefile's
        # SHELL equals its built-in default (/bin/sh). The OHOS image has no
        # standalone toybox applet symlinks for rm/mv/... on PATH, so those
        # execs fail with "rm: No such file or directory" (Error 127). With
        # SHELL = a non-default path (/system/bin/sh), make runs every recipe
        # through the shell, which resolves the applets internally.
        for candidate in (
            "/system/bin/sh",
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def _patch_conan_env_scripts(self, shell):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return
        bootstrap = ":".join(bootstrap_paths)
        marker = "# libxcb OHOS PATH bootstrap"
        for entry in os.listdir(generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(generators_folder, entry)
            with open(script_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            if marker not in content:
                content = f'{marker}\nexport PATH="{bootstrap}:${{PATH}}"\n' + content
            if shell:
                content = re.sub(
                    r'^export SHELL="[^"]*"$',
                    f'export SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r'^export CONFIG_SHELL="[^"]*"$',
                    f'export CONFIG_SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
            content = self._patch_missing_compiler_exports(content)

            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _patch_missing_compiler_exports(self, content):
        for variable, replacement in {
            "CC": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }.items():
            if replacement:
                content = re.sub(
                    rf'^export {variable}="[^"]*"$',
                    f'export {variable}="{replacement}"',
                    content,
                    flags=re.MULTILINE,
                )
        return content

    def _fallback_compiler(self, compiler_key, fallback_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(compiler_key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return None
        fallback = shutil.which(fallback_name)
        if fallback and os.path.exists(fallback) and os.access(fallback, os.X_OK):
            return fallback
        return None

    def _add_dependency_flags(self, toolchain):
        for name in ("xorgproto", "libxau", "libxdmcp", "check"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            include_dir = os.path.join(package_folder, "include")
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(include_dir):
                toolchain.extra_cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                toolchain.extra_ldflags.append(f"-L{lib_dir}")

    def _add_runtime_library_paths(self, build_env):
        for name in ("libxau", "libxdmcp", "check"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(lib_dir):
                build_env.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def _prepend_ohos_tool_paths(self):
        tool_paths = self._ohos_tool_paths()
        existing = os.environ.get("PATH", "")
        for path in reversed(tool_paths):
            if os.path.isdir(path):
                if path not in existing.split(os.pathsep):
                    existing = path + (os.pathsep + existing if existing else "")
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]

    def _write_pkg_config_shim(self):
        modules = self._pkg_config_modules()
        shim = os.path.join(self.build_folder, "pkg-config-libxcb.py")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                "import re\n"
                "import sys\n"
                f"MODULES = {json.dumps(modules, sort_keys=True)}\n"
                "def requested_modules(args):\n"
                "    found = []\n"
                "    for arg in args:\n"
                "        if arg.startswith('-'):\n"
                "            continue\n"
                "        for token in re.split(r'\\s+|>=|<=|=|>|<', arg):\n"
                "            if token in MODULES and token not in found:\n"
                "                found.append(token)\n"
                "    return found\n"
                "def main():\n"
                "    args = sys.argv[1:]\n"
                "    if any(arg.startswith('--atleast-pkgconfig-version') for arg in args):\n"
                "        return 0\n"
                "    modules = requested_modules(args)\n"
                "    if not modules:\n"
                "        return 0\n"
                "    unknown = [module for module in modules if module not in MODULES]\n"
                "    if unknown:\n"
                "        return 1\n"
                "    if any(arg.startswith('--exists') for arg in args):\n"
                "        return 0\n"
                "    if any(arg.startswith('--atleast-version') for arg in args):\n"
                "        return 0\n"
                "    if '--modversion' in args:\n"
                "        print(MODULES[modules[0]]['version'])\n"
                "        return 0\n"
                "    for arg in args:\n"
                "        if arg.startswith('--variable='):\n"
                "            variable = arg.split('=', 1)[1]\n"
                "            print(MODULES[modules[0]].get('variables', {}).get(variable, ''))\n"
                "            return 0\n"
                "    output = []\n"
                "    if '--cflags' in args:\n"
                "        for module in modules:\n"
                "            output.extend(MODULES[module]['cflags'])\n"
                "    if '--libs' in args:\n"
                "        for module in modules:\n"
                "            output.extend(MODULES[module]['libs'])\n"
                "    print(' '.join(flag for flag in output if flag))\n"
                "    return 0\n"
                "sys.exit(main())\n"
            )
        return f"{sys.executable} {shim}"

    def _pkg_config_modules(self):
        xcb_proto = self._dependency_folder("xcb-proto")
        return {
            "check": self._module("check", "0.15.2", "check"),
            # 1.16 used libxau/1.0.11; bump to 1.0.12 to match the bumped
            # runtime requirement and the current libxau archive.
            "xau": self._module("libxau", "1.0.12", "Xau"),
            "xdmcp": self._module("libxdmcp", "1.1.5", "Xdmcp"),
            "xcb-proto": {
                "version": "1.17.0",
                "cflags": [],
                "libs": [],
                "variables": {
                    "pythondir": os.path.join(
                        xcb_proto, "lib", "python3", "site-packages"
                    )
                    if xcb_proto
                    else "",
                    "xcbincludedir": os.path.join(xcb_proto, "share", "xcb")
                    if xcb_proto
                    else "",
                },
            },
        }

    def _module(self, dependency, version, library):
        package_folder = self._dependency_folder(dependency)
        cflags = []
        libs = []
        if package_folder:
            include_dir = os.path.join(package_folder, "include")
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(include_dir):
                cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                libs.append(f"-L{lib_dir}")
        libs.append(f"-l{library}")
        return {
            "version": version,
            "cflags": cflags,
            "libs": libs,
            "variables": {},
        }

    def _dependency_folder(self, name):
        for dependencies in (
            self.dependencies.host,
            self.dependencies.build,
            self.dependencies.test,
        ):
            try:
                dependency = dependencies[name]
            except KeyError:
                continue
            return dependency.package_folder
        return None
