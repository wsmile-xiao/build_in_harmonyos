"""libdvbcsa 1.1.0 DVB-CSA library for HarmonyOS PC."""

import os
import shutil
import subprocess
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, replace_in_file, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdvbcsaConan(ConanFile):
    name = "libdvbcsa"
    version = "1.1.0"
    package_type = "library"
    description = "DVB Common Scrambling Algorithm library"
    homepage = "https://www.videolan.org/developers/libdvbcsa.html"
    license = "GPL-2.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build_requirements(self):
        self.tool_requires("bash/5.3")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, build_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBDVBCSA_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        if not signer or not readelf or not objcopy:
            raise ConanInvalidConfiguration("ELF signer, readelf, and objcopy are required on OHOS")
        original = Path(path)
        pending = original.with_name(original.name + ".dvbcsa-signing")
        signed = original.with_name(original.name + ".dvbcsa-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling: {}".format(original))
        try:
            shutil.copy2(original, pending)
            before = subprocess.run([readelf, "-S", str(pending)], check=True,
                                    capture_output=True, text=True, timeout=20)
            if ".codesign" in before.stdout:
                subprocess.run([objcopy, "--remove-section=.codesign", str(pending)],
                               check=True, capture_output=True, text=True, timeout=20)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF has no .codesign section")
            os.chmod(signed, original.stat().st_mode | 0o755)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        apply_conandata_patches(self)
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.build_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&',
                            strict=True)
            replace_in_file(self, configure, 'tmp=./conf$$-$RANDOM',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"', strict=True)
            replace_in_file(self, configure, '(umask 077 && mkdir "$tmp")',
                            '(umask 007 && mkdir "$tmp")', strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        autotools = Autotools(self)
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                shell = Path(self.dependencies.build["bash"].package_folder, "bin", "bash")
                if not shell.is_file():
                    raise ConanException("declared Bash configure interpreter is missing")
                quoted_shell = shlex.quote(str(shell))
                configure = shlex.quote(str(Path(self.source_folder, "configure")))
                self.run(f"CONFIG_SHELL={quoted_shell} SHELL={quoted_shell} "
                         f"{quoted_shell} {configure} {autotools._configure_args}")
            else:
                autotools.configure()
        autotools.make(args=["-j1"])
        if str(self.settings.os) == "OHOS":
            if self.options.shared:
                self._sign_elf(os.path.join(self.build_folder, "src", ".libs",
                                            "libdvbcsa.so.1.0.1"))
            # Upstream test/Makefile.am registers exactly these four TESTS.
            for name in ("testbsops", "testdec", "testenc", "testbitslice"):
                test_dir = Path(self.build_folder) / "test"
                # Libtool links a .libs/ ELF and exposes a shell wrapper when
                # testing an uninstalled shared library.
                executable = test_dir / ".libs" / name
                if not executable.is_file():
                    executable = test_dir / name
                self._sign_elf(executable)
        check_args = ["-j1"]
        if str(self.settings.os) == "OHOS" and self.options.shared:
            # The real .libs ELFs are signed above. Interpret Libtool's
            # generated shell launchers explicitly instead of asking HMDFS
            # to execute an unsigned script via the implicit ENOEXEC path.
            for name in ("testbsops", "testdec", "testenc", "testbitslice"):
                launcher = Path(self.build_folder, "test", name)
                if not launcher.is_file() or not launcher.read_bytes().startswith(b"#!"):
                    raise ConanException("expected shared Libtool shell launcher: " + name)
            check_args.append("TESTS_ENVIRONMENT=" + quoted_shell)
        autotools.make(target="check", args=check_args)
        self.output.info("UPSTREAM_4_OF_4_PASS")

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_elf(os.path.join(self.package_folder, "lib",
                                        "libdvbcsa.so.1.0.1"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["dvbcsa"]
        self.cpp_info.set_property("cmake_file_name", "libdvbcsa")
        self.cpp_info.set_property("cmake_target_name", "libdvbcsa::libdvbcsa")
        self.cpp_info.set_property("pkg_config_name", "libdvbcsa")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
