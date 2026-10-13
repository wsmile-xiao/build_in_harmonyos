#!/usr/bin/env python3
"""Conan recipe — srcpd 2.1.7 (Autotools, SRCP model-railroad daemon)

srcpd is the Simple Railroad Command Protocol (SRCP) server daemon: a
gateway between digital model-railroad hardware and SRCP client programs.
Upstream ships a classic Autotools tree (configure.ac + src/Makefile.am)
that builds a single sbin binary plus man pages. Hard build requirement
is libxml2 (AM_PATH_XML2); threading uses plain pthreads.

OHOS adaptation notes:
- The ddl-s88 device module needs <sys/io.h>/ioperm (x86 port I/O),
  unavailable on OHOS aarch64, so it is disabled via --disable-ddls88.
  All other modules keep their upstream defaults.
- config.sub is the 2022-01-03 release and rejects the linux-ohos
  triplet (OS `ohos' not recognized); patches/0001 teaches it ohos*
  (OS whitelist + kernel-OS validation, same two hunks as sarg/2.4.0).
  The canonical host aarch64-unknown-linux-ohos then matches
  configure's *-*-linux* branches, so the Linux header probes run;
  --disable-ddls88 keeps the only x86-only probe (sys/io.h) off.
- Upstream ships no test suite (no check target, no tests/ dir), so
  build() runs configure + make only; functional verification lives
  in test_package/test.sh.
- OHOS musl leaves the POSIX thread-cancellation family unimplemented
  (pthread_setcancelstate/setcanceltype/testcancel/cancel), so the final
  link fails with undefined symbols (same family as s3fs-fuse/1.94).
  generate()/build() force-include an inline rename-stub header in every
  TU (-include) plus explicit -pthread in CFLAGS/LDFLAGS; no Makefile or
  link-line surgery is needed.
- CC/CXX come from tools.build:compiler_executables after a
  file-exists + --version probe (healthy runners: used untouched);
  only a missing/mute pinned compiler falls back through PATH, and the
  fallback is written into the aggregated generator scripts because a
  toolchain-level define loses to conanbuild.sh sourcing. A configure
  failure dumps the config.log tail plus CC/CXX/CFLAGS/LDFLAGS context
  so the next round diagnoses from evidence.
"""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class SrcpdConan(ConanFile):
    name = "srcpd"
    version = "2.1.7"
    description = "SRCP server daemon: gateway between digital model railroad systems and SRCP clients"
    license = "GPL-2.0-or-later"
    homepage = "https://srcpd.sourceforge.net/"
    url = "https://sourceforge.net/projects/srcpd/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Use the ohpcd R37 adaptation revision 2.15.3.1 (bare-cmake recipe,
        # no conan cmake tool_requires) instead of plain 2.15.3: the plain
        # version is also published on ConanCenter, and with the preflight
        # remote order (conancenter first) it resolves to the CCI recipe,
        # whose cmake/<ver> tool_requires has no OHOS source entry and fails
        # its own build() with KeyError: 'OHOS'. CCI publishes no 2.15.3.1
        # (R37 suffix is ohpcd-only), so this ref resolves unambiguously to
        # the OHOS-adapted recipe (same precedent as sollya/8.0; cf. the
        # sail/0.9.10 RREV-pin fix for the same KeyError).
        self.requires("libxml2/2.15.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "srcpd is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-ohos",
            "--disable-ddls88",
        ])
        # E003:鸿蒙 clang needs explicit -pthread (compile+link effect).
        tc.extra_cflags.append("-pthread")
        tc.extra_ldflags.append("-pthread")
        compat = self._ensure_ohos_pthread_compat()
        if compat:
            tc.extra_cflags.append("-include%s" % compat)
            self.output.info("srcpd: OHOS pthread-cancel compat header: %s" % compat)
        tc.generate()
        # AM_PATH_XML2 probes libxml2 via xml2-config; export the dep
        # flags explicitly so configure finds them even when the helper
        # script path is not on PATH.
        xml = self.dependencies["libxml2"]
        cppflags = " ".join("-I" + p for p in xml.cpp_info.includedirs)
        libflags = " ".join("-L" + p for p in xml.cpp_info.libdirs)
        libs = " ".join("-l" + lib for lib in xml.cpp_info.libs)
        env = Environment()
        if cppflags:
            env.define("XML_CPPFLAGS", cppflags)
        combined = (libflags + " " + libs).strip()
        if combined:
            env.define("XML_LIBS", combined)
        # CI fix (PR #15384 build #88261): AM_PATH_XML2 ignores
        # XML_CPPFLAGS/XML_LIBS env and hard-requires an executable
        # xml2-config (AC_PATH_PROG -> "no matching library found" when
        # absent). The ohpcd libxml2/2.15.3.1 recipe is a CMake build and
        # installs no xml2-config, and CI workers carry no host one, so
        # provide a conan-path-backed shim and point XML2_CONFIG at it
        # (plus PATH prepend so AC_PATH_PROG also resolves it).
        xml2_config = self._ensure_xml2_config_shim()
        if xml2_config:
            env.define("XML2_CONFIG", xml2_config)
            env.prepend_path("PATH", os.path.dirname(xml2_config))
        env.vars(self).save_script("conanxml")

    def _ensure_xml2_config_shim(self):
        # Write a minimal xml2-config shim backed by the conan libxml2
        # package paths and return its absolute path ("" on failure).
        # AM_PATH_XML2 (see upstream acinclude.m4) overwrites
        # XML_CPPFLAGS/XML_LIBS from `$XML2_CONFIG --cflags/--libs` and
        # parses `$XML2_CONFIG --version`; env-only exports can never
        # satisfy it. Cross builds take the "assumed OK" branch, so the
        # shim only needs --cflags/--libs/--version (+ prefix passthrough).
        # Idempotent: rewritten on every generate()/build() call so stale
        # absolute paths from a previous cache never linger.
        try:
            xml = self.dependencies["libxml2"]
        except Exception as exc:
            self.output.warning("srcpd: no libxml2 dep for xml2-config shim: %s" % exc)
            return ""
        try:
            pkg = xml.package_folder or ""
        except Exception:
            pkg = ""
        if not pkg:
            self.output.warning("srcpd: libxml2 package_folder empty, skipping xml2-config shim")
            return ""
        try:
            incs = list(xml.cpp_info.includedirs or [])
        except Exception:
            incs = []
        try:
            libdirs = list(xml.cpp_info.libdirs or [])
        except Exception:
            libdirs = []
        try:
            libs = list(xml.cpp_info.libs or ["xml2"])
        except Exception:
            libs = ["xml2"]
        try:
            syslibs = list(xml.cpp_info.system_libs or [])
        except Exception:
            syslibs = []
        abs_incs = [p if os.path.isabs(p) else os.path.join(pkg, p) for p in incs]
        abs_libdirs = [p if os.path.isabs(p) else os.path.join(pkg, p) for p in libdirs]
        cflags = " ".join("-I" + p for p in abs_incs if p)
        libflags = " ".join("-L" + p for p in abs_libdirs if p)
        linklibs = " ".join("-l" + lib for lib in libs if lib)
        syss = " ".join("-l" + lib for lib in syslibs if lib)
        libline = (libflags + " " + linklibs + " " + syss).strip()
        try:
            dep_ver = str(xml.ref.version)
        except Exception:
            dep_ver = "2.15.3"
        parts = dep_ver.split(".")
        version = ".".join(parts[:3]) if len(parts) >= 3 else dep_ver
        try:
            folder = self.build_folder or ""
        except Exception:
            folder = ""
        if not folder:
            return ""
        shim_dir = os.path.join(folder, "hmbs-xml2-shim")
        shim = os.path.join(shim_dir, "xml2-config")
        script = (
            "#!/bin/sh\n"
            "# hmbs xml2-config shim (srcpd 2.1.7): backs AM_PATH_XML2 with\n"
            "# the conan libxml2 package paths. Cross builds only.\n"
            "XML2_CFLAGS=\"%s\"\n"
            "XML2_LIBS=\"%s\"\n"
            "XML2_VERSION=\"%s\"\n"
            "want_cflags=0\n"
            "want_libs=0\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    --cflags) want_cflags=1 ;;\n"
            "    --libs) want_libs=1 ;;\n"
            "    --version) echo \"$XML2_VERSION\"; exit 0 ;;\n"
            "    --prefix=*|--exec-prefix=*|--prefix|--exec-prefix|--help) ;;\n"
            "  esac\n"
            "done\n"
            "out=\"\"\n"
            "if [ \"$want_cflags\" = \"1\" ]; then out=\"$XML2_CFLAGS\"; fi\n"
            "if [ \"$want_libs\" = \"1\" ]; then\n"
            "  if [ -n \"$out\" ]; then out=\"$out $XML2_LIBS\";\n"
            "  else out=\"$XML2_LIBS\"; fi\n"
            "fi\n"
            "if [ -n \"$out\" ]; then echo \"$out\"; exit 0; fi\n"
            "echo \"$XML2_LIBS\"\n"
            "exit 0\n" % (cflags, libline, version)
        )
        try:
            os.makedirs(shim_dir, exist_ok=True)
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError as exc:
                self.output.warning(
                    "srcpd: xml2-config shim chmod failed (HMBS_CAP_CHMOD=0?): %s" % exc)
            self.output.info(
                "srcpd: xml2-config shim: %s (cflags=%s libs=%s version=%s)"
                % (shim, cflags[:200], libline[:200], version))
            return shim
        except OSError as exc:
            self.output.warning("srcpd: cannot write xml2-config shim: %s" % exc)
            return ""

    def _reroute_pinned_shell(self):
        # Profile [buildenv] pins CONFIG_SHELL/SHELL to
        # /data/service/hnp/bin/bash, and autoconf re-execs configure through
        # it (E386 family: sarg/2.4.0, scanmem/0.17, gtypist/2.10.1). On some
        # preflight runners that path is missing, so configure dies with
        # "configure[NNN]: /data/service/hnp/bin/bash: inaccessible or not
        # found" (Error 127) before any compiler check runs. Toolchain-level
        # Environment.define is overridden by the profile buildenv, so the
        # only reliable landing spot is a text replacement in the aggregated generator
        # env scripts (sarg precedent; no second save_script with the same
        # name — the aggregator self-sources and would recurse).
        # Healthy runners keep the stock path untouched (zero change).
        pinned = "/data/service/hnp/bin/bash"
        if os.path.exists(pinned):
            return
        shell_bin = "/bin/sh"
        for cand in ("/bin/sh", "/system/bin/sh"):
            if os.path.exists(cand):
                shell_bin = cand
                break
        self.output.info(
            "srcpd: pinned shell %s missing, routing CONFIG_SHELL/SHELL -> %s"
            % (pinned, shell_bin))
        for name in os.listdir(self.generators_folder):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(self.generators_folder, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            if pinned in text:
                replace_in_file(self, path, pinned, shell_bin)

    def _resolve_compilers(self):
        # tools.build:compiler_executables pins absolute CC/CXX paths in the
        # profile (idsgrep/0.6 precedent). Probe them first: a pinned path
        # that exists and answers --version is used untouched (healthy
        # runners: zero change). Only a missing/mute pinned compiler falls
        # back through PATH (clang family preferred, same-dir siblings
        # preferred); with no working compiler at all this raises an
        # explicit environment error for infra routing instead of letting
        # configure die with a bare "cannot create executables".
        # Only CC/CXX are covered; CFLAGS/LDFLAGS/... are never touched.
        # Returns (c_compiler, cpp_compiler).
        pinned = {}
        try:
            conf_val = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf_val, dict):
                pinned = conf_val
        except Exception as exc:
            self.output.info("srcpd: cannot read compiler_executables conf: %s" % exc)

        def _probe(exe):
            if not exe or not os.path.isfile(exe):
                self.output.info("srcpd: compiler probe %s -> missing" % exe)
                return False
            try:
                proc = subprocess.run([exe, "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,
                                      timeout=30)
            except Exception as exc:
                self.output.info("srcpd: compiler probe %s -> exec failed: %s" % (exe, exc))
                return False
            first = ""
            try:
                out_lines = (proc.stdout or b"").decode("utf-8", "ignore").splitlines()
                first = out_lines[0] if out_lines else ""
            except Exception:
                pass
            self.output.info("srcpd: compiler probe %s -> rc=%s %s"
                             % (exe, proc.returncode, first.strip()[:120]))
            return proc.returncode == 0

        c_pin = pinned.get("c", "") if isinstance(pinned, dict) else ""
        cxx_pin = pinned.get("cpp", "") if isinstance(pinned, dict) else ""
        if c_pin and cxx_pin and _probe(c_pin) and _probe(cxx_pin):
            return c_pin, cxx_pin
        self.output.warning("srcpd: pinned compiler unusable (c=%s cpp=%s), trying PATH fallback"
                            % (c_pin, cxx_pin))
        c_found = ""
        for cand in ("clang", "aarch64-linux-ohos-clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found:
                c_found = found
                break
        cxx_found = ""
        if c_found:
            sib = os.path.join(os.path.dirname(c_found), "clang++")
            if os.path.isfile(sib):
                cxx_found = sib
        if not cxx_found:
            for cand in ("clang++", "aarch64-linux-ohos-clang++", "c++", "g++"):
                found = shutil.which(cand)
                if found:
                    cxx_found = found
                    break
        if c_found and cxx_found and _probe(c_found) and _probe(cxx_found):
            self.output.warning("srcpd: compiler fallback -> CC=%s CXX=%s" % (c_found, cxx_found))
            return c_found, cxx_found
        raise ConanInvalidConfiguration(
            "srcpd: no working C/C++ compiler (pinned c=%s cpp=%s, PATH fallback c=%s cpp=%s); "
            "environment fault, not a recipe bug" % (c_pin, cxx_pin, c_found, cxx_found))

    def _reroute_missing_compilers(self, c_compiler, cpp_compiler):
        # The AutotoolsToolchain bakes tools.build:compiler_executables into
        # the aggregated conanbuild.sh (export CC=.../CXX=...), which the
        # configure subshell sources: a toolchain-level Environment.define in
        # the Python process loses to it (proven this round: the fallback
        # resolved harmonybrew clang, yet configure still probed the missing
        # /data/service/hnp/bin/clang). So the fallback must be written into
        # the aggregated generator scripts — the same landing spot as the
        # shell reroute (sarg precedent). Pins that exist on disk are never
        # touched (healthy runners: zero change). The clang++ pair goes
        # first; matches are full absolute pinned paths, so the two passes
        # cannot corrupt each other's resolved paths.
        try:
            conf_val = self.conf.get("tools.build:compiler_executables")
        except Exception:
            conf_val = None
        if not isinstance(conf_val, dict):
            return
        pairs = [(conf_val.get("cpp", ""), cpp_compiler),
                 (conf_val.get("c", ""), c_compiler)]
        targets = []
        for pinned, resolved in pairs:
            if not pinned or not resolved or pinned == resolved:
                continue
            if os.path.exists(pinned):
                continue
            targets.append((pinned, resolved))
        if not targets:
            return
        self.output.warning("srcpd: rerouting missing pinned compiler(s) in generator scripts: %s"
                            % (", ".join("%s -> %s" % t for t in targets),))
        for name in os.listdir(self.generators_folder):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(self.generators_folder, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for pinned, resolved in targets:
                if pinned in text:
                    replace_in_file(self, path, pinned, resolved)

    def _dump_config_log(self):
        # configure failed with Error 77: the real cc/ld error hides inside
        # config.log, so dump its tail plus the compiler/flag context for
        # the next round's diagnosis (evidence over guessing).
        cands = []
        try:
            if self.build_folder:
                cands.append(os.path.join(self.build_folder, "config.log"))
        except Exception:
            pass
        try:
            src = getattr(self, "source_folder", "") or ""
            if src:
                cands.append(os.path.join(src, "config.log"))
        except Exception:
            pass
        path = next((p for p in cands if p and os.path.isfile(p)), "")
        if not path:
            self.output.warning("srcpd: configure failed but no config.log found (looked in %s)"
                                % (cands,))
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError as exc:
            self.output.warning("srcpd: cannot read %s: %s" % (path, exc))
            return
        self.output.warning("srcpd: ---- config.log tail (%s, %d lines) ----" % (path, len(lines)))
        for line in lines[-80:]:
            self.output.warning("srcpd config.log: %s" % line[:400])
        for var in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS"):
            self.output.warning("srcpd env: %s=%s" % (var, str(os.environ.get(var, "<unset>"))[:400]))

    @staticmethod
    def _ohos_pthread_compat_header_text():
        return (
            "/* ohos_pthread_compat.h - OHOS musl pthread-cancellation stubs"
            " (srcpd 2.1.7). */\n"
            "/* OHOS musl provides create/join/mutex/cond but leaves the POSIX\n"
            " * cancellation family unimplemented, so the final link fails with\n"
            " * \"undefined symbol: pthread_setcancelstate/setcanceltype/\n"
            " * testcancel/cancel\" (clientservice.c:thr_doClient, netservice.c,\n"
            " * config-srcpd.c:cancel_all_bus_threads/run_bus_watchdog).\n"
            " * Same family as s3fs-fuse/1.94 (musl pthread_cancel stub fix).\n"
            " *\n"
            " * Force-included in every TU (-include); the four calls are\n"
            " * renamed to static no-op implementations. Renaming (instead of\n"
            " * same-named statics) avoids \"static follows non-static\"\n"
            " * conflicts with <pthread.h> declarations and needs no Makefile\n"
            " * or link-line surgery. Threads run with cancellation disabled;\n"
            " * cancel requests report success without terminating the target.\n"
            " */\n"
            "#ifndef SRCPD_OHOS_PTHREAD_CANCEL_COMPAT_H\n"
            "#define SRCPD_OHOS_PTHREAD_CANCEL_COMPAT_H\n"
            "#include <pthread.h>\n"
            "static int ohos_srcpd_setcancelstate(int state, int *oldstate) {\n"
            "    (void) state;\n"
            "    if (oldstate != 0) { *oldstate = PTHREAD_CANCEL_ENABLE; }\n"
            "    return 0;\n"
            "}\n"
            "static int ohos_srcpd_setcanceltype(int type, int *oldtype) {\n"
            "    (void) type;\n"
            "    if (oldtype != 0) { *oldtype = PTHREAD_CANCEL_DEFERRED; }\n"
            "    return 0;\n"
            "}\n"
            "static void ohos_srcpd_testcancel(void) { }\n"
            "static int ohos_srcpd_cancel(pthread_t thread)"
            " { (void) thread; return 0; }\n"
            "#define pthread_setcancelstate ohos_srcpd_setcancelstate\n"
            "#define pthread_setcanceltype ohos_srcpd_setcanceltype\n"
            "#define pthread_testcancel ohos_srcpd_testcancel\n"
            "#define pthread_cancel ohos_srcpd_cancel\n"
            "#endif\n"
        )

    def _ensure_ohos_pthread_compat(self):
        # Write the cancellation-stub header into the build folder and return
        # its absolute path ("" on failure). Deterministic location: no guess
        # about where exports_sources lands, and valid for both the toolchain
        # CFLAGS (-include) and the build() Environment append below.
        try:
            folder = self.build_folder or ""
        except Exception:
            folder = ""
        if not folder:
            return ""
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            pass
        path = os.path.join(folder, "ohos_pthread_compat.h")
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(self._ohos_pthread_compat_header_text())
            return path
        except OSError as exc:
            self.output.warning("srcpd: cannot write pthread compat header: %s" % exc)
            return ""

    @staticmethod
    def _is_writable_dir(path):
        try:
            if not path or not os.path.isdir(path):
                return False
            probe = os.path.join(path, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            try:
                os.remove(probe)
            except OSError:
                pass
            return True
        except OSError:
            return False

    def _writable_tmpdir(self):
        # HMBS readonly_tmp: /tmp is erofs read-only on the device.
        # Reuse the hmbs-injected task-private TMPDIR/TMP/TEMP chain
        # verbatim after a real write probe (isdir alone cannot prove a
        # read-only mount writable). HMBS_AUTOCONF_MKTEMP_FALLBACK may
        # itself carry a directory path on some runners (aldo precedent),
        # honour it as a candidate too. Fallback is build-local.
        # Only the temp-file root is redirected; no test is skipped.
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = (os.environ.get(key) or "").strip()
            if cand and self._is_writable_dir(cand):
                return cand
        for key in ("HMBS_TMPDIR", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            cand = (os.environ.get(key) or "").strip()
            if cand and cand not in ("0", "1") and self._is_writable_dir(cand):
                return cand
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _mktemp_fallback_shim(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory created
        # by mktemp on the current device filesystem cannot be written by
        # Autoconf afterwards (./conf*/subs1.awk: Permission denied ->
        # could not setup config files machinery). When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during configure
        # only so calls for "./conf*" fail and Autoconf falls back to its
        # `mkdir` path. All other mktemp calls delegate to the real binary.
        # Precedent: cyrus-sasl/serf/swbis. Best-effort under
        # HMBS_CAP_CHMOD=0 (chmod may fail -> shim not executable); the
        # umask patch below is the primary fix and works regardless.
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/system/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError as exc:
                self.output.warning(
                    "srcpd: mktemp shim chmod failed (HMBS_CAP_CHMOD=0?): %s" % exc)
        except OSError:
            return ""
        return shim_dir

    def _patch_configure_umask(self):
        # HMFS + toybox mktemp: `umask 077 && mktemp -d ./confXXXXXX`
        # yields an owner-unwritable dir (drwx--S---) so config.status
        # cannot create subs1.awk afterwards. Relax 077 -> 022 in the
        # configure本体 (which also templates config.status). Covers the
        # `umash` misspelling too. Only permission bits change; mktemp
        # itself is kept. Precedent: buildtorrent/0.9.1 (chmod=0 runners
        # where the mktemp shim alone cannot execute), swbis/1.13.3.
        roots = []
        for attr in ("source_folder", "build_folder"):
            try:
                val = getattr(self, attr, "") or ""
            except Exception:
                val = ""
            if val and os.path.isdir(val) and val not in roots:
                roots.append(val)
        patched = 0
        for root in roots:
            for dirpath, _, files in os.walk(root):
                if "configure" not in files:
                    continue
                cfg = os.path.join(dirpath, "configure")
                try:
                    with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except OSError:
                    continue
                orig = content
                content, n_mktemp = re.subn(
                    r"um(?:ask|ash) 077 && mktemp -d",
                    "umask 022 && mktemp -d", content)
                content, n_mkdir = re.subn(
                    r"um(?:ask|ash) 077 && mkdir",
                    "umask 022 && mkdir", content)
                if n_mktemp == 0 and n_mkdir == 0 and "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                    n_mktemp = 1
                if content != orig:
                    try:
                        with open(cfg, "w", encoding="utf-8", newline="\n") as fh:
                            fh.write(content)
                    except OSError:
                        continue
                    patched += 1
                    self.output.info(
                        "[ok] relaxed umask 077 -> 022 in %s (mktemp:%d mkdir:%d)"
                        % (cfg, n_mktemp, n_mkdir))
        if patched == 0:
            self.output.info("srcpd: no umask 077 pattern found in configure")

    def build(self):
        apply_conandata_patches(self)
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            os.umask(0o022)
        except OSError:
            pass
        self._patch_configure_umask()
        self._reroute_pinned_shell()
        c_compiler, cpp_compiler = self._resolve_compilers()
        self._reroute_missing_compilers(c_compiler, cpp_compiler)
        mktemp_shim = self._mktemp_fallback_shim(tmpdir)
        if mktemp_shim:
            cur = os.environ.get("PATH", "")
            if mktemp_shim not in cur.split(os.pathsep):
                os.environ["PATH"] = mktemp_shim + os.pathsep + cur
            self.output.info("srcpd: configure mktemp shim: %s" % mktemp_shim)
        self.output.info("srcpd: writable tmpdir: %s" % tmpdir)
        compat = self._ensure_ohos_pthread_compat()
        if compat:
            self.output.info("srcpd: pthread-cancel compat (build): %s" % compat)
        autotools = Autotools(self)
        env = Environment()
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("CC", c_compiler)
        env.define("CXX", cpp_compiler)
        # Re-ensure the xml2-config shim at build time (same build_folder
        # as generate(); refreshes absolute conan paths) and export it so
        # the configure subshell resolves AM_PATH_XML2 via conan libxml2
        # even on workers with no host xml2-config (CI #88261).
        xml2_config = self._ensure_xml2_config_shim()
        if xml2_config:
            env.define("XML2_CONFIG", xml2_config)
            env.prepend_path("PATH", os.path.dirname(xml2_config))
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # Belt-and-suspenders with the toolchain-level -pthread/-include above:
        # the aggregated conanbuild.sh already carries them, but an explicit
        # append here guarantees configure conftests and the final link see
        # them even if a profile buildenv layer overrides CFLAGS/LDFLAGS.
        env.append("CFLAGS", "-pthread")
        env.append("LDFLAGS", "-pthread")
        if compat:
            env.append("CFLAGS", "-include%s" % compat)
        if mktemp_shim:
            env.prepend_path("PATH", mktemp_shim)
        with env.vars(self).apply():
            try:
                autotools.configure()
            except Exception:
                self._dump_config_log()
                raise
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
