"""MyThes 1.2.6 for HarmonyOS PC."""

import os
import re
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MythesConan(ConanFile):
    name = "mythes"
    version = "1.2.6"
    description = "C++ thesaurus lookup library used by LibreOffice"
    license = "LicenseRef-MyThes-BSD-style"
    homepage = "https://dev-www.libreoffice.org/src/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("upstream libtool recipe builds shared only")
        self.options.rm_safe("fPIC")

    def requirements(self):
        # The shared library does not use Hunspell, but the upstream example
        # that make check builds and the README instructs to run does.
        self.requires("hunspell/1.7.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("MYTHES_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("MYTHES_SOURCE_ARCHIVE must name a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-werror")
        toolchain.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _run_environment(self):
        environment = Environment()
        environment.define("PKG_CONFIG_LIBDIR", self.generators_folder)
        environment.define("PKG_CONFIG_PATH", self.generators_folder)
        # The published Hunspell metadata advertises include/, while its
        # public hunspell.hxx is actually under include/hunspell/. The
        # upstream example (built by make check) includes it unqualified.
        hunspell_include = Path(self.dependencies["hunspell"].package_folder,
                                "include", "hunspell")
        if not (hunspell_include / "hunspell.hxx").is_file():
            raise ConanInvalidConfiguration("missing packaged hunspell.hxx")
        environment.define("HUNSPELL_CFLAGS", "-I" + str(hunspell_include))
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if directory.is_dir():
                    environment.prepend_path("LD_LIBRARY_PATH", str(directory))
        return environment

    def build(self):
        args = []
        header = Path(self.source_folder, "mythes.hxx")
        text = header.read_text(encoding="utf-8")
        marker = "#define _MYTHES_HXX_"
        addition = marker + "\n// Packaged public header uses FILE.\n#include <stdio.h>"
        if text.count(marker) != 1:
            raise ConanInvalidConfiguration("unexpected mythes.hxx include guard")
        if addition not in text:
            header.write_text(text.replace(marker, addition, 1), encoding="utf-8")
        if str(self.settings.os) == "OHOS":
            # Autoconf's mktemp -d unconditionally creates a 0700 directory.
            # On CI HMDFS its mapped owner differs from the build uid, so
            # config.status cannot read its own subs1.awk. Create the unique
            # directory group-accessible from the outset (chmod is ineffective).
            configure = Path(self.source_folder, "configure")
            script = configure.read_text(encoding="utf-8")
            old_temp = '''{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            new_temp = '''{
  tmp=./conf$$-$RANDOM
  (umask 007 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            if script.count(old_temp) != 1:
                raise ConanInvalidConfiguration("unexpected Autoconf temp-directory logic")
            configure.write_text(script.replace(old_temp, new_temp, 1),
                                 encoding="utf-8")
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = executables.get("c")
            if not compiler or not Path(compiler).is_file():
                raise ConanInvalidConfiguration("missing configured C compiler")
            result = subprocess.run(
                [compiler, "-dumpmachine"], capture_output=True, text=True,
                check=True, timeout=10,
            )
            triplet = result.stdout.strip()
            if not re.fullmatch(r"[A-Za-z0-9_.+-]+", triplet):
                raise ConanInvalidConfiguration("invalid compiler target triplet")
            args = ["--build=" + triplet, "--host=" + triplet]
        with self._run_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure(args=args)
            autotools.make(args=["-j2"])
            # Upstream declares check_PROGRAMS=example but no TESTS. The
            # documented invocations are therefore run explicitly, not
            # counted merely because make check built the executable.
            autotools.make(target="check", args=["-j1"])
            example = Path(self.build_folder, "example")
            if not example.is_file():
                raise ConanInvalidConfiguration("make check did not build example")
            cases = (
                ("th_en_US_new.idx", "th_en_US_new.dat", "checkme.lst"),
                ("morph.idx", "morph.dat", "morph.lst", "morph.aff", "morph.dic"),
            )
            for index, filenames in enumerate(cases, 1):
                paths = [str(Path(self.source_folder, name)) for name in filenames]
                # Libtool's top-level example is a shell wrapper. HMDFS
                # requires an explicit interpreter for this nested script.
                command = (["/system/bin/sh", str(example)] if
                           str(self.settings.os) == "OHOS" else [str(example)])
                run = subprocess.run([*command, *paths],
                                     cwd=self.source_folder, capture_output=True,
                                     text=True, check=False, timeout=120)
                output = run.stdout + run.stderr
                Path(self.build_folder, f"upstream-example-{index}.log").write_text(
                    output, encoding="utf-8"
                )
                if run.returncode or not re.search(r"has [1-9][0-9]* meanings", output):
                    raise ConanInvalidConfiguration(
                        f"documented upstream example {index}/2 failed (rc={run.returncode})"
                    )
                self.output.info(f"UPSTREAM_EXAMPLE {index}/2 PASS")
            self.output.info("# TOTAL: 2")
            self.output.info("# PASS: 2")
            self.output.info("# SKIP: 0")
            self.output.info("# FAIL: 0")

    def package(self):
        with self._run_environment().vars(self).apply():
            Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        indexer = Path(self.package_folder, "bin", "th_gen_idx.pl")
        if not indexer.is_file():
            raise ValueError("MyThes did not install its index generator")
        script = indexer.read_text(encoding="utf-8")
        if not script.startswith("#!/usr/bin/perl\n"):
            raise ValueError("unexpected upstream indexer shebang")
        indexer.write_text(script.replace("#!/usr/bin/perl\n",
                                         "#!/usr/bin/env perl\n", 1),
                           encoding="utf-8")
        pc = Path(self.package_folder, "lib", "pkgconfig", "mythes.pc")
        if not pc.is_file():
            raise ValueError("MyThes did not install mythes.pc")
        lines = pc.read_text(encoding="utf-8").splitlines()
        prefixes = [i for i, line in enumerate(lines) if line.startswith("prefix=")]
        if len(prefixes) != 1:
            raise ValueError("unexpected mythes.pc prefix")
        lines[prefixes[0]] = "prefix=${pcfiledir}/../.."
        pc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = ["mythes-1.2"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "mythes")
        self.cpp_info.set_property("cmake_target_name", "mythes::mythes")
        self.cpp_info.set_property("pkg_config_name", "mythes")
