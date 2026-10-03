"""libGenome 1.3.11-svn20110227.4616 for OpenHarmony PC."""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgenomeConan(ConanFile):
    name = "libgenome"
    version = "1.3.11-svn20110227.4616"
    description = "C++ DNA and protein sequence I/O and manipulation library"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/libgenome/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    win_bash = True

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBGENOME_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("LIBGENOME_SOURCE_ARCHIVE must be a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        path = Path(path)
        if not path.is_file():
            raise ConanInvalidConfiguration("missing ELF to sign: " + str(path))
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        objcopy = shutil.which("llvm-objcopy")
        if not all((signer, readelf, objcopy)):
            raise ConanInvalidConfiguration("OHOS execution requires binary-sign-tool, llvm-readelf and llvm-objcopy")
        pending = path.with_name(path.name + ".libgenome-signing")
        signed = path.with_name(path.name + ".libgenome-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling: " + str(path))
        try:
            shutil.copy2(path, pending)
            before = subprocess.run([readelf, "-S", str(pending)], capture_output=True, text=True, check=True, timeout=10).stdout
            if ".codesign" in before:
                subprocess.run([objcopy, "--remove-section", ".codesign", str(pending)], check=True, timeout=10)
            subprocess.run([signer, "sign", "-inFile", str(pending), "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, timeout=40)
            after = subprocess.run([readelf, "-S", str(signed)], capture_output=True, text=True, check=True, timeout=10).stdout
            if len(re.findall(r"\s\.codesign\s", after)) != 1:
                raise ConanInvalidConfiguration("signed ELF lacks a unique .codesign section: " + str(path))
            signed.chmod(path.stat().st_mode | 0o755)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    @staticmethod
    def _refresh_aliases(real, directory):
        for alias in ("libGenome-1.3.so.0", "libGenome-1.3.so"):
            target = directory / alias
            if not target.exists():
                raise ConanInvalidConfiguration("missing libtool alias: " + str(target))
            if target.is_symlink():
                if target.resolve() != real.resolve():
                    raise ConanInvalidConfiguration("libtool alias points elsewhere: " + str(target))
            else:
                shutil.copy2(real, target)

    def _automake_entrypoints(self):
        """Bypass OHOS automake package wrappers with stale absolute Perl shebangs."""
        package = Path(self.dependencies.build["automake"].package_folder)
        system_perl = shutil.which("perl")
        if not system_perl:
            raise ConanInvalidConfiguration("host Perl is required for Autotools bootstrap")
        perl = Path(system_perl).resolve()
        conan_perl = Path(self.dependencies.build["perl"].package_folder, "bin", "perl").resolve()
        if perl == conan_perl:
            raise ConanInvalidConfiguration("Autotools bootstrap must not use Conan Perl from the user cache")
        overlay = Path(self.build_folder, ".libgenome-automake")
        overlay.mkdir(exist_ok=True)
        scripts = {
            "aclocal": (".aclocal-real", [
                "--automake-acdir=" + str(package / "share" / "aclocal-1.18"),
                "--system-acdir=" + str(package / "share" / "aclocal")]),
            "automake": (".automake-real", [
                "--libdir=" + str(package / "share" / "automake-1.18")]),
        }
        result = {}
        for name, (real_name, arguments) in scripts.items():
            real = package / "bin" / real_name
            if not real.is_file():
                raise ConanInvalidConfiguration("automake tool payload missing: " + str(real))
            wrapper = overlay / name
            argv = " ".join(shlex.quote(part) for part in (str(real), *arguments))
            wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(str(perl)) +
                               " " + argv + ' "$@"\n', encoding="utf-8")
            wrapper.chmod(0o700)
            result[name] = wrapper
        result["perl"] = perl
        autoconf = Path(self.dependencies.build["autoconf"].package_folder)
        result["autoreconf"] = autoconf / "bin" / "autoreconf"
        result["perl5lib"] = ":".join((str(package / "share" / "automake-1.18"),
                                      str(autoconf / "share" / "autoconf")))
        if not result["autoreconf"].is_file():
            raise ConanInvalidConfiguration("Autoconf autoreconf payload missing")
        return result

    def _patch_generated_config_guess(self):
        path = Path(self.source_folder, "config", "config.guess")
        if not path.is_file():
            raise ConanInvalidConfiguration("autoreconf did not generate config.guess")
        contents = path.read_text(encoding="utf-8")
        anchor = "    *:NetBSD:*:*)"
        if contents.count(anchor) != 1:
            raise ConanInvalidConfiguration("unexpected config.guess format")
        harmony = ("    *:HarmonyOS:*:*)\n"
                   "        echo \"$UNAME_MACHINE-unknown-linux-ohos\"\n"
                   "        exit ;;\n")
        path.write_text(contents.replace(anchor, harmony + anchor, 1), encoding="utf-8")

    def build(self):
        entrypoints = self._automake_entrypoints()
        command = ("ACLOCAL=" + shlex.quote(str(entrypoints["aclocal"])) +
                   " AUTOMAKE=" + shlex.quote(str(entrypoints["automake"])) +
                   " PERL=" + shlex.quote(str(entrypoints["perl"])) +
                   " PERL5LIB=" + shlex.quote(entrypoints["perl5lib"]) +
                   " GREP=grep EGREP='grep -E' FGREP='grep -F'" +
                   " " + shlex.quote(str(entrypoints["autoreconf"])) +
                   " --force --install -I config -I m4")
        self.run(command,
                 cwd=self.source_folder, env="conanbuild")
        if str(self.settings.os) == "OHOS":
            self._patch_generated_config_guess()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        if str(self.settings.os) == "OHOS" and not cross_building(self) and self.options.shared:
            library_dir = Path(self.build_folder, "libGenome", ".libs")
            real = library_dir / "libGenome-1.3.so.0.1.3"
            self._sign_elf(real)
            self._refresh_aliases(real, library_dir)
        autotools.make(target="TestRevComp", args=["-j1", "-C", "libGenome"])
        if cross_building(self):
            self.output.info("UPSTREAM_TESTS=NOT_RUN: cross-built test cannot execute on build host")
            return
        if str(self.settings.os) == "OHOS":
            directory = Path(self.build_folder, "libGenome")
            if self.options.shared:
                library_dir = directory / ".libs"
                executable = library_dir / "TestRevComp"
                self._sign_elf(executable)
                shutil.copy2(executable, directory / "TestRevComp")
                runtime = Environment()
                runtime.prepend_path("LD_LIBRARY_PATH", str(library_dir))
            else:
                self._sign_elf(directory / "TestRevComp")
                runtime = Environment()
            with runtime.vars(self).apply():
                autotools.make(target="check", args=["-j1"])
        else:
            autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        library_dir = Path(self.package_folder, "lib")
        library = library_dir / "libGenome-1.3.so.0.1.3"
        if self.options.shared:
            if not library.is_file():
                raise ConanInvalidConfiguration("shared libGenome artifact missing")
            if str(self.settings.os) == "OHOS" and not cross_building(self):
                self._sign_elf(library)
                self._refresh_aliases(library, library_dir)
            static = library_dir / "libGenome-1.3.a"
            if static.exists():
                static.unlink()
        else:
            if not (library_dir / "libGenome-1.3.a").is_file():
                raise ConanInvalidConfiguration("static libGenome artifact missing")
        libtool_archive = library_dir / "libGenome-1.3.la"
        if libtool_archive.exists():
            libtool_archive.unlink()
        pkgconfig = library_dir / "pkgconfig" / "libGenome-1.3.pc"
        if not pkgconfig.is_file():
            raise ConanInvalidConfiguration("libGenome pkg-config file missing")
        text = pkgconfig.read_text(encoding="utf-8")
        updated, count = re.subn(r"^prefix=(?:/usr|/)$",
                                 "prefix=${pcfiledir}/../..", text, count=1, flags=re.MULTILINE)
        if count != 1:
            raise ConanInvalidConfiguration("unexpected libGenome pkg-config prefix")
        pkgconfig.write_text(updated, encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = ["Genome-1.3"]
        self.cpp_info.includedirs = ["include/libGenome-1.3"]
        self.cpp_info.set_property("cmake_file_name", "libgenome")
        self.cpp_info.set_property("cmake_target_name", "libgenome::libgenome")
        self.cpp_info.set_property("pkg_config_name", "libGenome-1.3")
