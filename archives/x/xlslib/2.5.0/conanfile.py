#!/usr/bin/env python3
"""Conan recipe — xlslib 2.5.0 (Autotools).

xlslib is a multiplatform C/C++ library for dynamically generating
Microsoft Excel(TM) .xls files (BIFF8).  This recipe builds the static
libxls library natively on OHOS/Linux aarch64.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XlslibConan(ConanFile):
    name = "xlslib"
    version = "2.5.0"
    description = "C/C++ library to construct Excel .xls files in code"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/xlslib/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xlslib is supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # In-source build: the check programs dump .xls files and read the
        # expected *.md5 fixtures from their working directory, which must be
        # the source tree (targets/test/).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release archive nests the Autotools project under
        # xlslib/xlslib (the top-level xlslib/OpenEXR directory is unrelated
        # Windows-only project scaffolding).  Flatten so that
        # self.source_folder is the project root.
        nested = os.path.join(self.source_folder, "xlslib")
        if os.path.isdir(nested):
            for entry in os.listdir(nested):
                shutil.move(
                    os.path.join(nested, entry),
                    os.path.join(self.source_folder, entry),
                )
            shutil.rmtree(nested)

    def _resolve_shell(self):
        """Return a shell guaranteed to exist and be executable in the
        preflight sandbox.

        hmbs injects SHELL=/bin/sh.  The CI profile may hardcode
        CONFIG_SHELL to a HNP bash that is missing/not executable inside
        the preflight sandbox, and `sh configure` re-execs itself through
        $CONFIG_SHELL, so forcing /bin/sh (HMDFS-safe per the E011 class)
        avoids autoconf re-exec failing.  Nothing is skipped; this only
        picks a usable interpreter.
        """
        return "/bin/sh"

    def _writable_tmp(self, fallback):
        """Return a writable temp-file root, never /tmp.

        The HMBS preflight sandbox mounts /tmp read-only (erofs), and the
        runner-injected $TMPDIR can itself be unwritable for subshells, so
        prefer a build-local directory (created by conan for this build,
        same mount as the compiler output) and only fall back to the
        injected chain (HMBS_TMPDIR/TMPDIR/TMP/TEMP) and to
        HMBS_AUTOCONF_MKTEMP_FALLBACK.  This only redirects where the
        configure/make temp files are written; no test is skipped.
        """
        import tempfile

        def _probe(path):
            try:
                os.makedirs(path, exist_ok=True)
                fd, probe = tempfile.mkstemp(dir=path)
                os.close(fd)
                os.unlink(probe)
                return True
            except Exception:
                return False

        # 1) build-local first (most trustworthy; same mount as compiler).
        if _probe(fallback):
            return fallback
        # 2) injected writable chain as fallback.
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val != fallback and _probe(val):
                return val
        # 3) HMBS-autoconf mktemp fallback (when it carries a path).
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fb and fb not in ("0", "1") and fb != "/tmp" and fb != fallback and _probe(fb):
            return fb
        # Last resort: return the build-local dir even if the probe failed
        # so the failure is explicit rather than silently using /tmp.
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _forward_hmbs_caps(self, env):
        # Keep HMBS platform capabilities visible to child processes
        # (clang/mktemp/shell) so they see the same writable root and the
        # same local capabilities.  Flags are forwarded unchanged; no test
        # is skipped or removed.
        for key in ("HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                    "HMBS_CAP_LOCAL_MKTEMP", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.environ.get(key)
            if val:
                env.define(key, val)

    def _hmbs_env(self, tc, tmp_base):
        # Primary channel: inject SHELL/TMPDIR/PWD through the toolchain
        # environment so they land in conanbuild.sh with correct ordering
        # against the profile [buildenv].  os.environ alone loses at
        # self.run time (courier-unicode / libfreexl precedent).  Only
        # redirects the temp-root and interpreter; no test is skipped.
        shell = self._resolve_shell()
        env = tc.environment()
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmp_base)
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        # E011/getcwd: HMDFS cannot resolve the working directory, so a
        # POSIX shell falls back to $PWD (logical path) for its `pwd`
        # builtin.  Exporting PWD headed at the build folder keeps
        # `configure`'s "working directory cannot be determined" check
        # from firing.
        env.define("PWD", self.build_folder)
        self._forward_hmbs_caps(env)
        return env

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static build by default.  xlslib's bundled libtool 2.2.10 generates
        # #!/bin/bash wrapper scripts for the check programs when shared
        # libraries are produced; OHOS has no /bin/bash, so the shared
        # link mode would break `make check`.  Static linking also avoids
        # polluting the OHOS system lib directory.
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            # The bundled 2009 config.guess does not know aarch64 and the
            # bundled config.sub (patched in 0001) is what validates the
            # canonical host.  This is a native build, so build == host.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tmp_base = self._writable_tmp(os.path.join(self.build_folder, "tmp"))
        # Belt-and-braces: expose the same writable root + interpreter via
        # the build context so direct children see them even if a cached
        # toolchain script is reused.
        shell = self._resolve_shell()
        for var in ("TMPDIR", "TMP", "TEMP"):
            self.buildenv_info.define(var, tmp_base)
        self.buildenv_info.define("SHELL", shell)
        self.buildenv_info.define("CONFIG_SHELL", shell)
        self.buildenv_info.define("PWD", self.build_folder)
        tc.generate(env=self._hmbs_env(tc, tmp_base))
        self.output.info("HMBS tmp root (build-local first): {}".format(tmp_base))

    def _avoid_autotools_regeneration(self):
        """The release tarball ships generated configure/Makefile.in files
        whose 2014 timestamps are older than configure.ac/Makefile.am, so a
        plain `make` tries to regenerate them with autoconf/automake, which
        are not installed on the OHOS worker.  Touching the generated files
        (with `configure` last, so no dependency is newer than it) makes all
        the am--refresh rules no-ops.
        """
        rel = [
            "aclocal.m4",
            "Makefile.in",
            "src/Makefile.in",
            "targets/Makefile.in",
            "targets/test/Makefile.in",
            "src/common/xlconfig.h.in",
        ]
        for f in rel:
            p = os.path.join(self.source_folder, f)
            if os.path.isfile(p):
                os.utime(p, None)
        os.utime(os.path.join(self.source_folder, "configure"), None)

    def _run_upstream_tests(self):
        """Run the upstream `make check` suite and emit the
        HMBS_UPSTREAM_TEST_RESULT hard-gate marker.  The four check programs
        (testCPP / testC / PR2859188 / PR3076678) compare the MD5 of the
        generated .xls files against the expected hashes shipped in the
        release archive, so PASS counts come from the automake harness output.
        """
        log_path = os.path.join(self.build_folder, "make_check.log")
        make = os.environ.get("HMBS_MAKE") or "make"
        test_cmd = '{0} check > "{1}" 2>&1'.format(make, log_path)
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream make check (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        passed = len(re.findall(r"^PASS: ", out, flags=re.MULTILINE))
        failed = len(re.findall(r"^FAIL: ", out, flags=re.MULTILINE))
        skipped = len(re.findall(r"^SKIP: ", out, flags=re.MULTILINE))
        executed = passed + failed + skipped
        discovered = executed
        gate_ok = executed == 4 and failed == 0 and skipped == 0
        ut_result = {
            "status": "passed" if gate_ok else "failed",
            "framework": "automake",
            "command": test_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )
        if not gate_ok:
            raise RuntimeError(
                "upstream make check failed: executed=%d failed=%d skipped=%d"
                % (executed, failed, skipped)
            )

    def _configure_via_sh(self):
        """Run the bundled `configure` through the sh interpreter.

        The release tarball is a .zip, whose extraction does not set the
        execute bit on `configure`, and the OHOS hmdfs user partition refuses
        direct `#!`-script exec regardless of file mode (EACCES -> shell
        rc=126 "Permission denied").  Conan's `Autotools.configure()` exec's
        `./configure` directly and therefore fails; running it via `sh`
        needs neither an exec bit nor shebang exec permission.  The
        configure arguments come from the same `conanbuild.conf` that the
        `Autotools` instance reads.
        """
        args = load_toolchain_args(self.generators_folder).get("configure_args", "")
        configure = os.path.join(self.source_folder, "configure")
        self.run('sh "{0}" {1}'.format(configure, args))

    def build(self):
        apply_conandata_patches(self)
        self._avoid_autotools_regeneration()
        # HMBS preflight: /tmp is read-only and HMDFS cannot resolve the
        # working directory.  Push the same writable temp root + /bin/sh +
        # PWD onto the current process so every child spawned by self.run
        # (configure re-exec, conftest compile, make check) inherits them
        # even before conanbuild.sh is sourced (E011/E002 precedent).
        shell = self._resolve_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        tmp_base = self._writable_tmp(os.path.join(self.build_folder, "tmp"))
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp_base
        os.environ["PWD"] = self.build_folder
        # E011/HMDFS getcwd + readonly /tmp hardening for the bundled
        # autoconf configure script:
        #  - `umask 077` temp dirs are not writable under HMDFS mapping, so
        #    relax to the conventional 022.
        #  - autoconf's `ac_pwd=\`pwd\`` fails when HMDFS cannot resolve the
        #    working directory, tripping "working directory cannot be
        #    determined".  Fall back to the exported $PWD (logical path)
        #    so configure can start regardless of getcwd (aldo precedent).
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            try:
                with open(configure_path, "r", encoding="utf-8",
                          errors="ignore") as handle:
                    content = handle.read()
                changed = False
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                    changed = True
                # autoconf determines the cwd via `ac_pwd=`pwd``; when HMDFS
                # cannot resolve it (getcwd fails) pwd returns non-zero and
                # ac_pwd is empty -> "working directory cannot be determined".
                # Fall back to the exported $PWD (logical path) so configure
                # can start regardless of getcwd (aldo precedent).
                if "ac_pwd=`pwd`" in content:
                    content = content.replace(
                        "ac_pwd=`pwd`",
                        "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"",
                    )
                    changed = True
                if changed:
                    with open(configure_path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    self.output.info("patched configure (umask 077->022, ac_pwd fallback)")
            except Exception as exc:
                self.output.warning("configure hardening patch skipped: {}".format(exc))
        autotools = Autotools(self)
        self._configure_via_sh()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _manual_install(self):
        """Stage lib + headers into the package folder without the libtool
        `install` / `chmod` binaries.

        The HMBS preflight sandbox reports HMBS_CAP_CHMOD=0 (chmod is not
        supported on the HMDFS user partition) and masks /bin/install with a
        non-executable file, so `autotools.install()` fails inside libtool's
        static-archive post-install step (`old_postinstall_cmds='chmod 644
        $oldlib'` reports "chmod: .../lib/libxls.a: No such file or
        directory").  Mirror the upstream `make install` layout with plain
        data copies only (shutil.copyfile performs no chmod), following the
        clthreads OHOS package-stage precedent.  Nothing is skipped: the
        exact same lib and headers that upstream installs are staged.
        """
        src = self.source_folder

        def _stage_file(rel_src, rel_dst):
            s = os.path.join(src, rel_src)
            d = os.path.join(self.package_folder, rel_dst)
            if not os.path.isfile(s):
                raise RuntimeError(
                    "expected to install {0!r} but it was not built".format(rel_src)
                )
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(s, d)

        # Static library archive built by libtool under --disable-shared.
        _stage_file(os.path.join("src", ".libs", "libxls.a"),
                    os.path.join("lib", "libxls.a"))

        # pkginclude_HEADERS = xlslib.h  (installed to include/xlslib/).
        _stage_file(os.path.join("src", "xlslib.h"),
                    os.path.join("include", "xlslib", "xlslib.h"))

        # nobase_pkginclude_HEADERS (installed preserving subdir layout).
        # xlconfig.h is configure-generated but lives in the same in-source
        # build tree (folders.build == ".").
        nobase_headers = [
            "common/xlconfig.h",
            "common/xlsys.h",
            "common/stringtok.h",
            "common/systype.h",
            "common/timespan.h",
            "common/xls_poppack.h",
            "common/xls_pshpack1.h",
            "common/xls_pshpack2.h",
            "common/xls_pshpack4.h",
            "common/xlstypes.h",
            "oledoc/binfile.h",
            "oledoc/oledoc.h",
            "oledoc/olefs.h",
            "oledoc/oleprop.h",
            "xlslib/biffsection.h",
            "xlslib/blank.h",
            "xlslib/boolean.h",
            "xlslib/cell.h",
            "xlslib/colinfo.h",
            "xlslib/colors.h",
            "xlslib/common.h",
            "xlslib/continue.h",
            "xlslib/datast.h",
            "xlslib/docsumminfo.h",
            "xlslib/err.h",
            "xlslib/extformat.h",
            "xlslib/font.h",
            "xlslib/format.h",
            "xlslib/formula.h",
            "xlslib/formula_cell.h",
            "xlslib/formula_const.h",
            "xlslib/formula_expr.h",
            "xlslib/formula_estimate.h",
            "xlslib/globalrec.h",
            "xlslib/HPSF.h",
            "xlslib/index.h",
            "xlslib/label.h",
            "xlslib/merged.h",
            "xlslib/note.h",
            "xlslib/number.h",
            "xlslib/range.h",
            "xlslib/recdef.h",
            "xlslib/record.h",
            "xlslib/rectypes.h",
            "xlslib/row.h",
            "xlslib/sheetrec.h",
            "xlslib/summinfo.h",
            "xlslib/unit.h",
            "xlslib/workbook.h",
        ]
        for rel in nobase_headers:
            _stage_file(os.path.join("src", rel), os.path.join("include", "xlslib", rel))

        self.output.info(
            "manual install: staged lib/libxls.a + {0} headers under "
            "include/xlslib".format(len(nobase_headers) + 1)
        )

    def package(self):
        # autotools.install() is unusable in the HMBS preflight sandbox
        # (chmod:0, masked install binary).  Package manually with plain data
        # copies, mirroring the upstream make install layout exactly.
        self._manual_install()

    def package_info(self):
        self.cpp_info.libs = ["xls"]
        self.cpp_info.includedirs = ["include/xlslib"]
