#!/usr/bin/env python3
"""Conan recipe — libofa 0.9.3 (Autotools)."""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _config_shell():
    """Pick an executable shell for configure re-exec.

    HMBS preflight injects SHELL=/bin/sh (capability-tested) while the
    ohos-aarch64 profile exports /data/service/hnp/bin/bash; on the
    preflight host that hnp path is reported as "inaccessible or not
    found", so probing with an executability check (nasm 2.16.03 pattern)
    is required instead of hardcoding either path.
    """
    for candidate in (
        os.environ.get("SHELL"),
        os.environ.get("CONFIG_SHELL"),
        "/bin/sh",
        "/data/service/hnp/bin/bash",
        shutil.which("bash"),
        shutil.which("sh"),
    ):
        if not candidate:
            continue
        if os.path.isabs(candidate):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        elif shutil.which(candidate):
            return candidate
    return "sh"


def _probe_writable_dir(candidate):
    """True if a directory can be created and really written to.

    Uses makedirs + open(write) + unlink. Never uses os.access(X_OK) or
    chmod probes: HMDFS ignores chmod and X_OK is always False (E046/R49).
    """
    try:
        os.makedirs(candidate, exist_ok=True)
        probe = os.path.join(candidate, ".tmp-write-probe")
        with open(probe, "w") as handle:
            handle.write("ok")
        os.unlink(probe)
        return True
    except OSError:
        return False


class LibofaConan(ConanFile):
    name = "libofa"
    version = "0.9.3"
    description = ("Library Open Fingerprint Architecture: generates acoustic "
                   "fingerprints for music identification via the MusicDNS service")
    license = "GPL-2.0-only"
    homepage = "https://code.google.com/archive/p/musicip-libofa/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libofa is adapted for Linux/OHOS only")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Declared by configure.in: expat (XML), curl (MusicDNS HTTP), fftw3 (FFT).
        self.requires("expat/2.8.2.1")
        self.requires("curl/8.15.0")
        self.requires("fftw/3.3.10.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """Pick a TMPDIR that is really writable, with build-local fallback.

        clang spills compiler temp files into TMPDIR; an unwritable or
        missing TMPDIR makes the first configure compiler test fail with
        "C compiler cannot create executables" (Error 77) while the real
        "unable to make temporary file" error stays hidden in config.log
        (coinor-vol 1.5.4, same signature). Candidate order: the HMBS
        injected task TMPDIR/TMP/TEMP first, then $HOME/tmp (E002), then
        build_folder/.tmp (conan always materializes sources there, so it
        is writable on every worker). Probing is a real write, never
        os.access/chmod (E046/R49).
        """
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and value not in candidates:
                candidates.append(value)
        home = os.environ.get("HOME")
        if home:
            candidates.append(os.path.join(home, "tmp"))
        candidates.append(os.path.join(self.build_folder, ".tmp"))
        for candidate in candidates:
            if _probe_writable_dir(candidate):
                return candidate
        fallback = os.path.join(self.build_folder, ".tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # OHOS cross declaration: pass ONLY --host, never --build. Autoconf sets
        # cross_compiling=yes only when host != build; passing
        # --build=<same ohos triplet> forces build==host, i.e. a "native"
        # build, so configure tries to RUN the conftest a.out and dies with
        # "cannot run C compiled programs ... use --host" (two rounds running:
        # vendor-less form died in config.sub, vendor-qualified form died here).
        # Omitting --build lets configure guess it via config.guess: the build
        # worker is a Linux container carrying a harmonybrew cross clang
        # (/data/service/hnp/bin/clang absent, clang 15 LLVM cross toolchain),
        # so the guess differs from the ohos host and cross mode is entered.
        # aarch64-unknown-linux-ohos is the form this tree supports: the 0002
        # config.sub early-exit only matches vendor-qualified triplets
        # (aarch64-*-linux-ohos), and the 0001 config.guess emits exactly it.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Put the probed shell into the toolchain environment itself so it
        # cannot be overridden by the profile buildenv ordering (a separate
        # save_script("libofa_shell") lost to the profile's SHELL on the
        # preflight host, leaving configure re-exec on the inaccessible
        # /data/service/hnp/bin/bash).
        shell = _config_shell()
        env = tc.environment()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        # Pin a probed-writable TMPDIR into the toolchain environment so it
        # survives inside the conanbuild scope (host TMPDIR alone is not
        # reliably visible there); without this clang's temp files fall back
        # to read-only /tmp and the compiler sanity check fails (Error 77).
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)
        # Expose the declared requires (expat/curl/fftw) to configure's
        # AC_CHECK_LIB probes: on a clean OHOS device there are no system
        # copies, so without these generators the post-sanity lib checks
        # would fail next. Same pair as the exult autotools recipe.
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _probe_compiler(self):
        """Verify the C compiler by really compiling+linking (exp1 adapted).

        configure's own compiler probe failed two rounds running while the
        binary visibly exists, so verify the exact compile+link step outside
        configure: candidates come from this profile's
        tools.build:compiler_executables plus PATH lookup (this
        environment only — no foreign paths). Returns the verified CC path
        or None. Never aborts the build; failures only print the real
        compiler stderr into the preflight log as ground truth.
        """
        candidates = []
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}) or {}
        except Exception:
            executables = {}
        if isinstance(executables, dict):
            for key in ("c", "cpp"):
                value = executables.get(key)
                if value and value not in candidates:
                    candidates.append(str(value))
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        tmpdir = self._writable_tmpdir()
        src = os.path.join(tmpdir, "hmbs-cc-probe.c")
        try:
            with open(src, "w") as handle:
                handle.write("int main(void){return 0;}\n")
        except OSError as error:
            self.output.info("compiler probe: cannot write probe source (%s)"
                             % error)
            return None
        for cc in candidates:
            exe = os.path.join(tmpdir, "hmbs-cc-probe")
            try:
                if os.path.isfile(exe):
                    os.unlink(exe)
            except OSError:
                pass
            try:
                proc = subprocess.run(
                    [cc, src, "-o", exe], capture_output=True, text=True,
                    timeout=180)
            except Exception as error:
                self.output.info("compiler probe: %s not launchable (%s)"
                                 % (cc, error))
                continue
            if proc.returncode == 0 and os.path.isfile(exe):
                try:
                    ver = subprocess.run(
                        [cc, "--version"], capture_output=True, text=True,
                        timeout=60).stdout.splitlines()
                except Exception:
                    ver = []
                self.output.info("compiler probe: %s OK%s"
                                 % (cc, (" (%s)" % ver[0][:100]) if ver else ""))
                return cc
            self.output.info("compiler probe: %s FAILED rc=%d"
                             % (cc, proc.returncode))
            for line in ((proc.stderr or "").splitlines()[:20]):
                self.output.info("compiler probe stderr | %s" % line[:300])
        self.output.info("compiler probe: no candidate compiled; "
                         "continuing to configure for config.log evidence")
        return None

    def _probe_cxx(self, verified_cc=None):
        """Verify the C++ compiler by really compiling+linking.

        New failure domain after the triplet rounds: the C probe pins CC
        to the working harmonybrew clang, but CXX is still the profile's
        /data/service/hnp/bin/clang++ (not launchable on the preflight
        host), so configure dies at `C++ preprocessor "/lib/cpp" fails
        sanity check'. Candidates come from this profile's
        tools.build:compiler_executables cpp value plus the sibling
        clang++ next to the verified CC plus PATH lookup (this
        environment only — no foreign paths). Returns the verified CXX
        path or None; never aborts, failures only print stderr.
        """
        candidates = []
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}) or {}
        except Exception:
            executables = {}
        if isinstance(executables, dict):
            value = executables.get("cpp")
            if value and value not in candidates:
                candidates.append(str(value))
        # Sibling of the verified C compiler: harmonybrew ships clang and
        # clang++ side by side, so if CC probe hit .../bin/clang the CXX
        # is almost surely .../bin/clang++ even when it is not on PATH.
        if verified_cc:
            sibling = os.path.join(
                os.path.dirname(verified_cc), "clang++")
            if sibling not in candidates:
                candidates.append(sibling)
            sibling_gxx = os.path.join(
                os.path.dirname(verified_cc), "g++")
            if sibling_gxx not in candidates:
                candidates.append(sibling_gxx)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        tmpdir = self._writable_tmpdir()
        src = os.path.join(tmpdir, "hmbs-cxx-probe.cpp")
        try:
            with open(src, "w") as handle:
                handle.write("int main(){return 0;}\n")
        except OSError as error:
            self.output.info("cxx probe: cannot write probe source (%s)"
                             % error)
            return None
        for cxx in candidates:
            exe = os.path.join(tmpdir, "hmbs-cxx-probe")
            try:
                if os.path.isfile(exe):
                    os.unlink(exe)
            except OSError:
                pass
            try:
                proc = subprocess.run(
                    [cxx, src, "-o", exe], capture_output=True, text=True,
                    timeout=180)
            except Exception as error:
                self.output.info("cxx probe: %s not launchable (%s)"
                                 % (cxx, error))
                continue
            if proc.returncode == 0 and os.path.isfile(exe):
                try:
                    ver = subprocess.run(
                        [cxx, "--version"], capture_output=True, text=True,
                        timeout=60).stdout.splitlines()
                except Exception:
                    ver = []
                self.output.info("cxx probe: %s OK%s"
                                 % (cxx, ((" (%s)" % ver[0][:100]) if ver else "")))
                return cxx
            self.output.info("cxx probe: %s FAILED rc=%d"
                             % (cxx, proc.returncode))
            for line in ((proc.stderr or "").splitlines()[:20]):
                self.output.info("cxx probe stderr | %s" % line[:300])
        self.output.info("cxx probe: no candidate compiled; "
                         "continuing to configure for config.log evidence")
        return None

    def _dump_config_log(self):
        """Print the config.log tail so the preflight log carries the real
        compiler error (configure's summary line hides it). Bounded tail,
        diagnostics only."""
        path = os.path.join(self.build_folder, "config.log")
        if not os.path.isfile(path):
            self.output.info("config.log not found at %s" % path)
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError as error:
            self.output.info("cannot read config.log (%s)" % error)
            return
        self.output.info("----- config.log tail (%d lines) -----" % len(lines))
        for line in lines[-60:]:
            self.output.info("config.log | %s" % line[:400])

    def build(self):
        apply_conandata_patches(self)
        # Same probed TMPDIR for the configure process itself (covers the
        # custom _configure_with_shell path, which merges os.environ).
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        verified_cc = self._probe_compiler()
        verified_cxx = self._probe_cxx(verified_cc)
        if str(self.settings.os) == "OHOS":
            self._configure_with_shell(verified_cc, verified_cxx)
        else:
            Autotools(self).configure()
        autotools = Autotools(self)
        # Makefiles baked the pinned CC/CXX at configure time; repeat them
        # as make overrides so a broken profile CXX cannot leak back in
        # via conanbuild during compilation.
        make_args = ["-j1"]
        if str(self.settings.os) == "OHOS":
            if verified_cc:
                make_args.append("CC=%s" % verified_cc)
            if verified_cxx:
                make_args.append("CXX=%s" % verified_cxx)
        autotools.make(args=make_args)
        # Upstream has no test suite (audited: no tests/ dir, no TESTS in
        # any of the 7 Makefile.am files - see test_package/MANIFEST.yml
        # upstream_test_audit). build() therefore does NOT invoke make
        # check (upstream_test_in_build: false); the
        # HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package/conanfile.py in the test phase every run
        # (cache-hit safe). This mirrors the merged bwm/0.6.3 +
        # wraplinux/1.7 no_tests precedent: a non-empty
        # upstream_check_command / in_build:true in MANIFEST makes the
        # hmbs lister treat the library as upstream-has-tests and reject
        # no_tests/0.

    def _configure_with_shell(self, verified_cc=None, verified_cxx=None):
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", "")
        shell = _config_shell()
        configure = os.path.join(self.source_folder, "configure")
        # Pin probe-verified CC/CXX so configure and make use the identical
        # binaries that just proved compile+link. CPP/CXXCPP are derived
        # from the same binaries: without them a broken profile CXX leaves
        # configure falling back to /lib/cpp, which fails sanity on OHOS
        # (`C++ preprocessor "/lib/cpp" fails sanity check').
        cpp_from_cc = ("%s -E" % verified_cc) if verified_cc else ""
        cxxcpp_from_cxx = ("%s -E" % verified_cxx) if verified_cxx else ""
        command = " ".join(
            part
            for part in (
                "CONFIG_SHELL=%s" % shlex.quote(shell),
                "SHELL=%s" % shlex.quote(shell),
                # Pin the probe-verified compiler so configure and make use
                # the identical binary that just proved compile+link works.
                ("CC=%s" % shlex.quote(verified_cc)) if verified_cc else "",
                ("CXX=%s" % shlex.quote(verified_cxx)) if verified_cxx else "",
                ("CPP=%s" % shlex.quote(cpp_from_cc)) if cpp_from_cc else "",
                ("CXXCPP=%s" % shlex.quote(cxxcpp_from_cxx)) if cxxcpp_from_cxx else "",
                shlex.quote(shell),
                shlex.quote(configure),
                configure_args,
            )
            if part
        )
        try:
            self.run(command, cwd=self.build_folder, env="conanbuild")
        except ConanException:
            self._dump_config_log()
            raise

    # ---------------------------------------------------------------- package

    def package(self):
        autotools = Autotools(self)
        # examples/ programs are noinst demos (MusicDNS network clients), so a
        # plain install only delivers the library, headers and libofa.pc;
        # this stays a library package (no bin/, hence no commands.json).
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Upstream libtool names the shared object libofa.so.0.0.0
        # (-version-info 0:0:0) and keeps libofa.so/libofa.a development
        # names, so consumers link -lofa.
        self.cpp_info.libs = ["ofa"]
        # Static consumers must also link the configure.in probes
        # (expat/curl/fftw); without this CMakeDeps' libofa::libofa carries
        # no transitive link and a static link misses -lexpat/-lcurl/-lfftw3.
        # Refs use "<pkg>::<pkg>" (leptonica/libbigwig pattern); the target
        # names (expat::expat, CURL::libcurl, fftw::fftw) come from each
        # dependency's own cmake_target_name property.
        self.cpp_info.requires = ["expat::expat", "curl::curl", "fftw::fftw"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libofa")
        self.cpp_info.set_property("cmake_target_name", "libofa::libofa")
        self.cpp_info.set_property("pkg_config_name", "libofa")
