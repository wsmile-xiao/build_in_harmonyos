#!/usr/bin/env python3
"""Conan recipe -- libscca 20250915 (Autotools).

Library and tools to access the Windows Prefetch File (SCCA) format.
Upstream tests: `make check` (automake, tests/ TESTS scripts).
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsccaConan(ConanFile):
    name = "libscca"
    version = "20250915"
    description = "Library and tools to access the Windows XML Event Log (SCCA) format"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libscca"
    url = "https://github.com/libyal/libscca"
    topics = ("forensics", "scca", "prefetch")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        # configure hard-requires a pkg-config binary even with
        # --disable-python/--disable-nls (preflight: "configure: error:
        # pkg-config not found"). Same canonical provider as
        # libcacard/2.8.1, libmrss/0.19.4 in this repo.
        self.tool_requires("pkgconf/3.0.5")
        # Upstream tests/*.sh need a real bash (`#!/usr/bin/env bash` +
        # bashisms); the preflight/CI workers have no bash on PATH
        # (test-suite.log: `env: exec bash: No such file or directory`,
        # all wrappers exit 127). Same fix as castget/2.0.1,
        # blogc/0.20.1, acpica-unix/20260408: ship bash/5.3 via the build
        # context; VirtualBuildEnv puts its bin/ on PATH for `make check`.
        self.tool_requires("bash/5.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _gettext_lib_dir(self):
        # E053 (libesedb/20240420 precedent): libyal i18n code references
        # bindtextdomain even with --disable-nls, so sccatools link needs
        # -lintl from the on-device gettext. Probe versioned dirs instead
        # of hardcoding one version; fall back to the libesedb path.
        candidates = []
        base = "/data/service/hnp/gettext.org"
        try:
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base)):
                    cand = os.path.join(base, entry, "lib")
                    if os.path.isdir(cand):
                        candidates.append(cand)
        except OSError:
            pass
        candidates.append("/data/service/hnp/gettext.org/gettext_0.26/lib")
        for cand in candidates:
            try:
                names = os.listdir(cand)
            except OSError:
                continue
            if any(n.startswith("libintl.") for n in names):
                return cand
        for cand in candidates:
            if os.path.isdir(cand):
                return cand
        return ""

    def generate(self):
        # Expose tool_requires (pkgconf) on PATH for configure probes.
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Python bindings need a full CPython dev environment; the library
        # and sccatools build without them.
        tc.configure_args.append("--disable-python")
        # NLS pulls in external gettext/libintl; the SCCA parsing logic
        # does not depend on translated messages.
        tc.configure_args.append("--disable-nls")
        # Round 2 (different strategy): round-1 appended -L/-lintl from
        # /data/service/hnp/gettext.org, but the preflight link line still
        # shows only "-lpthread -ldl" (probe found no libintl on that host),
        # so sccainfo still fails on bindtextdomain. Instead of relying
        # on an on-device lib, force configure to NOT detect NLS so the
        # libscca_i18n.c guard evaluates to a no-op. Cache variables passed
        # as VAR=VALUE assignments are honored by autoconf configure.
        tc.configure_args.append("ac_cv_header_libintl_h=no")
        tc.configure_args.append("ac_cv_func_bindtextdomain=no")
        tc.configure_args.append("ac_cv_func_textdomain=no")
        tc.configure_args.append("gt_cv_func_gnugettext_libintl=no")
        tc.configure_args.append("am_cv_func_iconv=no")
        # E053: preflight shows --disable-nls alone does NOT drop the
        # bindtextdomain reference (libscca_i18n.o in libscca.a, sccainfo
        # link fails with "undefined symbol: bindtextdomain"). Same libyal
        # family as libesedb/20240420, which links the on-device libintl.
        # Keep --disable-nls (skip po/ build) and add -lintl so any
        # remaining i18n reference links.
        gettext_lib = self._gettext_lib_dir()
        if gettext_lib:
            tc.extra_ldflags.append("-L%s" % gettext_lib)
            tc.extra_ldflags.append("-lintl")
            inc = os.path.join(os.path.dirname(gettext_lib), "include")
            if os.path.isfile(os.path.join(inc, "libintl.h")):
                tc.extra_cflags.append("-I%s" % inc)
        if str(self.settings.os) == "OHOS":
            # CI profile exports CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash
            # which does not exist on the HMBS preflight host (configure[139]:
            # "/data/service/hnp/bin/bash: inaccessible or not found").
            # Pin a verified working shell into the toolchain environment so
            # generated scripts and Makefiles record a usable SHELL.
            shell = self._ohos_shell()
            env = tc.environment()
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            tc.generate(env=env)
        else:
            tc.generate()

    def _patch_config_guess(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "HarmonyOS" in content:
            return
        insertion = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n"
            "\n"
        )
        marker = "    *:NetBSD:*:*)"
        if marker not in content:
            raise ConanException("config.guess missing NetBSD marker, cannot patch")
        content = content.replace(marker, insertion + marker, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("Patched config.guess for HarmonyOS")

    def _patch_config_sub(self, path):
        # Strategy (round 2): version-agnostic early-recognition shim.
        # Round-1 patched inner anchors only; the 2024-01-01 config.sub in
        # libscca-20250915 still rejected aarch64-unknown-linux-ohos in
        # preflight (configure --build check), so inner-anchor patching
        # alone is not trusted anymore. The shim is inserted right after
        # the shebang and short-circuits ONLY *-linux-ohos / *-ohos-linux
        # inputs to their canonical form; every other input falls through
        # to the original logic untouched. Inner patches from round-1 are
        # kept as best-effort fallback, and a runtime self-test executes
        # the patched script so a silent miss becomes a loud error here.
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "HMBS OHOS" not in content:
            lines = content.splitlines(keepends=True)
            insert_at = 1 if lines and lines[0].startswith("#!") else 0
            shim = (
                "# HMBS OHOS: recognize HarmonyOS triplets "
                "(any config.sub version).\n"
                "case \"$1\" in\n"
                "  *-*-linux-ohos)\n"
                "    echo \"$1\"\n"
                "    exit 0\n"
                "    ;;\n"
                "  *-linux-ohos)\n"
                "    _hmbs_cpu=`echo \"$1\" "
                "| sed -e 's/-linux-ohos$//;s/.*-//'`\n"
                "    case \"$_hmbs_cpu\" in\n"
                "      arm64) _hmbs_cpu=aarch64 ;;\n"
                "      amd64) _hmbs_cpu=x86_64 ;;\n"
                "    esac\n"
                "    echo \"${_hmbs_cpu}-unknown-linux-ohos\"\n"
                "    exit 0\n"
                "    ;;\n"
                "  *-ohos-linux)\n"
                "    _hmbs_cpu=`echo \"$1\" "
                "| sed -e 's/-ohos-linux$//;s/.*-//'`\n"
                "    case \"$_hmbs_cpu\" in\n"
                "      arm64) _hmbs_cpu=aarch64 ;;\n"
                "      amd64) _hmbs_cpu=x86_64 ;;\n"
                "    esac\n"
                "    echo \"${_hmbs_cpu}-unknown-linux-ohos\"\n"
                "    exit 0\n"
                "    ;;\n"
                "esac\n"
            )
            content = (
                "".join(lines[:insert_at]) + shim + "".join(lines[insert_at:])
            )
        # Best-effort inner patches (round-1 logic, now non-fatal: the
        # shim above already guarantees ohos recognition).
        if "linux-ohos" not in content or "ohos-linux" not in content:
            m = re.search(
                r"(\s*android-linux\)\s*\n)"
                r"(\s*basic_machine=\$field1-unknown\s*\n)"
                r"(\s*basic_os=linux-android\s*\n)"
                r"(\s*;;\s*\n)",
                content,
            )
            if m:
                ind_machine = re.match(
                    r"(\s*)basic_machine", m.group(2)).group(1)
                ind_os = re.match(
                    r"(\s*)basic_os", m.group(3)).group(1)
                ind_semi = re.match(r"(\s*);;", m.group(4)).group(1)
                ohos_block = (
                    m.group(1) + m.group(2) + m.group(3) + m.group(4)
                    + ind_semi + "ohos-linux)\n"
                    + ind_machine + "basic_machine=$field1-unknown\n"
                    + ind_os + "basic_os=linux-ohos\n"
                    + ind_semi + ";;\n"
                )
                content = (
                    content[: m.start()] + ohos_block + content[m.end():]
                )
            if "ohos*" not in content:
                updated, n = re.subn(
                    r"gnu\*\s*\|\s*android\*",
                    lambda mm: mm.group(0) + " | ohos*",
                    content,
                    count=1,
                )
                if n:
                    content = updated
            if "linux-ohos" not in content and "linux-uclibc*" in content:
                updated, n = re.subn(
                    r"(linux-uclibc\*[/-]?\s*)\)",
                    r"\1| linux-ohos*)",
                    content,
                    count=1,
                )
                if n:
                    content = updated
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("Patched config.sub for HarmonyOS: %s" % path)
        self._verify_config_sub(path)

    def _verify_config_sub(self, path):
        # Execute the patched script against the exact triplet conan will
        # pass (--build/--host). A silent patch miss becomes a loud error
        # with actionable output instead of a bare configure failure.
        shell = self._ohos_shell()
        for triplet in ("aarch64-unknown-linux-ohos",
                        "x86_64-unknown-linux-ohos"):
            try:
                out = subprocess.check_output(
                    [shell, path, triplet],
                    stderr=subprocess.STDOUT,
                    timeout=60,
                ).decode("utf-8", errors="replace").strip()
            except subprocess.CalledProcessError as exc:
                detail = exc.output.decode(
                    "utf-8", errors="replace")[-2000:]
                raise ConanException(
                    "config.sub self-test failed for %s (rc=%s): %s"
                    % (triplet, exc.returncode, detail))
            except Exception as exc:
                raise ConanException(
                    "config.sub self-test could not run for %s: %s"
                    % (triplet, exc))
            self.output.info("config.sub self-test: %s -> %s" % (triplet, out))
            if "ohos" not in out:
                raise ConanException(
                    "config.sub self-test unexpected output for %s: %r"
                    % (triplet, out))
    def _drop_umask_077(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if "umask 077" not in data:
            return
        data = data.replace("umask 077", "umask 022")
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        self.output.info("Patched umask 077->022: %s" % os.path.basename(path))

    def _parse_test_suite_logs(self, top):
        summary = {"TOTAL": 0, "PASS": 0, "SKIP": 0, "XFAIL": 0,
                   "FAIL": 0, "XPASS": 0, "ERROR": 0}
        logs = sorted(glob.glob(
            os.path.join(top, "tests", "test-suite.log")))
        if not logs:
            logs = sorted(glob.glob(
                os.path.join(top, "**", "test-suite.log"), recursive=True))
        for log in logs:
            with open(log, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(
                        r"^# (TOTAL|PASS|SKIP|XFAIL|FAIL|XPASS|ERROR):\s*(\d+)",
                        line)
                    if m:
                        summary[m.group(1)] += int(m.group(2))
        return summary, logs

    def _ohos_shell(self):
        # Probe order: explicit env first, then PATH, then well-known OHOS
        # locations. Never return a path that does not exist (the CI profile
        # default /data/service/hnp/bin/bash is absent on HMBS hosts).
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            shutil.which("bash"),
            "/system/bin/sh",
            "/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        if os.path.isfile("/system/bin/sh"):
            return "/system/bin/sh"
        return "/bin/sh"

    def _ohos_bash(self):
        # Upstream tests/*.sh use `#!/usr/bin/env bash` plus bashisms
        # (arrays, `local`, `source`). The preflight failure signature is
        # `env: exec bash: No such file or directory` + all 3 wrappers FAIL
        # with exit 127: the shebang resolves `bash` via PATH, so a make
        # `SHELL=` override alone cannot fix it. This repo ships GNU Bash
        # 5.3 for OHOS (archives/b/bash, published 2026-04-13; on-device at
        # /data/service/hnp/bin/bash) but that dir is not on the default
        # PATH, hence the PATH lookup fails. Returns "" if no bash.
        cands = [shutil.which("bash"), os.environ.get("HMBS_BASH")]
        # Known on-device locations (absolute, no PATH needed).
        cands += [
            "/data/service/hnp/bin/bash",
            "/system/bin/bash",
            "/bin/bash",
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/storage/Users/currentUser/usr/local/bin/bash",
        ]
        for candidate in cands:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        # Last resort: scan a shallow on-device prefix for bin/bash
        # (bounded walk, no network, no install).
        for root in ("/data/service/hnp", "/storage/Users/currentUser/usr/local"):
            try:
                if not os.path.isdir(root):
                    continue
                for entry in sorted(os.listdir(root)):
                    cand = os.path.join(root, entry, "bin", "bash")
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
            except OSError:
                continue
        return ""

    def _tool_bash_path(self):
        # Absolute path of the bash/5.3 tool package binary (build context),
        # or None when the tool is not in the graph (castget/2.0.1 pattern).
        try:
            dep = self.dependencies.build["bash"]
            cand = os.path.join(dep.package_folder, "bin", "bash")
            if os.path.isfile(cand):
                return cand
        except Exception:
            pass
        for dep in self.dependencies.values():
            try:
                if dep.context == "build" and dep.ref.name == "bash" and dep.package_folder:
                    cand = os.path.join(dep.package_folder, "bin", "bash")
                    if os.path.isfile(cand):
                        return cand
            except Exception:
                continue
        return None

    def _ensure_bash_on_path(self, tmpdir):
        # Make `#!/usr/bin/env bash` resolvable for `make check`.
        # Round-3 lesson: `make SHELL=<bash>` cannot fix a shebang (PATH
        # lookup, exit 127). Round-4 lesson: aliasing bash->sh is harmful --
        # sh chokes on test_runner.sh arrays (`syntax error: unexpected '('`)
        # and turns clean 127s into confusing half-runs. So: real bash only.
        # Order: tool_requires bash (VirtualBuildEnv already puts its bin/ on
        # PATH, but prepend explicitly for certainty), then on-device spots.
        # Never fake bash. Returns the bash path or "".
        bash = self._tool_bash_path() or self._ohos_bash()
        if bash:
            bash_dir = os.path.dirname(bash)
            prev = os.environ.get("PATH", "")
            if bash_dir not in prev.split(os.pathsep):
                os.environ["PATH"] = bash_dir + os.pathsep + prev
                self.output.info("Prepended bash dir to PATH: %s" % bash_dir)
            self.output.info("Using bash for make check: %s" % bash)
            return bash
        self.output.info("No real bash found (tool bash + on-device search "
                         "empty); wrappers will FAIL with exit 127")
        return ""

    def _probe_test_tools(self):
        # Best-effort availability probe for the binaries tests/test_runner.sh
        # depends on (file/diff/gzip/zcat/sed/bash/...). Log only; never fail
        # the build here. The next preflight stdout will show which tool is
        # missing when all 3 wrappers FAIL identically.
        tools = ("bash", "sh", "file", "diff", "gzip", "zcat", "gzcat",
                 "sed", "grep", "awk", "ls", "cat", "readlink", "uname",
                 "wc", "tr", "cut", "head", "tail")
        for tool in tools:
            found = shutil.which(tool)
            self.output.info("HMBS_TEST_TOOL %s=%s" % (tool, found or "MISSING"))
        bash = self._ohos_bash()
        self.output.info("HMBS_TEST_BASH=%s" % (bash or "MISSING"))
        self.output.info("HMBS_TEST_SHELL_ENV=%s CONFIG_SHELL=%s" % (
            os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")))
        self.output.info("HMBS_TEST_TMPDIR_ENV=%s TMP=%s TEMP=%s" % (
            os.environ.get("TMPDIR", ""), os.environ.get("TMP", ""),
            os.environ.get("TEMP", "")))

    def _dump_test_logs(self, top):
        # Print test-suite.log plus per-test *.log tails so a 3/3 FAIL is
        # diagnosable from the preflight stdout summary (which truncates the
        # raw `make check` output). Best-effort; never raise.
        cands = sorted(glob.glob(os.path.join(top, "tests", "*.log")))
        if not cands:
            try:
                cands = sorted(glob.glob(
                    os.path.join(top, "**", "test-suite.log"), recursive=True))
            except Exception:
                cands = []
        for path in cands[:12]:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
            except OSError:
                continue
            tail = lines[-60:] if len(lines) > 60 else lines
            self.output.info("test-log (%s) %d lines, tail:" % (path, len(lines)))
            for line in tail:
                self.output.info("  test-log| " + line[:500])

    def _patch_conan_env_scripts(self, shell):
        # conanbuild.sh sources the recipe toolchain script first, then the
        # profile conanbuildenv-*.sh which re-exports the broken
        # SHELL/CONFIG_SHELL. Rewrite those exports in place so every
        # self.run(..., env="conanbuild") inherits the working shell.
        folder = self.generators_folder
        if not folder or not os.path.isdir(folder):
            return
        pat_shell = re.compile(r'^export SHELL="[^"]*"$', re.MULTILINE)
        pat_cshell = re.compile(r'^export CONFIG_SHELL="[^"]*"$', re.MULTILINE)
        for entry in os.listdir(folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            path = os.path.join(folder, entry)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except OSError:
                continue
            updated = pat_shell.sub('export SHELL="%s"' % shell, content)
            updated = pat_cshell.sub('export CONFIG_SHELL="%s"' % shell, updated)
            if updated != content:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(updated)
                self.output.info("Patched SHELL/CONFIG_SHELL in %s" % entry)

    def _patch_configure_runtime_shell(self):
        # configure shebang #!/bin/sh does not exist on some OHOS workers;
        # point it at the verified shell. umask handled separately.
        cf = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cf):
            return
        shell = self._ohos_shell()
        try:
            with open(cf, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except OSError:
            return
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            if pattern in content:
                content = content.replace(pattern, "#!%s" % shell, 1)
                break
        with open(cf, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _setup_tmpdir(self):
        # Writable TMPDIR probe (E002/readonly_tmp): prefer HMBS-injected
        # TMPDIR/TMP/TEMP, fall back to build_folder private dirs.
        # Never use bare /tmp (/tmp is erofs read-only on OHOS) and reject
        # flag-like values. Validated by makedirs + file probe + subdir
        # probe so configure/clang mktemp paths are truly writable.
        # Only the temp root is replaced; no test is removed.
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            try:
                val = os.environ.get(key)
            except Exception:
                val = None
            if val:
                candidates.append(val)
        try:
            candidates.append(os.path.join(self.build_folder, ".hmbs-tmp"))
            candidates.append(os.path.join(self.build_folder, ".tmp"))
        except Exception:
            pass
        tmpdir = None
        for cand in candidates:
            if not cand:
                continue
            cand = cand.strip()
            if not cand or cand.startswith("-"):
                continue
            if cand in ("/tmp", "/var/tmp", "/tmp/"):
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".tmp-write-probe")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.unlink(probe)
                sub = os.path.join(cand, ".mkdtemp-probe")
                os.makedirs(sub, exist_ok=True)
                os.rmdir(sub)
                tmpdir = cand
                break
            except OSError:
                continue
            except Exception:
                continue
        if tmpdir is None:
            tmpdir = os.path.join(self.build_folder, ".hmbs-tmp")
            os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.output.info("Using TMPDIR=%s" % tmpdir)
        return tmpdir

    def _sdk_llvm_lib(self):
        # Locate the active SDK llvm/lib holding the linker runtime so the
        # configure compiler probe can load its shared deps. No hardcoded
        # version: prefer explicit env, then scan the on-device SDK root.
        env_root = os.environ.get("OHOS_SDK_LLVM_ROOT")
        if env_root and os.path.isdir(env_root):
            return env_root
        base = "/data/service/hnp/ohos-sdk.org"
        try:
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base), reverse=True):
                    cand = os.path.join(base, entry, "ohos", "native", "llvm", "lib")
                    if os.path.isdir(cand):
                        return cand
        except OSError:
            pass
        # Sibling of the active clang (e.g. /data/service/hnp/bin/clang
        # -> ../ohos-sdk... or llvm lib next to the driver).
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        cc = (compilers.get("c") if isinstance(compilers, dict) else None) or \
            os.environ.get("CC") or "/data/service/hnp/bin/clang"
        cc = cc.split()[0]
        for cand in (
            os.path.join(os.path.dirname(cc), "..", "lib"),
            "/data/service/hnp/llvm/lib",
            "/data/service/hnp/lib",
        ):
            norm = os.path.normpath(cand)
            if os.path.isdir(norm):
                # Only accept dirs that actually carry a runtime lib.
                try:
                    names = os.listdir(norm)
                except OSError:
                    continue
                if any(n.endswith(".so") for n in names):
                    return norm
        return ""

    def _dump_config_log(self):
        # Best-effort config.log tail for configure diagnostics.
        roots = []
        for attr in ("build_folder", "source_folder"):
            try:
                roots.append(getattr(self, attr))
            except Exception:
                pass
        seen = set()
        for top in roots:
            if not top or top in seen:
                continue
            seen.add(top)
            cands = [os.path.join(top, "config.log")]
            try:
                cands += sorted(glob.glob(
                    os.path.join(top, "**", "config.log"), recursive=True))
            except Exception:
                pass
            for path in cands:
                if not path or not os.path.isfile(path):
                    continue
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        lines = f.read().splitlines()
                    tail = lines[-80:] if len(lines) > 80 else lines
                    self.output.info("config.log (%s) tail:" % path)
                    for line in tail:
                        self.output.info("  config.log| " + line)
                    return
                except OSError:
                    continue

    def _is_usable_tool(self, candidate):
        # Absolute/relative paths must exist and be executable; bare names
        # must resolve via PATH. Bare /tmp-excluded: never accept flag-like
        # values. This keeps profile paths honest: a stale
        # /data/service/hnp/bin/clang (missing on some preflight hosts)
        # falls back to PATH-found clang instead of hard-failing.
        if not candidate:
            return False
        candidate = candidate.strip().split()[0] if candidate.strip() else ""
        if not candidate or candidate.startswith("-"):
            return False
        if "/" in candidate or "\\" in candidate:
            try:
                return os.path.isfile(candidate) and os.access(candidate, os.X_OK)
            except Exception:
                return False
        return shutil.which(candidate) is not None

    def _resolve_compilers(self):
        # Resolve working C/C++ compilers with existence checks. Order:
        # profile conf -> CC/CXX env -> PATH (clang/clang++/cc). A conf
        # value pointing at a missing file is skipped, not trusted blindly
        # (preflight: profile /data/service/hnp/bin/clang was absent and
        # probe failed with Error 127 "inaccessible or not found").
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        if not isinstance(compilers, dict):
            compilers = {}
        c_cands = [
            compilers.get("c"),
            os.environ.get("CC"),
            os.environ.get("HMBS_CC"),
            shutil.which("clang"),
            "clang",
            "/data/service/hnp/bin/clang",
            shutil.which("cc"),
            "cc",
            "gcc",
        ]
        cxx_cands = [
            compilers.get("cpp"),
            os.environ.get("CXX"),
            os.environ.get("HMBS_CXX"),
            shutil.which("clang++"),
            "clang++",
            "/data/service/hnp/bin/clang++",
            shutil.which("c++"),
            "c++",
            "g++",
        ]
        cc = next((c.strip().split()[0] for c in c_cands
                   if c and self._is_usable_tool(c)), "clang")
        cxx = next((c.strip().split()[0] for c in cxx_cands
                    if c and self._is_usable_tool(c)), "clang++")
        return cc, cxx

    def _probe_compiler(self, tmpdir, ld_lib):
        # Version + hello compile-link probes before configure so a broken
        # toolchain fails fast with actionable output instead of bare
        # "C compiler cannot create executables". Uses existence-checked
        # resolution so a stale profile path falls back to PATH clang.
        cc, _cxx = self._resolve_compilers()
        self.output.info("Using CC=%s (LD_LIBRARY_PATH=%s)" % (cc, ld_lib))
        self.run("%s --version" % cc, env="conanbuild", ignore_errors=True)
        hello_c = os.path.join(tmpdir, "hmbs_hello.c")
        hello_b = os.path.join(tmpdir, "hmbs_hello")
        try:
            with open(hello_c, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
        except OSError as exc:
            raise ConanException("TMPDIR not writable for probe: %s (%s)" % (tmpdir, exc))
        self.run("%s %s -o %s" % (cc, hello_c, hello_b), env="conanbuild")
        self.run("%s" % hello_b, env="conanbuild")

    def _ensure_pkg_config_alias(self, tmpdir):
        # Some autoconf checks use AC_CHECK_PROG(PKGCONFIG, pkg-config)
        # which ignores $PKG_CONFIG. Provide a `pkg-config` alias on PATH
        # delegating to the pkgconf binary from tool_requires.
        pkgconf = shutil.which("pkgconf")
        if not pkgconf:
            try:
                dep = self.dependencies.build["pkgconf"]
                cand = os.path.join(dep.package_folder, "bin", "pkgconf")
                if os.path.isfile(cand):
                    pkgconf = cand
            except Exception:
                pkgconf = None
        if not pkgconf:
            self.output.info("pkgconf binary not on PATH, skipping alias")
            return
        alias_dir = os.path.join(tmpdir, "bin")
        try:
            os.makedirs(alias_dir, exist_ok=True)
        except OSError:
            return
        alias = os.path.join(alias_dir, "pkg-config")
        try:
            if os.path.lexists(alias):
                os.unlink(alias)
            try:
                os.symlink(pkgconf, alias)
            except OSError:
                shutil.copyfile(pkgconf, alias)
            self.output.info("Aliased pkg-config -> %s" % pkgconf)
        except OSError as exc:
            self.output.info("pkg-config alias failed: %s" % exc)
            return
        prev = os.environ.get("PATH", "")
        if alias_dir not in prev.split(os.pathsep):
            os.environ["PATH"] = alias_dir + os.pathsep + prev

    def _ohos_build_env(self, tmpdir):
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        build_env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        # pkgconf recipe ships bin/pkgconf (no bin/pkg-config alias);
        # libscca configure probes for `pkg-config`. Point autoconf at
        # the pkgconf binary (detox/3.0.1 precedent in this repo).
        build_env.define("PKG_CONFIG", "pkgconf")
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            build_env.define("CONFIG_SHELL", shell)
            build_env.define("SHELL", shell)
            sdk_lib = self._sdk_llvm_lib()
            if sdk_lib:
                build_env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return build_env

    def _neutralize_nls_reference(self, src):
        # Deterministic fallback independent of configure cache variable
        # names: even if some check still defines HAVE_BINDTEXTDOMAIN or
        # ENABLE_NLS, force the bindtextdomain call site in
        # libscca/libscca_i18n.c to compile out. Semantically identical to
        # --disable-nls (E027); SCCA parsing does not use translations.
        # Only narrows the NLS call site, never touches tests.
        path = os.path.join(src, "libscca", "libscca_i18n.c")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except OSError:
            return
        old = "#if defined( HAVE_BINDTEXTDOMAIN ) && defined( LOCALEDIR )"
        if old in content:
            content = content.replace(
                old,
                "#if 0 /* HMBS OHOS: no libintl, NLS disabled */",
                1)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("Neutralized bindtextdomain call site (OHOS NLS off)")

    # Upstream e2e input (from the git-only synctestdata.sh, absent from the
    # release tarball): one small prefetch sample. The tarball
    # ships no tests/input at all, so without this the sccainfo
    # wrappers exit 77 SKIP and the HMBS gate (no skipped) can never pass.
    _TEST_DATA_URL = ("https://raw.githubusercontent.com/log2timeline/plaso/"
                      "refs/heads/main/test_data/winprefetch/CMD.EXE-087B4001.pf")
    # Mirror fallback for the e2e input (same GitHub timeout class as the
    # main source tarball: ci/conan/build_and_test.sh maps github.com to
    # gh-proxy.com first). raw.githubusercontent.com gets the same prefix
    # treatment; original URL stays last. Test-only data, never shipped.
    _TEST_DATA_URLS = (
        "https://gh-proxy.com/https://raw.githubusercontent.com/log2timeline/plaso/refs/heads/main/test_data/winprefetch/CMD.EXE-087B4001.pf",
        "https://raw.githubusercontent.com/log2timeline/plaso/refs/heads/main/test_data/winprefetch/CMD.EXE-087B4001.pf",
    )

    def _fetch_test_input_data(self, build_dir):
        # Place tests/input under the build tree (automake runs TESTS with
        # cwd=builddir/tests). Python download, no curl dependency. Test-only
        # data, never packaged or shipped.
        dest_dir = os.path.join(build_dir, "tests", "input", "public")
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as exc:
            raise ConanException("cannot create test input dir: %s" % exc)
        dest = os.path.join(dest_dir, "CMD.EXE-087B4001.pf")
        if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
            last_err = None
            for test_url in self._TEST_DATA_URLS:
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        test_url,
                        headers={"User-Agent": "conan-hmbs/1.0"})
                    with urllib.request.urlopen(req, timeout=120) as resp, \
                            open(dest, "wb") as out:
                        out.write(resp.read())
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    self.output.info(
                        "Test input download failed from %s: %s"
                        % (test_url, exc))
                    try:
                        if os.path.isfile(dest):
                            os.unlink(dest)
                    except OSError:
                        pass
                    continue
            if last_err is not None:
                raise ConanException(
                    "cannot download upstream e2e input %s: %s"
                    % (self._TEST_DATA_URL, last_err))
        size = os.path.getsize(dest)
        if size < 1024:
            raise ConanException(
                "upstream e2e input suspiciously small (%d bytes): %s"
                % (size, dest))
        self.output.info("Test input ready: %s (%d bytes)" % (dest, size))

    def _assert_test_references(self, build_dir):
        # Diagnostic-only for libscca: unlike the libfsntfs-family harness,
        # libscca's test_library/test_tools/test_sccainfo
        # wrappers do NOT record compressed reference outputs under
        # tests/input/.*/ (*.log.gz). The 2026-09-15 preflight proved it:
        # `make check` finished with `# FAIL: 0` yet this glob found 0 files
        # and wrongly failed the build. So only log the input tree (proves
        # the fetched CMD.EXE-087B4001.pf + options file were in place) and never
        # raise; the test-suite.log TOTAL/PASS/SKIP gate below is the real
        # verdict. No test is removed or skipped here.
        root = os.path.join(build_dir, "tests", "input")
        try:
            count = 0
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in sorted(filenames):
                    path = os.path.join(dirpath, name)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        size = -1
                    self.output.info("e2e input: %s (%d bytes)"
                                     % (os.path.relpath(path, build_dir), size))
                    count += 1
                    if count >= 30:
                        return
            if count == 0:
                self.output.info("e2e input tree empty under %s" % root)
        except Exception as exc:
            self.output.info("e2e input listing failed: %s" % exc)

    def build(self):
        src = self.source_folder
        self._neutralize_nls_reference(src)
        cg = os.path.join(src, "config.guess")
        if os.path.isfile(cg):
            self._patch_config_guess(cg)
        patched_sub = 0
        for _root, _dirs, _files in os.walk(src):
            for _name in _files:
                if _name == "config.sub":
                    self._patch_config_sub(os.path.join(_root, _name))
                    patched_sub += 1
        if patched_sub == 0:
            self.output.info("No config.sub found under %s" % src)
        cf = os.path.join(src, "configure")
        if os.path.isfile(cf):
            self._drop_umask_077(cf)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
            if os.path.isfile(cf):
                self._drop_umask_077(cf)

        tmpdir = self._setup_tmpdir()
        build_env = self._ohos_build_env(tmpdir)
        if str(self.settings.os) == "OHOS":
            self._patch_conan_env_scripts(self._ohos_shell())
            # Same SDK runtime for probes run outside conanbuild env.
            sdk_lib = self._sdk_llvm_lib()
            if sdk_lib:
                prev = os.environ.get("LD_LIBRARY_PATH", "")
                if sdk_lib not in prev.split(os.pathsep):
                    os.environ["LD_LIBRARY_PATH"] = (
                        sdk_lib + (os.pathsep + prev if prev else ""))
                    self.output.info("Using LD_LIBRARY_PATH=%s" % sdk_lib)

        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            cc, cxx = self._resolve_compilers()
            os.environ["CC"] = cc
            os.environ["CXX"] = cxx
            os.environ["PKG_CONFIG"] = "pkgconf"
            self._ensure_pkg_config_alias(tmpdir)
            self.output.info("Resolved compilers: CC=%s CXX=%s" % (cc, cxx))
            self._probe_compiler(tmpdir, os.environ.get("LD_LIBRARY_PATH", ""))
            autotools = Autotools(self)
            try:
                autotools.configure(args=["CC=%s" % cc, "CXX=%s" % cxx])
            except Exception:
                self._dump_config_log()
                raise
            status_path = os.path.join(self.build_folder, "config.status")
            if not os.path.isfile(status_path):
                status_path = os.path.join(src, "config.status")
            if os.path.isfile(status_path):
                with open(status_path, "r", encoding="utf-8", errors="ignore") as f:
                    before = f.read()
                if "umask 077" in before:
                    self._drop_umask_077(status_path)

            # NOTE: Autotools configure runs out-of-source in build_folder
            # (basic_layout src_folder="src"); Makefiles live in build_folder,
            # not in src. A previous revision ran `cd src && make` which always
            # failed with "No targets specified and no makefile found".
            build_dir = self.build_folder
            autotools.make(args=["-j1"])

            check_cmd = "make check -j1 (in build_folder)"
            self._probe_test_tools()
            # Fetch the git-only e2e input (tarball ships no tests/input;
            # without it sccainfo exit 77 SKIP and the HMBS
            # no-skipped gate can never pass). Test-only data, never shipped.
            self._fetch_test_input_data(build_dir)
            # Round-3 lesson: `make SHELL=<bash>` does NOT fix
            # `#!/usr/bin/env bash` (PATH lookup, exit 127 on all 3 wrappers).
            # The fix is PATH: _ensure_bash_on_path prefers the bash/5.3
            # tool_requires binary (castget/2.0.1 precedent). TMPDIR/TMP/TEMP
            # stay exported via build_env (readonly_tmp: only the temp root
            # is replaced, no test is removed or skipped).
            check_shell = self._ensure_bash_on_path(tmpdir)
            # Do NOT override SHELL for make: automake defines
            # LIBTOOL=$(SHELL) $(top_builddir)/libtool, so
            # `make SHELL=<bash>` re-interprets libtool under bash which
            # lacks `print` (this round: lines 974/980/8437/1429/1331
            # `print: command not found` + `cd: null directory` on the
            # scca_test_file link, while the library link with
            # `/bin/sh ../libtool` succeeded). bash is only needed on PATH
            # for tests/*.sh `#!/usr/bin/env bash` shebangs; SHELL stays at
            # the HMBS-injected /bin/sh.
            check_args = ["-j1"]
            if not check_shell:
                self.output.info("No bash available for make check; wrappers "
                                 "will FAIL with exit 127 (bash truly absent)")
            try:
                autotools.make(target="check", args=check_args)
                rc = 0
            except Exception:
                rc = 1
                self._dump_test_logs(build_dir)
                if not os.path.isfile(os.path.join(build_dir, "tests", "test-suite.log")):
                    self._dump_test_logs(src)
            summary, logs = self._parse_test_suite_logs(build_dir)
            if not logs:
                # Fall back to src tree (in-source configure edge case).
                summary, logs = self._parse_test_suite_logs(src)
            total = summary["TOTAL"]
            passed = summary["PASS"] + summary["XFAIL"]
            failed = summary["FAIL"] + summary["XPASS"] + summary["ERROR"]
            skipped = summary["SKIP"]
            if failed > 0 or rc != 0:
                self._dump_test_logs(build_dir)
                raise ConanException(
                    "Upstream tests failed (record run): failed=%d/%d "
                    "skipped=%d (rc=%s), see %s"
                    % (failed, total, skipped, rc, logs))
            # Falsification note: libscca has no record-mode reference outputs
            # (no *.log.gz under tests/input); a single `make check` PASS is
            # the real verdict. Log the input tree as non-vacuous proof that
            # the e2e CMD.EXE-087B4001.pf + options file were present, then evaluate
            # the test-suite.log gate below. No second `make check` re-run.
            self._assert_test_references(build_dir)
            executed = total - skipped
            if total == 0:
                raise ConanException(
                    "Upstream tests did not run (no test-suite.log TAP summary, "
                    "rc=%s, logs=%s)" % (rc, logs))
            upstream_result = {
                "status": "passed" if (failed == 0 and skipped == 0) else "failed",
                "framework": "autotools",
                "command": check_cmd,
                "discovered": total,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result))
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(upstream_result, f, ensure_ascii=False)
            if failed > 0 or skipped > 0:
                self._dump_test_logs(build_dir)
                raise ConanException(
                    "Upstream tests failed: failed=%d/%d skipped=%d (rc=%s), see %s"
                    % (failed, total, skipped, rc, logs))
            if rc != 0:
                raise ConanException(
                    "make check exit code %s with no counted failure, see %s"
                    % (rc, logs))

    def package(self):
        tmpdir = self._setup_tmpdir()
        build_env = self._ohos_build_env(tmpdir)
        if str(self.settings.os) == "OHOS":
            self._patch_conan_env_scripts(self._ohos_shell())
        try:
            with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
                autotools = Autotools(self)
                autotools.install()
        except Exception as exc:
            # 2026-09-15 preflight: `make install` dies in libscca/ at
            # `libtool: install: .../install -c .libs/libscca.a .../p//lib/libscca.a`
            # followed by `chmod 644 .../libscca.a: No such file or directory`
            # (headers installed fine via the same install shim). The worker
            # reports HMBS hardlink=0 chmod=0, so libtool's install+chmod
            # sequence cannot land the archive on this FS. Fall back to a
            # manual pickup with os.walk + copyfile (no chmod/hardlink,
            # no metadata preservation); DESTDIR stays inside build_folder.
            # Upstream tests already passed (3/3) before this stage.
            self.output.info("autotools.install failed, manual pickup: %s" % exc)
            self._manual_pickup()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json missing, cannot ship test evidence")
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def _manual_pickup(self):
        # Manual install fallback: copy built artifacts without
        # chmod/hardlink/metadata ops (worker: hardlink=0 chmod=0).
        # Layout mirrors `make install`: lib/libscca.a(.so*), include/,
        # bin/sccainfo. Raises with a build-tree excerpt when
        # an artifact class is missing.
        build_dir = self.build_folder
        pkg = self.package_folder

        def _pick_first(cands):
            for path in cands:
                if path and os.path.isfile(path):
                    return path
            return ""

        def _walk_find(filename):
            hits = []
            for root, _dirs, files in os.walk(build_dir):
                if filename in files:
                    hits.append(os.path.join(root, filename))
                    if len(hits) >= 5:
                        break
            return hits

        # --- libraries -------------------------------------------------
        lib_cands = [
            os.path.join(build_dir, "libscca", ".libs", "libscca.a"),
            os.path.join(build_dir, ".libs", "libscca.a"),
        ]
        lib_cands += _walk_find("libscca.a")
        lib_a = _pick_first(lib_cands)
        so_hits = []
        for root, _dirs, files in os.walk(build_dir):
            for name in files:
                if name.startswith("libscca.so"):
                    so_hits.append(os.path.join(root, name))
        if not lib_a and not so_hits:
            tree = []
            for root, dirs, files in os.walk(build_dir):
                level = root.replace(build_dir, "").count(os.sep)
                if level > 4:
                    dirs[:] = []
                    continue
                tree.append(root.replace(build_dir, "") or "/")
                for name in (dirs + files)[:20]:
                    tree.append("  " + name)
                if len(tree) > 60:
                    break
            raise ConanException(
                "manual pickup: libscca archive not found. "
                "Build tree excerpt:\n" + "\n".join(tree[:60]))
        lib_dir = os.path.join(pkg, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        if lib_a:
            shutil.copyfile(lib_a, os.path.join(lib_dir, "libscca.a"))
            self.output.info("manual pickup lib: %s" % lib_a)
        for src in so_hits:
            shutil.copyfile(src, os.path.join(lib_dir, os.path.basename(src)))
            self.output.info("manual pickup lib: %s" % src)

        # --- headers ---------------------------------------------------
        inc_dst = os.path.join(pkg, "include")
        inc_src_root = os.path.join(self.source_folder, "include")
        found_hdr = False
        if os.path.isdir(inc_src_root):
            for root, _dirs, files in os.walk(inc_src_root):
                for name in files:
                    if not name.endswith(".h"):
                        continue
                    src = os.path.join(root, name)
                    rel = os.path.relpath(src, inc_src_root)
                    dst = os.path.join(inc_dst, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
                    found_hdr = True
        top_hdr = os.path.join(self.source_folder, "libscca.h")
        if os.path.isfile(top_hdr):
            shutil.copyfile(top_hdr, os.path.join(inc_dst, "libscca.h"))
            found_hdr = True
        if not found_hdr:
            raise ConanException("manual pickup: no headers under %s"
                                 % inc_src_root)

        # --- tools -----------------------------------------------------
        bin_dir = os.path.join(pkg, "bin")
        copied_tools = 0
        for tool in ("sccainfo",):
            cands = [
                os.path.join(build_dir, "sccatools", ".libs", tool),
                os.path.join(build_dir, "sccatools", tool),
            ]
            cands += _walk_find(tool)
            src = _pick_first(cands)
            if src:
                os.makedirs(bin_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(bin_dir, tool))
                self.output.info("manual pickup tool: %s" % src)
                copied_tools += 1
        if copied_tools == 0:
            self.output.info("manual pickup: no sccatools binaries found "
                             "(lib-only fallback)")

    def package_info(self):
        self.cpp_info.libs = ["scca"]
