#!/usr/bin/env python3
"""Conan recipe for xpar 1.1, an error-correction command-line tool."""

import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XparConan(ConanFile):
    name = "xpar"
    version = "1.1"
    description = "Error-correction and integrity command-line tool"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/iczelia/xpar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("error-correction", "integrity", "parity", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("xpar requires a POSIX host (Linux or OHOS)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-liburing")
        if self.settings.arch == "armv8":
            tc.configure_args.append("--enable-aarch64")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._fix_ohos_config_status_umask()
            self._build_ohos()
            if can_run(self):
                try:
                    self._run_ohos_self_check(self._ohos_build_folder)
                except Exception:
                    self._cleanup_ohos_build()
                    raise
            else:
                self.output.warning(
                    "Upstream self-check was not run because Conan cannot execute "
                    "the target binary on this build machine"
                )
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            if can_run(self):
                autotools.make(args=["-j1", "self-check"])
            else:
                self.output.warning(
                    "Upstream self-check was not run because Conan cannot execute "
                    "the target binary on this build machine"
                )

    def _fix_ohos_config_status_umask(self):
        """Avoid HMDFS making Autoconf's private config.status dir unwritable.

        GNU config.status creates ./confXXXXXX under `umask 077`, then writes
        subs1.awk there. On the Buildbot HMDFS mount this mode produces a
        directory that rejects that write even though configure can write in
        its build directory. Relax the generated configure umask before the
        out-of-source configure run; strict matching prevents a silent no-op
        if the upstream script changes.
        """
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022", strict=True)
        self.output.info("Applied HMDFS config.status fix: umask 077 -> 022")

    def _ohos_temp_root(self):
        """Return a writable temporary root, preferring the worker's TMPDIR."""
        candidates = (
            os.environ.get("TMPDIR"),
            os.path.join(os.path.expanduser("~"), "tmp"),
        )
        errors = []
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                os.makedirs(candidate, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix=".xpar-write-probe-", dir=candidate
                ) as probe_dir:
                    probe_file = os.path.join(probe_dir, "subs1.awk")
                    with open(probe_file, "wb") as stream:
                        stream.write(b"probe")
                return candidate
            except OSError as exc:
                errors.append("{}: {}".format(candidate, exc))
        raise ConanException(
            "No writable HarmonyOS temporary directory; checked " + "; ".join(errors)
        )

    def _run_ohos_self_check(self, build_folder):
        """Run upstream's self-check from a writable temporary directory.

        The generated Makefile has a few negative tests that redirect to
        /tmp/bad. HarmonyOS mounts /tmp read-only, so redirect those test-only
        outputs into the writable self-check directory. The complete build tree
        is copied so the Makefile can be adjusted and its test binaries signed
        without modifying the package build output.
        """
        tmp_root = getattr(self, "_ohos_tmp_root", None) or self._ohos_temp_root()
        with tempfile.TemporaryDirectory(prefix="xpar-self-check-", dir=tmp_root) as work:
            # The self-check target depends on generated .deps files and helper
            # scripts as well as the executable. Preserve the whole build tree
            # so make does not try to rebuild missing prerequisites in isolation.
            shutil.copytree(build_folder, work, dirs_exist_ok=True)

            binary = os.path.join(work, "xpar")
            helper = os.path.join(work, "inject-errors")
            makefile = os.path.join(work, "Makefile")
            for artifact in (binary, makefile):
                if not os.path.isfile(artifact):
                    raise ConanException("upstream self-check is missing " + artifact)
            if not os.path.isfile(helper):
                include_flags = '-I"{}" -I"{}"'.format(work, self.source_folder)
                shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"
                make = shutil.which("make") or "/data/service/hnp/bin/make"
                self.run(
                    "{} -j1 {} {} inject-errors".format(
                        shlex.quote(make),
                        shlex.quote("SHELL=" + shell),
                        shlex.quote("CFLAGS_FOR_BUILD=" + include_flags),
                    ),
                    cwd=work,
                    env="conanbuild",
                )
            if not os.path.isfile(helper):
                raise ConanException("upstream self-check is missing " + helper)

            os.chmod(binary, 0o755)
            self._self_sign(binary)
            os.chmod(helper, 0o755)
            self._self_sign(helper)

            with open(makefile, "r", encoding="utf-8") as stream:
                contents = stream.read()
            if "/tmp/bad" not in contents:
                raise ConanException("expected /tmp/bad self-check redirections were not found")
            with open(makefile, "w", encoding="utf-8") as stream:
                stream.write(contents.replace("/tmp/bad", "xpar.bad.out"))

            shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"
            make = shutil.which("make") or "/data/service/hnp/bin/make"
            result = subprocess.run(
                [make, "-f", makefile, "-j1", "SHELL=" + shell, "self-check"],
                cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=False, timeout=600,
            )
            self.output.info("Upstream make self-check output:\n" + result.stdout[-12000:])
            if result.returncode:
                raise ConanException("upstream make self-check failed (exit %d)" % result.returncode)

    def _build_ohos(self):
        """Build out of source under the worker's writable temporary directory."""
        tmp_root = self._ohos_temp_root()
        self.output.info("HarmonyOS temporary build root: " + tmp_root)
        build_folder = tempfile.mkdtemp(prefix="xpar-build-", dir=tmp_root)
        try:
            # Keep generated files in the probed writable tree; config.status's
            # own relative ./confXXXXXX directory is fixed separately above.
            self.output.info(
                "Configuring source {} in build directory {}".format(
                    self.source_folder, build_folder
                )
            )
            self._configure_ohos(self.source_folder, build_folder)

            shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"
            make = shutil.which("make") or "/data/service/hnp/bin/make"
            self.run(
                "{} -j1 {}".format(
                    shlex.quote(make), shlex.quote("SHELL=" + shell)
                ),
                cwd=build_folder,
                env="conanbuild",
            )
        except Exception:
            shutil.rmtree(build_folder, ignore_errors=True)
            raise
        self._ohos_build_folder = build_folder
        self._ohos_tmp_root = tmp_root

    def _configure_ohos(self, source_folder, build_folder):
        """Run the source configure script from an independent build directory."""
        shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") or "clang++"
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
        nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"

        env = Environment()
        env.define("CC", shell + " " + cc)
        env.define("CXX", shell + " " + cxx)
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        env.define("NM", nm)
        env.define("LD", ld)
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        # The HarmonyOS SDK bash cannot always getcwd() in the app sandbox,
        # even after the parent shell changed to this path. Autoconf re-execs
        # through CONFIG_SHELL and asks the shell for its working directory;
        # provide the correct logical path for that child process.
        env.define("PWD", build_folder)

        configure_args = load_toolchain_args(self.generators_folder).get("configure_args") or ""
        configure = os.path.join(source_folder, "configure")
        toolchain = AutotoolsToolchain(self)
        with toolchain.vars().apply(), env.vars(self).apply():
            self.run(
                'cd {} && "{}" "{}" --srcdir={} {}'.format(
                    shlex.quote(build_folder), shell, configure,
                    shlex.quote(source_folder), configure_args
                ),
                cwd=build_folder,
            )

    def _self_sign(self, binary):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", binary],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False, timeout=15)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or ""
        if not signer:
            raise ConanException("HarmonyOS binary-sign-tool is not available for upstream self-check")
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=30,
        )
        if result.returncode:
            output = result.stdout.decode(errors="replace")
            raise ConanException("HarmonyOS self-sign failed: " + output[-800:])

    def _cleanup_ohos_build(self):
        build_folder = getattr(self, "_ohos_build_folder", None)
        if build_folder:
            shutil.rmtree(build_folder, ignore_errors=True)
            del self._ohos_build_folder

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        licdir = os.path.join(self.package_folder, "licenses")
        for directory in (bindir, mandir, licdir):
            os.makedirs(directory, exist_ok=True)

        build_folder = getattr(self, "_ohos_build_folder", self.build_folder)
        try:
            copy(self, "xpar", src=build_folder, dst=bindir, keep_path=False)
            copy(self, "xpar.1", src=self.source_folder, dst=mandir, keep_path=False)
            copy(self, "COPYING", src=self.source_folder, dst=licdir, keep_path=False)
            executable = os.path.join(bindir, "xpar")
            if not os.path.isfile(executable):
                raise ConanException("package(): missing executable " + executable)
            os.chmod(executable, 0o755)
        finally:
            self._cleanup_ohos_build()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
