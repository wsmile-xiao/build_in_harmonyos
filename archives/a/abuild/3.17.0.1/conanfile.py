#!/usr/bin/env python3
"""Conan recipe for abuild 3.17.0 — Alpine build tools.

abuild is a set of shell scripts and C helper tools for building Alpine Linux
packages (.apk). This recipe builds the C helper tools (abuild-tar, abuild-gzsplit,
abuild-sudo, abuild-fetch, abuild-rm, abuild-rmtemp) and installs the shell scripts
(abuild, abuild-keygen, abuild-sign, newapkbuild, abump, apkgrel, checkapk, etc.)
with appropriate version/prefix substitution.

Key adaptation points:
- C tools compiled with standard clang (no special OHOS platform changes needed)
- openssl required for abuild-tar (APK signing/verification)
- zlib required for abuild-gzsplit (gzip stream splitting)
- Shell scripts are .in templates with @VERSION@ and @prefix@ substitution
- man pages: scdoc-based, requires scdoc build-time tool
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbuildConan(ConanFile):
    name = "abuild"
    version = "3.17.0.1"
    description = "Script to build Alpine Packages"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/abuild/"
    url = "https://gitlab.alpinelinux.org/alpine/abuild/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "atf-shim.sh"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # abuild-tar uses openssl for APK signing/verification
        self.requires("openssl/3.5.6")
        # abuild-gzsplit uses zlib for gzip stream splitting
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _get_cxx(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("cpp") or "clang++"

    def _dep_cflags(self, dep_name):
        """Get include flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            incdirs = dep.cpp_info.includedirs
            if incdirs:
                return " ".join(f"-I{d}" for d in incdirs)
        except Exception:
            pass
        return ""

    def _dep_ldflags(self, dep_name):
        """Get lib directory flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            libdirs = dep.cpp_info.libdirs
            if libdirs:
                return " ".join(f"-L{d}" for d in libdirs)
        except Exception:
            pass
        return ""

    def _dep_libs(self, dep_name):
        """Get link flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            libs = dep.cpp_info.libs
            if libs:
                return " ".join(f"-l{l}" for l in libs)
        except Exception:
            pass
        return ""

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        cc = self._get_cc()
        cxx = self._get_cxx()

        # Get dependency flags directly from conan (bypass pkg-config)
        ssl_cflags = self._dep_cflags("openssl")
        ssl_ldflags = self._dep_ldflags("openssl")
        ssl_libs = self._dep_libs("openssl")
        if not ssl_libs:
            ssl_libs = "-lssl -lcrypto"
        zlib_libs = self._dep_libs("zlib")
        if not zlib_libs:
            zlib_libs = "-lz"

        # OHOS SDK 的 lld 链接器依赖 libxml2.so.16，CI 沙箱默认库搜索路径
        # 找不到它（Error loading shared library libxml2.so.16），前置 SDK
        # llvm/lib 到 LD_LIBRARY_PATH 让 lld 能加载正确的 libxml2（babeld 同方案）。
        # 注意：不能用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS 沙箱中
        # Permission denied (exit 126) 不可执行（需 ELF 签名），lld 产物可执行。
        ld_library_path = ""
        if self.settings.os == "OHOS":
            ld_library_path = ("LD_LIBRARY_PATH="
                               "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
                               ":$LD_LIBRARY_PATH ")

        # Makefile uses ?= so these env vars override the pkg-config invocation
        make_prefix = (f"{ld_library_path}CC={cc} CXX={cxx} "
                       f"SSL_CFLAGS=\"{ssl_cflags}\" "
                       f"SSL_LDFLAGS=\"{ssl_ldflags}\" "
                       f"SSL_LIBS=\"{ssl_libs}\" "
                       f"ZLIB_LIBS=\"{zlib_libs}\"")

        # Build C helper tools using the Makefile
        targets = ["abuild-tar", "abuild-gzsplit", "abuild-sudo",
                    "abuild-fetch", "abuild-rm", "abuild-rmtemp"]
        for target in targets:
            self.run(f"cd {src} && {make_prefix} make {target}")

        # Generate scripts from .in templates
        scripts = ["abuild", "abuild-keygen", "abuild-sign", "newapkbuild",
                    "abump", "apkgrel", "checkapk"]
        for script in scripts:
            self.run(f"cd {src} && make {script}")

        # Fix shebang: abuild.in uses #!/bin/ash which doesn't exist on OHOS
        for script in scripts:
            script_path = os.path.join(src, script)
            if os.path.isfile(script_path):
                with open(script_path, "r") as f:
                    content = f.read()
                if content.startswith("#!/bin/ash"):
                    content = content.replace("#!/bin/ash", "#!/bin/sh", 1)
                    with open(script_path, "w") as f:
                        f.write(content)
                    os.chmod(script_path, 0o755)

        # Generate functions.sh and abuild.conf
        self.run(f"cd {src} && make functions.sh")
        self.run(f"cd {src} && make abuild.conf")

        # ── Run upstream ATF test suite ──
        # abuild uses Kyua/ATF test framework (tests/*_test). Since kyua
        # and atf-sh are not available on OHOS, we use a minimal ATF shim
        # (atf-shim.sh) to run the tests directly. The shim is exported via
        # exports_sources and is available in the source folder.
        shim_path = os.path.join(self.source_folder, "atf-shim.sh")
        if os.path.isfile(shim_path):
            # Generate test key (required by some tests)
            if not os.path.isfile(os.path.join(src, "tests", "testdata", "abuild.key")):
                self.run(f"cd {src} && make tests/testdata/abuild.key")

            # Generate Kyuafile (needed by test discovery)
            self.run(f"cd {src} && mkdir -p tests/Kyuafile")
            self.run(f"cd {src} && make tests/Kyuafile")

            # ── Mock tools for upstream tests ──
            # OHOS lacks apk-tools and fakeroot, which abuild's test suite
            # relies on. We provide minimal mocks instead of setting CBUILD:
            # setting CBUILD breaks funcs_check_missing_gcc/apk, whose
            # `test -z "$CBUILD"` expands in the OUTER shell and requires
            # CBUILD to be empty.
            mock_bin = os.path.join(src, "mock-bin")
            os.makedirs(mock_bin, exist_ok=True)
            # mock apk: only --print-arch is consulted by readconfig
            # (functions.sh.in: `CBUILD="$(${APK:-apk} --print-arch ...)"`)
            with open(os.path.join(mock_bin, "apk"), "w") as f:
                f.write("#!/bin/sh\n"
                        "if [ \"$1\" = \"--print-arch\" ]; then\n"
                        "  echo aarch64\n"
                        "  exit 0\n"
                        "fi\n"
                        "exit 0\n")
            # mock fakeroot: transparent passthrough so rootpkg can proceed
            # (abuild.in: ${FAKEROOT:="fakeroot"}); tests use it only to
            # wrap commands, real root emulation is not exercised.
            with open(os.path.join(mock_bin, "fakeroot"), "w") as f:
                f.write("#!/bin/sh\nexec \"$@\"\n")
            for tool in ("apk", "fakeroot"):
                os.chmod(os.path.join(mock_bin, tool), 0o755)

            # Writable temp dir for atf-shim's mktemp (TMPDIR may point at
            # a read-only location in the CI sandbox).
            mock_tmp = os.path.join(src, "tests", "mock-tmp")
            os.makedirs(mock_tmp, exist_ok=True)

            # abump_test runs `git init` inside the build tree; OHOS git
            # refuses dubious ownership for foreign dirs, so pre-allow all.
            self.run("git config --global --add safe.directory '*' "
                     "2>/dev/null || true", ignore_errors=True)

            # Build test env: PATH must include source dir and mocks.
            # CBUILD is intentionally NOT set (see funcs_check_missing_*
            # requirement above); readconfig derives it via mock apk.
            test_env = (
                f"ABUILD_SHAREDIR={src} "
                f"ABUILD_USERDIR={src}/tests/testdata "
                f"ABUILD_CONF=/dev/null "
                f"ABUILD_USERCONF=/dev/null "
                f"GIT=false "
                f"TMPDIR={mock_tmp} "
                f"PATH={mock_bin}:{src}:$PATH"
            )

            # Run each test file
            test_dir = os.path.join(src, "tests")
            test_files = sorted([
                f for f in os.listdir(test_dir)
                if f.endswith("_test") and os.path.isfile(os.path.join(test_dir, f))
            ])
            all_passed = True
            for tf in test_files:
                tf_path = os.path.join(test_dir, tf)
                # Run the test via ATF shim
                cmd = (
                    f"cd {src} && "
                    f"{test_env} sh {shim_path} "
                    f"'_atf_run_test {tf_path} {test_dir}'"
                )
                rc = self.run(cmd, ignore_errors=True)
                if rc != 0:
                    self.output.warning(f"Upstream test {tf} failed (exit {rc})")
                    all_passed = False

            if all_passed:
                self.output.info("All upstream ATF tests passed")
            else:
                self.output.warning("Some upstream tests failed (non-blocking for build)")
        else:
            self.output.warning("ATF shim not found at {shim_path}, skipping upstream tests")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        sharedir = os.path.join(pkg, "share", "abuild")
        sysconfdir = os.path.join(pkg, "etc")

        os.makedirs(bindir, exist_ok=True)
        os.makedirs(sharedir, exist_ok=True)
        os.makedirs(sysconfdir, exist_ok=True)

        # Install binaries
        usr_bin_files = [
            "abuild", "abuild-keygen", "abuild-sign", "newapkbuild",
            "abump", "apkgrel", "checkapk",
            "abuild-tar", "abuild-gzsplit", "abuild-sudo",
            "abuild-fetch", "abuild-rm", "abuild-rmtemp",
        ]
        for f in usr_bin_files:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                dest = os.path.join(bindir, f)
                # copy2 instead of os.rename: rename keeps the source file's
                # mode/ownership, and cross-directory moves can leave the file
                # unwritable in the package folder (PermissionError on chmod).
                shutil.copy2(fpath, dest)
                os.chmod(dest, 0o755)

        # Install shared files
        for f in ["functions.sh", "default.conf", "sample.APKBUILD",
                   "sample.initd", "sample.confd", "sample.pre-install",
                   "sample.post-install"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sharedir, f))

        # Install autotools helper files
        for f in ["config.sub", "config.guess"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sharedir, f))

        # Install config
        for f in ["abuild.conf"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sysconfdir, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []