#!/usr/bin/env python3
"""Conan recipe for qperf 0.4.11 -- Autotools (bootstrap required).

qperf measures bandwidth and latency between two nodes. It works over TCP/UDP
(socket transports) and, when built with libibverbs/librdmacm, over the RDMA
transports.

Three structural facts drive this recipe; each is recorded with its measured
evidence in notes.md:

1. The upstream tag tarball ships ``configure.ac`` / ``Makefile.am`` only --
   there is no generated ``configure`` and no ``Makefile.in``, so GNU autotools
   must bootstrap them (upstream's README says ``./autogen.sh``).
2. ``src/Makefile.am`` generates ``help.c`` and ``qperf.1`` by executing
   ``./mkhelp`` / ``./mkman`` *from the build directory* with relative inputs
   (``help.txt``), which an out-of-tree build cannot resolve -- hence the
   in-tree layout below instead of patching upstream's generator rules.
3. ``src/support.c`` calls ``sockatmark()``, which the OpenHarmony C library
   neither declares nor exports; the portability patch routes the query
   through the underlying ``SIOCATMARK`` ioctl, which the SDK does provide.
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# The OHOS root shell.  /bin/sh is toybox and resolves getcwd() inside the
# Conan cache correctly; the bash shipped by the SDK (see below) does not.
_POSIX_SHELL = "/bin/sh"


class QperfConan(ConanFile):
    name = "qperf"
    version = "0.4.11"
    description = ("Measure RDMA and socket (TCP/UDP/RDS/SCTP/SDP) bandwidth "
                   "and latency between two nodes")
    license = "GPL-2.0-only OR BSD-2-Clause"
    homepage = "https://github.com/linux-rdma/qperf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qperf needs a POSIX host (Linux/OHOS), got {self.settings.os}")

    def build_requirements(self):
        # The tag tarball has no generated build inputs, so aclocal/automake
        # must run during the build.  autoconf, m4 and perl come from the OHOS
        # SDK (/data/service/hnp/bin) and are deliberately NOT declared:
        # declaring autoconf would pull an OHOS-built perl whose XS .so
        # conflicts with the SDK perl interpreter (see accel-config 4.1.9).
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)
        # In-tree build: src/Makefile.am runs ./mkhelp and ./mkman with CWD set
        # to the build directory and reads "help.txt" through a *relative*
        # path, so an out-of-tree build directory cannot find either the
        # generator scripts or their input.
        self.folders.build = "."
        self.folders.generators = ".conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ env
    def _neutralize_umask077(self, configure):
        """Make autoconf's scratch directory usable on HarmonyOS/HMDFS.

        ``config.status`` (embedded in the generated ``configure``) creates its
        scratch directory with ``(umask 077 && mktemp -d "./confXXXXXX")`` and
        falls back to ``(umask 077 && mkdir "$tmp")``.  Under ``umask 077`` the
        toybox ``mktemp`` produces nothing and the ``mkdir`` fallback yields a
        directory HMDFS will not accept writes into, so every configure probe
        succeeds and then the run dies with

            ./config.status[726]: can't create ./confNNNN-NNNN/subs1.awk:
            Permission denied
            config.status: error: could not setup config files machinery

        Measured on the same build directory: ``mkdir``/``mktemp -d`` with the
        default umask 022 create ``drwxr-s--x``/``drwxrws--x`` directories that
        *are* writable, so only the restrictive umask is wrong here.  The
        substitution is applied to the *generated* ``configure`` (never
        committed, R6-compatible) and aborts if the expected template is not
        found, so a future autoconf change cannot silently reintroduce the bug.
        """
        with open(configure, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        patched = content.replace("(umask 077 && ", "(umask 022 && ")
        if patched == content:
            raise ConanException(
                "autoconf config.status 'umask 077' template not found in the "
                "generated configure; the HMDFS scratch-directory workaround "
                "must be revisited")
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info("neutralized %d 'umask 077' scratch-dir sites in "
                         "configure (HMDFS writable-temp workaround)" %
                         (content.count("(umask 077 && ")))

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # /tmp is read-only on OHOS, so keep autoconf/configure scratch files
        # inside this isolated build directory.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        env.define_path("TMPDIR", tmpdir)
        tc.generate(env=env)

    def _shell_prefix(self):
        """``CONFIG_SHELL``/``SHELL`` pinned to the platform POSIX shell.

        Kept on the command line rather than in the generated environment
        because ``conanbuild.sh`` sources the profile ``[buildenv]`` module
        *after* the toolchain module, which re-exports those two variables to
        the SDK bash again.
        """
        return "CONFIG_SHELL={0} SHELL={0} ".format(_POSIX_SHELL)

    # -------------------------------------------------------------- bootstrap
    def _automake_paths(self):
        pkg = self.dependencies.build["automake"].package_folder
        libdirs = sorted(glob.glob(os.path.join(pkg, "share", "automake-*")))
        if not libdirs:
            raise ConanException(f"automake perl libdir not found under {pkg}")
        libdir = libdirs[0]
        version = os.path.basename(libdir).split("-", 1)[1]
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl):
            raise ConanException("perl interpreter not available for automake")
        return pkg, libdir, version, perl

    def _bootstrap_autotools(self):
        """Recreate configure / Makefile.in from configure.ac / Makefile.am.

        Upstream's ``autogen.sh`` cannot be used verbatim here.  The automake
        conan package hardcodes its perl library directory as
        ``our $libdir = $ENV{"AUTOMAKE_LIBDIR"} || '//share/automake-1.18'`` in
        ``share/automake-1.18/Automake/Config.pm`` (the package was built with
        an empty install prefix), so automake aborts with
        ``cannot open < //share/automake-1.18/am/header-vars.am`` plus
        ``required file ./compile not found`` before emitting anything.  That
        module exposes the override as an environment variable, which is what
        is used below.  A host automake is not an option either: its
        ``#!/usr/bin/perl`` shebang cannot be satisfied because OHOS ships perl
        only under /data/service/hnp/bin.  Both traps are avoided by calling
        the package's real perl entry points through the interpreter with an
        explicit ``-I`` library directory.
        """
        pkg, libdir, version, perl = self._automake_paths()
        src = self.source_folder
        env_prefix = "AUTOMAKE_LIBDIR={} ".format(shlex.quote(libdir))
        base = [perl, "-I", libdir]

        # aclocal: merge system + package m4 macros into aclocal.m4.
        self.run(env_prefix + shlex.join(base + [
            os.path.join(pkg, "bin", ".aclocal-real"),
            "--automake-acdir="
            + os.path.join(pkg, "share", "aclocal-" + version),
            "--system-acdir=" + os.path.join(pkg, "share", "aclocal"),
            "--force"]), cwd=src, env="conanbuild")

        # AM_INIT_AUTOMAKE defaults to strict GNU mode, which demands NEWS,
        # ChangeLog and README.  Upstream's autogen.sh touches them the same way.
        for name in ("NEWS", "README", "ChangeLog"):
            path = os.path.join(src, name)
            if not os.path.exists(path):
                with open(path, "a", encoding="utf-8"):
                    pass

        # --foreign matches upstream's autogen.sh; it is what lets automake
        # proceed without AUTHORS/INSTALL, which the tag tarball does not ship.
        self.run(env_prefix + shlex.join(base + [
            os.path.join(pkg, "bin", ".automake-real"),
            "--foreign", "--add-missing", "--copy", "--force-missing",
            "--force"]), cwd=src, env="conanbuild")

        self.run("autoconf --force", cwd=src, env="conanbuild")

        configure = os.path.join(src, "configure")
        if not os.path.exists(configure):
            raise ConanException("autotools bootstrap did not produce configure")
        return configure

    # ------------------------------------------------------------- exec modes
    # Autotools helper scripts are executed, not interpreted from a fixed
    # shell line, so their executable bit is load-bearing (E490).
    _EXEC_HELPERS = ("configure", "config.guess", "config.sub", "install-sh",
                     "missing", "mkinstalldirs", "depcomp", "compile")

    def _restore_exec_bits(self):
        """Re-assert executable modes on autotools and generator helper scripts.

        Some HarmonyOS adaptation paths rewrite source content without
        preserving file modes (knowledge entry E490), which turns
        ``config.status`` (needs install-sh/missing) and the in-tree generators
        ``src/mkhelp`` / ``src/mkman`` (run as ``./mkhelp`` by
        src/Makefile.am) into failures that look like a toolchain problem.
        """
        wanted = [os.path.join(self.source_folder, n) for n in self._EXEC_HELPERS]
        wanted += [os.path.join(self.source_folder, "src", n)
                   for n in ("mkhelp", "mkman")]
        restored = []
        for path in wanted:
            if os.path.isfile(path):
                os.chmod(path, (os.stat(path).st_mode & 0o700) | 0o111)
                restored.append(os.path.basename(path))
        self.output.info("restored exec bits on: " + ", ".join(sorted(restored)))

    # --------------------------------------------------------------- configure
    def _configure(self, configure):
        """Run configure pinned to the platform POSIX shell.

        autoconf's configure re-execs itself under ``$CONFIG_SHELL``, and the
        OHOS Conan profile points that at ``/data/service/hnp/bin/bash``, whose
        bash 5.3 cannot resolve getcwd(3) for the Conan cache path on HMDFS
        (``shell-init: error retrieving current directory: getcwd: cannot
        access parent directories``).  The re-exec therefore dies before a
        single probe runs, with ``configure: error: working directory cannot be
        determined``.  The configure arguments are taken verbatim from the
        AutotoolsToolchain output, exactly like ``Autotools.configure()`` does,
        which is what keeps ``${prefix}`` quoted against shell expansion.
        """
        args = load_toolchain_args(self.generators_folder).get("configure_args") or ""
        self.run('{} "{}" {}'.format(self._shell_prefix(), configure, args),
                 cwd=self.build_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            configure = self._bootstrap_autotools()
        self._restore_exec_bits()
        self._neutralize_umask077(configure)
        self._configure(configure)
        # -j1: GNU make's jobserver FIFO is unreliable on HMDFS.
        self.run(self._shell_prefix() + "make -j1", cwd=self.build_folder,
                 env="conanbuild")

    def package(self):
        # DESTDIR with --prefix=/ is how the AutotoolsToolchain install
        # directories are laid out; run it with an explicit cwd so the step
        # does not depend on the inherited working directory.
        self.run('{}make install DESTDIR="{}"'.format(
            self._shell_prefix(), self.package_folder),
            cwd=self.build_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "qperf"))

    @staticmethod
    def _sign_ohos_elf(path):
        """Self-sign the packaged ELF so the OHOS kernel will exec it.

        Unsigned binaries are killed on exec on HarmonyOS; CI re-signs during
        the release pipeline, this only makes local W3/consumer tests run.
        """
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=120)
        sections = subprocess.run([readelf, "-SW", output], check=True,
                                  capture_output=True, text=True,
                                  timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged ELF has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        # qperf installs a single executable and no libraries or headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
