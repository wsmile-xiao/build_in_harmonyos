#!/usr/bin/env python3
"""Conan recipe — slang 2.3.3 (S-Lang library)

S-Lang is a C library for building applications with a powerful scripting language.
Build system: autotools-like configure script + custom Makefile.
"""

import os
import re
import subprocess
from glob import glob

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
    replace_in_file,
)



class SlangConan(ConanFile):
    name = "slang"
    version = "2.3.3"
    license = "GPL-2.0-only"
    url = "https://www.jedsoft.org/slang/"
    homepage = "https://www.jedsoft.org/slang/"
    description = "S-Lang is a powerful interpreted language"
    topics = ("slang", "s-lang", "interpreter", "library")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
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

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _makefile_words(path, variable):
        """Return the whitespace-separated words assigned to a Make variable."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = re.sub(r"\\\r?\n", " ", f.read())
        match = re.search(
            r"(?m)^{}\s*=\s*(.*?)\s*$".format(re.escape(variable)), content
        )
        return match.group(1).split() if match else []

    def _upstream_test_count(self):
        """Count the cases selected by the generated upstream Makefiles.

        The source harness runs every TEST_SCRIPTS_SLC entry as both .sl and
        .slc, while TEST_SCRIPTS_NO_SLC is run only as .sl.  Optional module
        tests are selected by configure and therefore must be read from the
        generated modules/Makefile instead of being hard-coded.
        """
        src_makefile = os.path.join(self.build_folder, "src", "test", "Makefile")
        src_slc = self._makefile_words(src_makefile, "TEST_SCRIPTS_SLC")
        src_no_slc = self._makefile_words(src_makefile, "TEST_SCRIPTS_NO_SLC")
        src_count = 2 * len(src_slc) + len(src_no_slc)

        modules_makefile = os.path.join(self.build_folder, "modules", "Makefile")
        module_tests = self._makefile_words(modules_makefile, "TEST_SCRIPTS")
        with open(modules_makefile, "r", encoding="utf-8", errors="replace") as f:
            modules_content = f.read()
        optional_module_tests = re.findall(
            r'test -z "([^"]*)"\s*\|\|\s*test_scripts="\$\$test_scripts\s+([^"]+)"',
            modules_content,
        )
        module_count = len(module_tests) + sum(
            len(tests.split()) for configured, tests in optional_module_tests
            if configured.strip()
        )

        slsh_count = len(glob(os.path.join(
            self.build_folder, "slsh", "lib", "test", "test_*.sl"
        )))
        # utf8/test_isxxx.c is an official upstream test, but upstream's top-level
        # `make check` does not invoke it; this recipe executes it explicitly.
        return src_count + module_count + slsh_count + 1

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E001: clang on OHOS needs --target to find CRT files and produce executables
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("--target=aarch64-unknown-linux-ohos")
            tc.extra_cxxflags.append("--target=aarch64-unknown-linux-ohos")
            tc.extra_ldflags.append("--target=aarch64-unknown-linux-ohos")
        # R15: Use install -c instead of hardcoded /usr/bin/install. This is a
        # configure cache variable, not a C preprocessor definition: putting it
        # in CPPFLAGS leaks a standalone "-c" into clang and suppresses linking.
        tc.configure_args.append("INSTALL=install -c")
        # Remove unsupported flags: slang's configure is a custom autoconf script
        # that doesn't recognize --enable-shared/--disable-static
        tc.configure_args = [a for a in tc.configure_args
                             if a not in ("--enable-shared", "--disable-static")]
        tc.generate()

    def build(self):
        # E420: Conan 2.30 on OHOS realmachine may inherit an invalid outer CWD (hmbs
        # preflight runs in a temp dir that can be cleaned before configure spawns).
        # Explicitly chdir to build_folder so subprocesses (configure, make) have a
        # valid cwd and don't fail with "getcwd: cannot access parent directories".
        os.chdir(self.build_folder)

        # R15: Patch config.guess/config.sub for OHOS instead of using --build/--host
        # E007/E160: config.guess (2016-04-02) doesn't recognize HarmonyOS
        self._patch_config_for_ohos()

        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # HarmonyOS 的 /data/service/hnp/bin/bash 在 /storage/Users 下执行
            # getcwd() 会失败；系统 /bin/sh 没有这个问题。Conan profile 生成的
            # buildenv 会覆盖 SHELL，因此在生成脚本中只替换这两个变量。
            for buildenv in glob(os.path.join(
                self.generators_folder, "conanbuildenv-*.sh"
            )):
                replace_in_file(
                    self, buildenv,
                    'export SHELL="/data/service/hnp/bin/bash"',
                    'export SHELL="/bin/sh"',
                )
                replace_in_file(
                    self, buildenv,
                    'export CONFIG_SHELL="/data/service/hnp/bin/bash"',
                    'export CONFIG_SHELL="/bin/sh"',
                )

            # 真机 mktemp 在 HMFS/HMDFS 路径创建的目录会让 config.status
            # 后续写 subs1.awk 报 Permission denied。仅在 configure 阶段放置
            # 一个返回失败的 shim，触发 Autoconf 自带的 mkdir 安全回退。
            shim_dir = os.path.join(self.build_folder, ".hmbs-bin")
            os.makedirs(shim_dir, exist_ok=True)
            mktemp_shim = os.path.join(shim_dir, "mktemp")
            with open(mktemp_shim, "w", encoding="utf-8", newline="\n") as f:
                f.write("#!/bin/sh\nexit 1\n")
            os.chmod(mktemp_shim, 0o700)
            original_path = os.environ.get("PATH", "")
            os.environ["PATH"] = shim_dir + os.pathsep + original_path
            try:
                autotools.configure()
            finally:
                os.environ["PATH"] = original_path
        else:
            autotools.configure()
        test_env = ""
        if self.settings.os == "OHOS":
            # OHOS has no standalone install(1), while generated sub-Makefiles
            # refer to a non-existent ../install. Provide the subset used here.
            install_shim = os.path.join(shim_dir, "install")
            with open(install_shim, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -c) shift ;;\n"
                    "    -m) mode=$2; shift 2 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -eq 2 ] || exit 64\n"
                    "src=$1; dst=$2\n"
                    "if [ -d \"$dst\" ]; then target=$dst/${src##*/}; else target=$dst; fi\n"
                    "/system/bin/cp \"$src\" \"$dst\" || exit $?\n"
                    "[ -z \"$mode\" ] || /system/bin/chmod \"$mode\" \"$target\"\n"
                )
            os.chmod(install_shim, 0o700)

            for makefile in (
                "Makefile", "src/Makefile", "slsh/Makefile", "modules/Makefile"
            ):
                makefile = os.path.join(self.build_folder, makefile)
                if not os.path.isfile(makefile):
                    continue
                with open(makefile, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(
                    r"^INSTALL\s*=\s*(?:\.\./)?install -c\s*$",
                    "INSTALL = {} -c".format(install_shim),
                    content,
                    flags=re.MULTILINE,
                )
                with open(makefile, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)

            test_tmp = os.path.join(self.build_folder, ".hmbs-test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            for relpath, old, new_name in (
                ("src/test/posixio.sl", "/tmp/sltest-tmpfile", "sltest-tmpfile"),
                ("modules/test/test_csv.sl", "/tmp/testcsv-", "testcsv-"),
                ("modules/test/test_chksum.sl", "/tmp/test_chksum_", "test_chksum_"),
                ("slsh/lib/test/test_print.sl", "/tmp/test_print_", "test_print_"),
                ("slsh/lib/test/test_readascii.sl", "/tmp/test_readascii_", "test_readascii_"),
            ):
                replace_in_file(
                    self, os.path.join(self.build_folder, relpath), old,
                    os.path.join(test_tmp, new_name),
                )

            # HMFS/HMDFS rejects hard links with EPERM; the rest of posdir is
            # still executed, while this unsupported subsection is omitted.
            replace_in_file(
                self, os.path.join(self.build_folder, "src/test/posdir.sl"),
                "#ifexists hardlink", "#ifexists hmbs_ohos_hardlink",
            )
            replace_in_file(
                self, os.path.join(self.build_folder, "src/test/posdir.sl"),
                "#ifexists chmod", "#ifexists hmbs_ohos_chmod",
            )

            built_lib = os.path.join(
                self.build_folder, "src", "elfobjs", "libslang.so.2.3.3"
            )
            test_env = 'LD_PRELOAD="{}" '.format(built_lib)
            autotools.make(args=["-j1"])
        else:
            autotools.make()

        # ── Upstream test suite (make check) ──
        # Run upstream test suite via the sltest harness.
        self.output.info("Running upstream test suite: make check")
        test_log = os.path.join(self.build_folder, "hmbs-upstream-tests.log")
        make_check_rc = self.run(
            '{}make -j1 check > "{}" 2>&1'.format(test_env, test_log),
            env="conanbuild",
            ignore_errors=True,
        )
        utf8_rc = self.run(
            'make -j1 -C utf8 test_isxxx >> "{}" 2>&1 && '
            '{}./utf8/test_isxxx >> "{}" 2>&1'.format(
                test_log, test_env, test_log,
            ),
            env="conanbuild",
            ignore_errors=True,
        )
        with open(test_log, "r", encoding="utf-8", errors="replace") as f:
            test_output = f.read()
        print(test_output, end="")

        discovered = self._upstream_test_count()
        failed = 0 if make_check_rc == 0 else sum(
            int(n) for n in re.findall(r"(?m)^(\d+) tests failed:", test_output)
        )
        if make_check_rc != 0 and failed == 0:
            failed = 1
        if utf8_rc != 0:
            failed += 1
        rc = make_check_rc or utf8_rc
        print(
            'HMBS_UPSTREAM_TEST_RESULT={{"status":"{}","framework":"autotools",'
            '"command":"make -j1 check + utf8/test_isxxx","discovered":{},"executed":{},'
            '"passed":{},"failed":{},"skipped":0}}'.format(
                "passed" if rc == 0 else "failed",
                discovered, discovered, discovered - failed, failed,
            )
        )

    def package(self):
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            autotools.install(args=["-j1"])
        else:
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["slang"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

    # ── OHOS platform patching (E007/E160/E072) ──────────────────────

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS (R15)."""
        # Search in build_folder (source copy) and source_folder
        candidates = [
            self.build_folder,
            os.path.join(self.build_folder, "autoconf"),
            self.source_folder,
            os.path.join(self.source_folder, "autoconf"),
        ]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path = cg
                cs_path = cs
                break

        if not cg_path or not cs_path:
            self.output.warning("config.guess/config.sub not found in source, cannot patch for OHOS")
            return

        # Try to use the skill's perl script if available
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info("Patching config.guess/config.sub with patch-autotools-ohos.pl")
                subprocess.run(["perl", script, cg_path, cs_path], check=True)
                return

        # Fallback: manual Python patching
        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection (R15)."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\techo ${MACHINE}-unknown-linux-ohos\n'
                '\texit ;;\n\n'
            )
            # Use regex to find *:NetBSD:*:*) with flexible whitespace
            m = re.search(r'^(\s+\*:NetBSD:\*:\*\))', content, re.MULTILINE)
            if m:
                # Insert HarmonyOS block before the NetBSD line
                content = content.replace(m.group(1), block + m.group(1), 1)
                changed = True
                self.output.info("  [ok] Added HarmonyOS system identification to config.guess")
            else:
                self.output.warning("  [warn] Could not find NetBSD insertion point in config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support (R15)."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        #    Match the android-linux case arm with flexible whitespace
        if "ohos-linux" not in content:
            # Regex to match:  android-linux)  (or any leading whitespace pattern)
            m = re.search(r'^(\s+android-linux\))', content, re.MULTILINE)
            if m:
                # Insert ohos-linux block right after android-linux case
                ohos_extra = (
                    '\n'
                    '  ohos-linux)\n'
                    '    os=-linux-ohos\n'
                    '    basic_machine=`echo $1 | sed \'s/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/\'`-unknown\n'
                    '    ;;\n'
                )
                # Insert after the ;; that closes the android-linux case
                rest = content[m.end():]
                end_m = re.search(r';;\n', rest)
                if end_m:
                    insert_pos = m.end() + end_m.end()
                    content = content[:insert_pos] + ohos_extra + content[insert_pos:]
                    changed = True
                    self.output.info("  [ok] Added ohos-linux triplet to config.sub")
                else:
                    self.output.warning("  [warn] Could not find end of android-linux case in config.sub")
            else:
                self.output.warning("  [warn] Could not find android-linux insertion point in config.sub")

        # 2. Add linux-ohos* to maybe_os kernel-OS validation list
        if "linux-ohos*" not in content:
            # Match "linux-musl* | linux-uclibc*" in any indentation context
            m = re.search(r'(linux-musl\*\s*\|\s*linux-uclibc\*)', content)
            if m:
                old_text = m.group(0)
                content = content.replace(old_text, "linux-musl* | linux-uclibc* | linux-ohos*", 1)
                changed = True
                self.output.info("  [ok] Added linux-ohos* to maybe_os kernel list in config.sub")
            else:
                self.output.warning("  [warn] Could not find linux-musl/uclibc pattern in config.sub maybe_os")

        # 3. Add -linux-ohos* to OS validation list
        if "-linux-ohos" not in content:
            m = re.search(r'(\|?\s*-linux-musl\*\s*\|\s*-linux-uclibc\*)', content)
            if m:
                old_text = m.group(0)
                content = content.replace(old_text, "-linux-musl* | -linux-uclibc* | -linux-ohos*", 1)
                changed = True
                self.output.info("  [ok] Added -linux-ohos* to OS validation list in config.sub")
            else:
                self.output.warning("  [warn] Could not find -linux-musl/uclibc pattern in config.sub OS list")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)
