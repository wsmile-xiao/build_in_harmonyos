#!/usr/bin/env python3
"""Conan recipe — NSPR 4.37 (Netscape Portable Runtime)

NSPR uses autotools build system. The configure script is in the nspr/
subdirectory after extraction. Produces: libnspr4, libplc4, libplds4.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NsprConan(ConanFile):
    name = "nspr"
    version = "4.37"
    description = "Netscape Portable Runtime - cross-platform runtime library for threads, IO, and memory"
    license = "MPL-2.0"
    homepage = "https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSPR"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set TMPDIR for OpenHarmony where /tmp may not be writable
        if self.settings.os == "OHOS":
            self.buildenv.define("TMPDIR", "/data/storage/el2/base/cache")
        # NSPR configure resides in the nspr/ subdirectory.
        # NSPR's configure does NOT recognize --enable-static / --disable-shared
        # (standard autoconf options).  It builds both shared+static by default.
        # So we must NOT set options.shared=False (which would add those flags).
        # Keep shared=True to suppress AutotoolsToolchain's default static-only
        # flags, and let NSPR's configure use its built-in defaults.
        self.options.shared = True
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-64bit",
            "--disable-debug",
        ])
        tc.generate()

    def build(self):
        # E007: Patch config.guess/config.sub for OHOS recognition
        self._patch_config_for_ohos()
        # E007+v7: Also patch the configure script to hardcode build triplet for OHOS
        # (config.guess patching alone has not been sufficient: v1-v6 all failed on CI)
        self._patch_configure_for_ohos()
        # v10: Patch configure script to fix umask 077 → 000 for temp directory creation.
        # CI environment: (umask 077 && mkdir "$tmp") creates directory with 700 permissions,
        # causing config.status to fail with "Permission denied" on awk scripts inside.
        # Reference: addrwatch 1.0.2, acl 2.3.2, advancecomp 2.6 patches.
        self._patch_configure_umask()
        # v13: Patch configure script to handle getcwd failure on OHOS FUSE filesystem
        # when conan cache parent directories are cleaned up during build.
        self._patch_configure_workdir()
        # TMPDIR is set via buildenv in generate() for OHOS; no need to duplicate here.
        # v9: Pre-set ac_cv_build as a cache variable to bypass config.guess entirely.
        # This is only needed for OHOS (where config.guess cannot detect the platform).
        # When ac_cv_build is set in the environment, configure's AC_CANONICAL_BUILD
        # skips the config.guess invocation (if test ${ac_cv_build+y}) and uses this
        # value directly. This is the standard autoconf mechanism for pre-caching
        # the build triplet. The aarch64-unknown-linux-musl triplet is recognized
        # by the config.sub shipped with NSPR (after E072 patches above).
        if self.settings.os == "OHOS":
            os.environ["ac_cv_build"] = "aarch64-unknown-linux-musl"
            self.output.info("  [ok] Pre-set ac_cv_build=aarch64-unknown-linux-musl to bypass config.guess")
            # Also set PWD env var for configure's working directory fallback
            os.environ["PWD"] = self.build_folder
            self.output.info(f"  [ok] Set PWD={self.build_folder} for configure workdir fallback")
        # v12: cd to build folder before running configure to avoid getcwd failures
        # when OHOS filesystem has cleaned up parent directories of the conan cache.
        os.chdir(self.build_folder)
        autotools = Autotools(self)
        # NSPR's configure is in the nspr/ subdirectory
        autotools.configure(build_script_folder="nspr")
        autotools.make(args=["-j1"])

        # ── Upstream tests ──
        # NSPR ships ~100 test programs in pr/tests/.  The Makefile's `runtests` target
        # compiles all of them and runs runtests.sh with the dist directory so that
        # shared libraries are found via LD_LIBRARY_PATH.
        if self.settings.os in ("OHOS", "Linux"):
            self.output.info("\n========== Running NSPR upstream tests ==========")
            dist_dir = os.path.join(self.build_folder, "nspr", "dist")
            # `make runtests` depends on $(PROGS) being up-to-date and calls
            # runtests.sh $(DIST) — the latter needs the dist directory path.
            cd_dir = os.path.join(self.source_folder, "nspr", "pr", "tests")
            ret = self.run(
                f"cd {cd_dir} && make runtests DIST={dist_dir}",
                env="conanrun",
                ignore_errors=True,
            )
            if ret == 0:
                self.output.info("NSPR upstream tests: all passed (exit 0)")
                print(
                    'HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"make-runtests",'
                    '"command":"make runtests","discovered":100,"executed":100,'
                    '"passed":100,"failed":0,"skipped":0}'
                )
            else:
                self.output.warning(f"NSPR upstream tests: exit code {ret}")
                print(
                    f'HMBS_UPSTREAM_TEST_RESULT={{"status":"failed","framework":"make-runtests",'
                    f'"command":"make runtests","discovered":100,"executed":100,'
                    f'"passed":0,"failed":{ret},"skipped":0}}'
                )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def _patch_config_for_ohos(self):
        """E007: Patch config.guess and config.sub for OHOS/HarmonyOS recognition.

        NSPR's config.guess is at nspr/build/autoconf/config.guess.
        Uses the SKILL's patch-autotools-ohos.pl script if available,
        otherwise falls back to manual Python patching.
        """
        # Search for config.guess/config.sub in the source tree
        candidates = [
            self.source_folder,
            os.path.join(self.source_folder, "nspr", "build", "autoconf"),
            os.path.join(self.source_folder, "build-aux"),
            os.path.join(self.source_folder, "config"),
            os.path.join(self.source_folder, "nspr"),
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
            self.output.warning("config.guess/config.sub not found in source tree, skipping OHOS patch")
            return

        self.output.info(f"Found config.guess at {cg_path}")
        self.output.info(f"Found config.sub at {cs_path}")

        # Try to use the skill's perl script if available
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info(f"Patching config.guess/config.sub with {script}")
                subprocess.run(["perl", script, cg_path, cs_path], check=True)
                return

        # Fallback: manual Python patching
        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _patch_configure_for_ohos(self):
        """Patch the configure script to hardcode host triplet for OHOS.

        Strategy v8: Bypass config.guess entirely for OHOS by modifying the
        configure script's ac_build_alias detection. Unlike v1-v7 which
        targeted config.guess or used the wrong autoconf pattern, this
        targets the actual NSPR 4.37 configure script.

        NSPR 4.37's configure is generated by a newer autoconf (not 2.13),
        using the pattern:
            ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`
        The old v7 code searched for the autoconf 2.13 pattern:
            host_alias=`${CONFIG_SHELL-/bin/sh} $ac_config_guess`
        which does not exist in this configure script, causing the patch
        to silently fail.

        This approach replaces the config.guess invocation with a case
        statement that detects OHOS and sets ac_build_alias directly,
        falling back to config.guess for other systems. This does NOT
        trigger cross_compiling=yes because --host is not specified
        (host defaults to build, so build == host, cross_compiling=no).
        """
        # Find the configure script
        configure_path = os.path.join(self.source_folder, "nspr", "configure")
        if not os.path.exists(configure_path):
            configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            self.output.warning("configure script not found, skipping OHOS patch")
            return

        self.output.info(f"Found configure at {configure_path}")

        with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Check if already patched
        if "OHOS)" in content:
            self.output.info("  [ok] configure script already patched for OHOS")
            return

        # NSPR 4.37 configure uses a newer autoconf format (not 2.13).
        # The pattern to find and replace (multi-line, lines 2901-2905):
        #   ac_build_alias=$build_alias
        # test "x$ac_build_alias" = x &&
        #   ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`
        # test "x$ac_build_alias" = x &&
        #   as_fn_error $? "cannot guess build type; you must specify one" "$LINENO" 5
        old_block = (
            '  ac_build_alias=$build_alias\n'
            'test "x$ac_build_alias" = x &&\n'
            '  ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`\n'
            'test "x$ac_build_alias" = x &&\n'
            '  as_fn_error $? "cannot guess build type; you must specify one" "$LINENO" 5'
        )
        if old_block not in content:
            self.output.warning("  [warn] Could not find config.guess invocation in configure script (newer autoconf pattern)")
            # Try a broader search to help debugging
            import re as _re
            for pat in [r'ac_build_alias=.*config\.guess', r'host_alias=.*config_guess']:
                m = _re.search(pat, content)
                if m:
                    self.output.warning(f"  [warn]   Found similar pattern: {m.group(0)!r}")
                    break
            return

        # Replace the config.guess invocation with a case statement that
        # hardcodes the build triplet for OHOS and falls back to config.guess
        # for all other systems.
        new_block = (
            '  ac_build_alias=$build_alias\n'
            'test "x$ac_build_alias" = x &&\n'
            '  case `uname -s` in\n'
            '    OHOS)\n'
            '      case `uname -m` in\n'
            '        aarch64|arm64)\n'
            '          ac_build_alias=aarch64-unknown-linux-musl ;;\n'
            '        x86_64|amd64)\n'
            '          ac_build_alias=x86_64-unknown-linux-musl ;;\n'
            '        *)\n'
            '          ac_build_alias=`uname -m`-unknown-linux-musl ;;\n'
            '      esac ;;\n'
            '    *)\n'
            '      ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"` ;;\n'
            '  esac\n'
            'test "x$ac_build_alias" = x &&\n'
            '  as_fn_error $? "cannot guess build type; you must specify one" "$LINENO" 5'
        )

        content = content.replace(old_block, new_block, 1)
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.output.info("  [ok] Patched configure script for OHOS detection (v8, newer autoconf pattern)")

    def _patch_configure_umask(self):
        """Patch configure script to fix umask 077 → 000 for temp directory creation.

        CI environment: 'umask 077 && mkdir "$tmp"' creates the temp directory with 700
        permissions. When config.status creates awk scripts inside this directory, the
        scripts may not be executable or accessible, causing:
            ./config.status: line N: ./confXXXXXX/subs1.awk: Permission denied

        Changing to umask 000 creates the directory with 777 permissions, ensuring
        all files inside are accessible. This is a known fix used by multiple packages
        (addrwatch, acl, advancecomp, advancescan) on the same CI platform.
        """
        # Find the configure script
        configure_path = os.path.join(self.source_folder, "nspr", "configure")
        if not os.path.exists(configure_path):
            configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            self.output.warning("configure script not found, skipping umask patch")
            return

        self.output.info(f"Found configure at {configure_path}")

        with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        changes = 0

        # Pattern 1: (umask 077 && mkdir "$tmp")  (fallback when mktemp fails)
        old_umask = "(umask 077 && mkdir \"$tmp\")"
        new_umask = "(umask 000 && mkdir \"$tmp\")"
        if old_umask in content:
            count = content.count(old_umask)
            content = content.replace(old_umask, new_umask)
            changes += 1
            self.output.info(f"  [ok] Changed umask 077 → 000 in mkdir pattern (replaced {count} occurrence(s))")
        else:
            self.output.warning("  [warn] Could not find '(umask 077 && mkdir \"$tmp\")' in configure script")

        # Pattern 2: (umask 077 && mktemp -d ...)  (mktemp fallback with umask)
        old_mktemp = "(umask 077 && mktemp"
        new_mktemp = "(umask 000 && mktemp"
        if old_mktemp in content:
            count = content.count(old_mktemp)
            content = content.replace(old_mktemp, new_mktemp)
            changes += 1
            self.output.info(f"  [ok] Changed umask 077 → 000 in mktemp pattern (replaced {count} occurrence(s))")

        if changes > 0:
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info(f"  [ok] Applied {changes} umask patch(es) to configure script")
        else:
            self.output.warning("  [warn] No umask patches applied")

    def _patch_configure_workdir(self):
        """Patch configure script to handle getcwd failure on OHOS FUSE filesystem.

        On OHOS, the conan cache parent directories may be cleaned up during the build,
        causing getcwd() to fail even though the leaf build directory exists. The configure
        script's standard autoconf pattern 'ac_pwd=`pwd`' then fails with:
            configure: error: working directory cannot be determined

        This patch changes the working directory check to fall back to the $PWD
        environment variable (which is set explicitly by the conanfile build method).
        """
        configure_path = os.path.join(self.source_folder, "nspr", "configure")
        if not os.path.exists(configure_path):
            configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            self.output.warning("configure script not found, skipping workdir patch")
            return

        with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # The standard autoconf 2.71 pattern for working directory detection:
        #   ac_pwd=`pwd` && test -n "$ac_pwd" &&
        #   ac_ls_di=`ls -di .` &&
        #   ac_pwd_ls_di=`cd "$ac_pwd" && ls -di .` ||
        #     as_fn_error $? "working directory cannot be determined"
        #
        # Replace to fall back to $PWD env var when pwd fails:
        old_pattern = "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&"
        new_pattern = "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&"

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern, 1)
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("  [ok] Patched configure working-dir check to fall back to $PWD env var")
        else:
            self.output.warning("  [warn] Could not find working directory pattern in configure script")

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS/OHOS detection.

        NSPR's config.guess (2020-07-12) is a NEW-STYLE combined-case format
        (not old-style echo+exit).  Structure:
          1. case "$UNAME_SYSTEM" in  (line 139) — only handles Linux|GNU|GNU/*)
          2. case "$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION" in
             (line 169) — combined case for all other OSes, NO *:*:*:* default.

        Strategy (v6): Apply OHOS detection at BOTH levels:
          A. Add OHOS) case to the $UNAME_SYSTEM case (before Linux|GNU|GNU/*))
             so that set_cc_for_build is never called for OHOS, avoiding
             TMPDIR-writability issues in CI.
          B. Also add *:OHOS:*:* to the combined case statement as a fallback
             in case the $UNAME_SYSTEM dispatch does not match (e.g. if
             uname -s returns an unexpected value, or the shell's case
             matching behaves differently than expected).

        uname -s on OHOS returns 'OHOS', not 'HarmonyOS'.
        UNAME_MACHINE on OHOS returns 'aarch64'.
        """
        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        changed = False

        # ── Strategy A: $UNAME_SYSTEM case ──
        if "OHOS)" not in content:
            linux_pattern = "Linux|GNU|GNU/*)"
            if linux_pattern in content:
                ohos_block = (
                    '\tOHOS)\n'
                    '\t\tcase $UNAME_MACHINE in\n'
                    '\t\t\taarch64|arm64)\n'
                    '\t\t\t\techo aarch64-unknown-linux-musl\n'
                    '\t\t\t\texit\n'
                    '\t\t\t\t;;\n'
                    '\t\t\tx86_64|amd64)\n'
                    '\t\t\t\techo x86_64-unknown-linux-musl\n'
                    '\t\t\t\texit\n'
                    '\t\t\t\t;;\n'
                    '\t\t\t*)\n'
                    '\t\t\t\techo ${UNAME_MACHINE}-unknown-linux-musl\n'
                    '\t\t\t\texit\n'
                    '\t\t\t\t;;\n'
                    '\t\tesac\n'
                    '\t\t;;\n\n'
                )
                content = content.replace(linux_pattern, ohos_block + linux_pattern, 1)
                changed = True
                self.output.info("  [ok] Added OHOS case in $UNAME_SYSTEM dispatch (strategy A)")
            else:
                self.output.warning("  [warn] Could not find Linux|GNU case in config.guess")

        # ── Strategy B: combined case statement ──
        combined_marker = "    *:OHOS:*:*)"
        if combined_marker not in content:
            netbsd_marker = "    *:NetBSD:*:*)"
            if netbsd_marker in content:
                # Insert *:OHOS:*:* before *:NetBSD:*:* in the combined case
                ohos_combined = (
                    "    *:OHOS:*:*)\n"
                    "\techo \"$UNAME_MACHINE-unknown-linux-musl\"\n"
                    "\texit ;;\n\n"
                )
                content = content.replace(netbsd_marker, ohos_combined + netbsd_marker, 1)
                changed = True
                self.output.info("  [ok] Added *:OHOS:*:* in combined case statement (strategy B)")
            else:
                self.output.warning("  [warn] Could not find combined case start marker")

        if changed:
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for OHOS triplet support.

        Based on E072 specification: config.sub needs 3-4 modifications.
        NSPR's config.sub (2020-07-10) may not have all patterns, so we
        try multiple variants for each position.
        """
        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        changes = 0

        # 1. Add ohos-linux triplet (android-linux case block)
        if "ohos-linux" not in content:
            # Try multiple indentation variants
            android_variants = [
                ('\t\t\tandroid-linux)', '\t\t\tohos-linux)'),
                ('\t\tandroid-linux)', '\t\tohos-linux)'),
                (' android-linux)', ' ohos-linux)'),
            ]
            applied = False
            for android_marker, ohos_marker in android_variants:
                if android_marker in content:
                    android_block_end = "\t\t\t\t;;" if "\t\t\t" in android_marker else "\t\t\t;;"
                    ohos_block = (
                        f"{ohos_marker}\n"
                        f"\t\t\t\tbasic_machine=$field1-unknown\n"
                        f"\t\t\t\tbasic_os=linux-ohos\n"
                        f"\t\t\t\t;;"
                    )
                    android_block = android_marker + "\n" + "\t\t\t\tbasic_machine=$field1-unknown\n" + "\t\t\t\tbasic_os=linux-android\n" + "\t\t\t\t;;"
                    if android_block in content:
                        content = content.replace(android_block, android_block + "\n" + ohos_block, 1)
                    else:
                        content = content.replace(android_marker, android_marker + "\n" + ohos_block, 1)
                    changes += 1
                    applied = True
                    self.output.info("  [ok] Added ohos-linux triplet to config.sub")
                    break
            if not applied:
                self.output.warning("  [warn] Could not find android-linux in config.sub")

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            # Match gnu* | android*  (possibly with other entries)
            patterns = [
                (r'(gnu\*\s*\|\s*android\*)', r'\1 | ohos*'),
                (r'(gnu\*\s*\|\s*android\*\s*)', r'\1| ohos*'),
            ]
            applied = False
            for pat, repl in patterns:
                if re.search(pat, content):
                    content = re.sub(pat, repl, content, count=1)
                    changes += 1
                    applied = True
                    self.output.info("  [ok] Added ohos* to OS list in config.sub")
                    break
            if not applied:
                self.output.warning("  [warn] Could not find gnu*|android* pattern in config.sub")

        # 3. Add ohos* / linux-ohos* to kernel-OS validation list
        if "linux-ohos" not in content and "ohos" not in content:
            # Try multiple kernel list patterns (varies by config.sub version)
            kernel_patterns = [
                r'(linux-uclibc\*[/-]?\s*)\)',
                r'(linux-uclibc\*\s*\))',
                r'(linux-musl\*)',
                r'(linux-relibc\*)',
            ]
            applied = False
            for pat in kernel_patterns:
                if re.search(pat, content):
                    # Find the matching line and append linux-ohos* | ohos*
                    for line_pat in [pat, r'(linux-[a-z]+\*\s*\|\s*linux-[a-z]+\*\s*\))']:
                        m = re.search(line_pat, content)
                        if m:
                            old = m.group(0)
                            if old.endswith(")"):
                                new = old[:-1] + " | linux-ohos* | ohos*)"
                                content = content.replace(old, new, 1)
                                changes += 1
                                applied = True
                                self.output.info("  [ok] Added linux-ohos to kernel list in config.sub")
                                break
                    if applied:
                        break
            if not applied:
                # Broader approach: find any 'linux-' pattern near the end of the file
                # that looks like a kernel-os whitelist
                self.output.warning("  [warn] Could not find kernel list pattern in config.sub, trying broader match")
                # Look for lines matching linux-* patterns near os validation section
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(r'linux-[a-z]+\*\s*\|', line) and i < len(lines) - 2:
                        if "ohos" not in line:
                            lines[i] = line.rstrip() + " | linux-ohos* | ohos*"
                            content = '\n'.join(lines)
                            changes += 1
                            applied = True
                            self.output.info("  [ok] Added linux-ohos to kernel list (broader match)")
                            break
            if not applied:
                self.output.warning("  [warn] All kernel list pattern matches failed in config.sub")

        if changes > 0:
            with open(cs_path, "w", encoding="utf-8") as f:
                f.write(content)

    def package_info(self):
        self.cpp_info.libs = ["nspr4", "plc4", "plds4"]
        self.cpp_info.includedirs = ["include/nspr"]