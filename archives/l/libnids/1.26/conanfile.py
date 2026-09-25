#!/usr/bin/env python3
"""Conan recipe — libnids 1.26 (Autotools: configure + make).

Network intrusion detection E-component: IP defragmentation,
TCP stream reassembly and port scan detection over libpcap.

OHOS base adaptation (path A):
  - requires libpcap only; --disable-libnet --disable-libglib
  - E007 config.guess bypass via --build/--host triplet
  - HMDFS: umask 022 rewrite, writable TMPDIR, make -j1
  - Upstream ships no automated test suite (no_tests).

R32: settings.os checked in ("Linux", "OHOS").
R33: no bare shell env vars; compiler from Conan conf.
R34: consumer test calls real nids API (see test_package/).
"""

import os
import shutil
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnidsConan(ConanFile):
    name = "libnids"
    version = "1.26"
    description = "Network intrusion detection system E-component library"
    license = "GPL-2.0-only"
    homepage = "https://github.com/MITRECND/libnids"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnids is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps feeds libpcap -I/-L/-l into the configure/make
        # environment (cursynth 1.5 precedent on the same true machine).
        # NOTE: libnids src/Makefile.in ignores CPPFLAGS and only uses
        # $(CFLAGS) + $(LIBS_CFLAGS) with LIBS_CFLAGS=$(PCAP_CFLAGS).
        # configure's fallback probe leaves PCAP_CFLAGS empty when the
        # header is only visible via AutotoolsDeps CPPFLAGS, so bridge
        # the dependency include dir into CFLAGS as well (configure
        # conftest uses CPPFLAGS and passes, but `make static` then
        # fails with 'pcap.h file not found').
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.extra_cflags.append("-D_DEFAULT_SOURCE")
        try:
            pcap_inc = os.path.join(
                self.dependencies["libpcap"].package_folder,
                "include",
            ).replace("\\", "/")
            tc.extra_cflags.append("-I%s" % pcap_inc)
            self.output.info("libnids: bridged libpcap include: %s"
                             % pcap_inc)
        except Exception as exc:
            self.output.warning("libnids: cannot bridge pcap include: %s"
                                % exc)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        # DRAFT-6487 global fallback (myman 4.0.116 precedent): the
        # ohos-aarch64 profile buildenv exports
        # CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, which is
        # inaccessible on HMDFS (getcwd fails). Force the HMBS-injected
        # /bin/sh for every child process spawned below.
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        gen = self.generators_folder or self.build_folder
        # Round-5 new fingerprint (config.log): configure's `$CC --version`
        # equivalent fails with
        #   "/data/service/hnp/bin/clang: inaccessible or not found"
        # i.e. the toolchain-declared absolute CC is not executable from
        # /bin/sh in this preflight worker. Previous rounds only fixed
        # SHELL (now proven good: HMBS_DIAG_SHELL=/bin/sh, target type
        # parsed), so a different route is required here: probe the
        # configured compiler for real executability and pin a working one
        # (libnewt/0.52.25 precedent). The --build/--host triplet is kept
        # unconditionally regardless of which CC wins.
        chosen_cc = self._probe_working_cc()
        if chosen_cc:
            os.environ["CC"] = chosen_cc
            self._pin_cc_into_toolchain_script(gen, chosen_cc)
        # libnids quirk (see generate()): PCAP_CFLAGS drives
        # LIBS_CFLAGS in src/Makefile.in. Export it explicitly so the
        # manual `sh configure` substitution and the later
        # Autotools.make() both see a non-empty value even when
        # configure's fallback branch leaves it empty.
        try:
            pcap_inc = os.path.join(
                self.dependencies["libpcap"].package_folder,
                "include",
            ).replace("\\", "/")
            pcap_cflags = "-I%s" % pcap_inc
            os.environ["PCAP_CFLAGS"] = pcap_cflags
            self.output.info("libnids: PCAP_CFLAGS=%s"
                             % os.environ["PCAP_CFLAGS"])
        except Exception as exc:
            pcap_inc = ""
            pcap_cflags = ""
            self.output.warning("libnids: cannot set PCAP_CFLAGS: %s"
                                % exc)
        source_folder = self.source_folder
        tmpdir = self._writable_tmpdir()
        self._fix_autoconf_umask_for_ohos(source_folder)
        self._patch_config_sub_for_aarch64(source_folder)
        mktemp_shim = self._mktemp_fallback_shim_for_ohos(tmpdir)
        configure = os.path.join(source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure
            )
        configure_args = " ".join(
            shlex.quote(arg) for arg in self._configure_args()
        )
        # Always interpret configure with /bin/sh (HMBS-injected). Never
        # trust CONFIG_SHELL here
        path_prefix = ("%s:" % mktemp_shim) if mktemp_shim else ""
        tc_sh = os.path.join(gen, "conanautotoolchain.sh").replace("\\", "/")
        deps_sh = os.path.join(gen, "conanautotoolsdeps.sh").replace("\\", "/")
        # Manual `sh configure` (kept for the umask/TMPDIR handling) must
        # source the toolchain scripts explicitly. NOTE: `VAR=val cmd;`
        # prefixes do NOT persist past the single `[ -f ...]` command, and
        # conanautotoolchain.sh re-exports the profile's bad
        # SHELL=/data/service/hnp/bin/bash, which configure then uses as
        # `$SHELL config.sub` -> "cannot run .../bash .../config.sub".
        # Hence `export` first, source, then re-export /bin/sh AFTER
        # sourcing (myman 4.0.116 DRAFT-6487 pattern). The [ -f ] guards
        # keep this a no-op if a future Conan renames the scripts.
        command = (
            "export TMPDIR=\"%s\"; export TMP=\"%s\"; export TEMP=\"%s\"; "
            "export PATH=\"%s$PATH\"; umask 022; "
            "[ -f \"%s\" ] && . \"%s\"; "
            "[ -f \"%s\" ] && . \"%s\"; "
            "export CONFIG_SHELL=\"/bin/sh\"; export SHELL=\"/bin/sh\"; "
            "export PCAP_CFLAGS=\"%s\"; "
            "echo \"HMBS_DIAG_CC=$CC\"; "
            "echo \"HMBS_DIAG_CFLAGS=$CFLAGS\"; "
            "echo \"HMBS_DIAG_CPPFLAGS=$CPPFLAGS\"; "
            "echo \"HMBS_DIAG_PCAP_CFLAGS=$PCAP_CFLAGS\"; "
            "echo \"HMBS_DIAG_LDFLAGS=$LDFLAGS\"; "
            "echo \"HMBS_DIAG_LIBS=$LIBS\"; "
            "echo \"HMBS_DIAG_SHELL=$SHELL\"; "
            "/bin/sh \"%s\" %s"
            % (tmpdir, tmpdir, tmpdir,
               path_prefix, tc_sh, tc_sh, deps_sh, deps_sh,
               pcap_cflags, configure, configure_args)
        )
        try:
            self.run(command, cwd=self.build_folder, env="conanbuild")
        except Exception:
            self._dump_config_log_tail()
            raise
        autotools = Autotools(self)
        # R9: single job - parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

    def _probe_working_cc(self):
        # libnewt/0.52.25 precedent: really exec `$cc --version` on the
        # target worker; keep the first candidate that exits 0, else ""
        # (caller then keeps the toolchain default and configure reports).
        candidates = []
        try:
            comp = self.conf.get("tools.build:compiler_executables")
            if isinstance(comp, dict) and comp.get("c"):
                candidates.append(comp["c"])
            elif isinstance(comp, str) and comp:
                candidates.append(comp)
        except Exception:
            pass
        env_cc = os.environ.get("CC")
        if env_cc:
            candidates.append(env_cc)
        candidates.append("/data/service/hnp/bin/clang")
        for tool in ("clang", "cc", "gcc",
                     "aarch64-unknown-linux-gnu-gcc",
                     "aarch64-linux-gnu-gcc"):
            try:
                found = shutil.which(tool)
            except Exception:
                found = None
            if found:
                candidates.append(found)
        seen = set()
        ordered = []
        for cand in candidates:
            if not cand or not isinstance(cand, str):
                continue
            exe = cand.split()[0]
            if not exe or exe in seen:
                continue
            seen.add(exe)
            ordered.append(cand)
        for cand in ordered:
            exe = cand.split()[0]
            if "/" in exe and not os.path.isfile(exe):
                self.output.info("CC probe: not a file, skip: %s" % cand)
                continue
            try:
                result = subprocess.run(
                    [exe, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception as exc:
                self.output.info("CC probe: exec failed %s (%s)"
                                 % (cand, exc))
                continue
            if result.returncode == 0:
                self.output.info("CC probe: usable: %s" % cand)
                return cand
            self.output.info("CC probe: %s --version rc=%s"
                             % (cand, result.returncode))
        self.output.warning(
            "CC probe: no working compiler, keeping toolchain default")
        return ""

    def _pin_cc_into_toolchain_script(self, gen, chosen):
        # The manual configure invocation sources conanautotoolchain.sh
        # from disk, so appending the probed CC there overrides the stale
        # absolute path for both the manual invocation and Autotools.make.
        script = os.path.join(gen, "conanautotoolchain.sh")
        try:
            with open(script, "a", encoding="utf-8") as handle:
                handle.write('\nexport CC="%s"\n'
                             % chosen.replace('"', ''))
            self.output.info("CC probe: pinned into conanautotoolchain.sh: %s"
                             % chosen)
        except OSError as exc:
            self.output.warning("CC probe: cannot pin toolchain script: %s"
                                % exc)

    def package(self):
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        tmpdir = self._writable_tmpdir()
        # Out-of-source quirk: src/Makefile calls `../mkinstalldirs`,
        # i.e. <build>/mkinstalldirs, but configure never copies this
        # auxiliary script to the build tree. Stage it from the source
        # tree (build-time copy only, no tarball change) so
        # `make install` works with basic_layout.
        try:
            src_mk = os.path.join(self.source_folder, "mkinstalldirs")
            dst_mk = os.path.join(self.build_folder, "mkinstalldirs")
            if os.path.isfile(src_mk) and not os.path.isfile(dst_mk):
                shutil.copy2(src_mk, dst_mk)
                self.output.info("staged mkinstalldirs for out-of-source install")
            try:
                os.chmod(dst_mk, 0o755)
            except OSError:
                pass
        except OSError as exc:
            self.output.warning("cannot stage mkinstalldirs: %s" % exc)
        try:
            self.run(
                "export TMPDIR=\"%s\"; export TMP=\"%s\"; export TEMP=\"%s\"; "
                "export CONFIG_SHELL=\"/bin/sh\"; export SHELL=\"/bin/sh\"; umask 022; "
                "make install install_prefix=\"%s\" -j1"
                % (tmpdir, tmpdir, tmpdir, self.package_folder),
                cwd=self.build_folder,
                env="conanbuild",
            )
        except Exception:
            # Fallback (libnet/1.2 OHOS precedent): hand-install the
            # three artefacts so a fragile install-sh/mkinstalldirs on
            # HMDFS cannot fail the whole package.
            self.output.warning("make install failed, manual fallback")
            self._manual_install_fallback()
        self._fix_missing_so_symlink_for_ohos()
        if not self.options.shared:
            self._purge_shared_artefacts()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def _manual_install_fallback(self):
        # Minimal hand-install mirroring src/Makefile _install target:
        # libnids.a -> <pkg>/lib, nids.h -> <pkg>/include,
        # libnids.3 -> <pkg>/share/man/man3. Build tree holds the .a,
        # source tree holds the headers/man.
        built_a = os.path.join(self.build_folder, "src", "libnids.a")
        if not os.path.isfile(built_a):
            built_a = os.path.join(self.source_folder, "src", "libnids.a")
        for directory in (
            os.path.join(self.package_folder, "lib"),
            os.path.join(self.package_folder, "include"),
            os.path.join(self.package_folder, "share", "man", "man3"),
        ):
            os.makedirs(directory, exist_ok=True)
        if os.path.isfile(built_a):
            shutil.copy2(
                built_a,
                os.path.join(self.package_folder, "lib", "libnids.a"),
            )
            self.output.info("manual fallback: installed libnids.a")
        for src_dir in (os.path.join(self.build_folder, "src"),
                        os.path.join(self.source_folder, "src")):
            header = os.path.join(src_dir, "nids.h")
            if os.path.isfile(header):
                shutil.copy2(
                    header,
                    os.path.join(self.package_folder, "include", "nids.h"),
                )
                self.output.info("manual fallback: installed nids.h")
                break
        for src_dir in (os.path.join(self.build_folder, "src"),
                        os.path.join(self.source_folder, "src")):
            man = os.path.join(src_dir, "libnids.3")
            if os.path.isfile(man):
                shutil.copy2(
                    man,
                    os.path.join(
                        self.package_folder, "share", "man", "man3",
                        "libnids.3",
                    ),
                )
                break

    def package_info(self):
        self.cpp_info.libs = ["nids"]
        self.cpp_info.requires = ["libpcap::libpcap"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libnids")
        self.cpp_info.set_property(
            "cmake_target_name", "libnids::libnids")
        self.cpp_info.set_property("pkg_config_name", "libnids")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _configure_args(self):
        args = [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-libnet",
            "--disable-libglib",
        ]
        if self.options.shared:
            args.append("--enable-shared")
        return args

    def _writable_tmpdir(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                return candidate
        tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _fix_autoconf_umask_for_ohos(self, source_folder):
        configure = os.path.join(source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)

    def _patch_config_sub_for_aarch64(self, source_folder):
        # libnids 1.26 ships config.sub timestamp 2000-12-15, which predates
        # aarch64 (first support ~2012). With --build/--host=
        # aarch64-unknown-linux-gnu it aborts:
        #   "Invalid configuration `aarch64-unknown-linux-gnu':
        #    machine `aarch64-unknown' not recognized".
        # Teach the two CPU case lists about aarch64 at build time (no
        # tarball/patch change, no new tool_requires; pure-Python so it
        # works on CI and HMBS preflight alike). config.guess needs no
        # change: explicit --build/--host already bypasses it.
        config_sub = os.path.join(source_folder, "config.sub")
        try:
            with open(config_sub, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "aarch64" in content:
            return
        bare = "| thumb | d10v | d30v | fr30 | avr)"
        if bare in content:
            content = content.replace(
                bare, "| thumb | d10v | d30v | fr30 | avr | aarch64 | aarch64be)",
                1,
            )
        company = "| bs2000-* | tic54x-* | c54x-* | x86_64-*)"
        if company in content:
            content = content.replace(
                company,
                "| bs2000-* | tic54x-* | c54x-* | x86_64-* | aarch64-* | aarch64be-*)",
                1,
            )
        else:
            return
        with open(config_sub, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info("patched config.sub for aarch64 (2000-vintage)")

    def _dump_config_log_tail(self, max_lines=30):
        # configure prints only "See `config.log' for more details" while the
        # real linker error stays in the build folder. Extract just the
        # failing conftest link invocation plus compiler/linker error lines
        # (compact on purpose: full tails get truncated by the messenger).
        for folder in (self.build_folder, self.source_folder):
            log_path = os.path.join(folder, "config.log")
            try:
                with open(log_path, "r", encoding="utf-8",
                           errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError:
                continue
            start = None
            for i, line in enumerate(lines):
                if "$CC" in line and "conftest" in line:
                    start = i
            excerpt = []
            if start is not None:
                excerpt.extend(lines[start:start + 10])
            keywords = ("error", "cannot find", "undefined", "no such",
                        "not found", "failed")
            hits = [line for line in lines
                    if any(key in line.lower() for key in keywords)]
            excerpt.append("--- error-like lines (last 8) ---")
            excerpt.extend(hits[-8:])
            excerpt = [line[:300] for line in excerpt][:max_lines]
            self.output.info("config.log excerpt (%s):\n%s"
                             % (log_path, "\n".join(excerpt)))
            return
        self.output.warning("config.log not found in build/source folders")

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
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
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _fix_missing_so_symlink_for_ohos(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        real = os.path.join(libdir, "libnids.so.1.26")
        link = os.path.join(libdir, "libnids.so")
        if os.path.isfile(real) and not os.path.lexists(link):
            try:
                os.symlink("libnids.so.1.26", link)
                self.output.info("created missing symlink: %s" % link)
            except OSError as exc:
                try:
                    shutil.copy2(real, link)
                    self.output.info(
                        "symlink unsupported, copied instead: %s" % exc)
                except OSError as exc2:
                    self.output.warning(
                        "cannot provide libnids.so: %s" % exc2)

    def _purge_shared_artefacts(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _dirs, files in os.walk(libdir):
            for name in files:
                if name.endswith(".so") or ".so." in name \
                        or name.endswith(".la"):
                    stale = os.path.join(root, name)
                    try:
                        os.remove(stale)
                        self.output.info(
                            "removed stale shared artefact: %s" % stale)
                    except OSError as exc:
                        self.output.warning(
                            "cannot remove %s: %s" % (stale, exc))
