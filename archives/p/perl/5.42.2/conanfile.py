import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class PerlConan(ConanFile):
    name = "perl"
    version = "5.42.2"
    description = "Perl programming language interpreter"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://www.perl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("perl", "interpreter", "scripting")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Perl is supported on Linux and OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        toolchain_bin = os.path.dirname(cc)
        return (
            cc,
            compilers.get("ar") or os.path.join(toolchain_bin, "llvm-ar"),
            compilers.get("ranlib") or os.path.join(toolchain_bin, "llvm-ranlib"),
        )

    def build(self):
        cc, ar, ranlib = self._tools()
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if self.settings.os == "OHOS":
            # OHOS uses a case-insensitive filesystem. Configure generates
            # Makefile, then its stale-file cleanup removes "makefile", which
            # resolves to the same path and deletes the generated Makefile.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "Makefile.SH"),
                "$rm -f $firstmakefile",
                'case "$osname" in harmonyos) ;; *) $rm -f $firstmakefile ;; esac',
            )
            # With -d, Configure otherwise answers yes to its final
            # "make depend" prompt. That target expects generated *.depends
            # files which do not exist on the initial OHOS build.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "Configure"),
                'dflt=y\n\tcase "$silent" in\n\ttrue) ;;',
                'dflt=n\n\tcase "$silent" in\n\ttrue) ;;',
            )
            locale_source = os.path.join(self.source_folder, "locale.c")
            # OHOS defines LC_IDENTIFICATION but not glibc's corresponding
            # _NL_IDENTIFICATION_* langinfo values.
            replace_in_file(
                self,
                locale_source,
                "      case _NL_IDENTIFICATION_TITLE:\n"
                "      case _NL_IDENTIFICATION_SOURCE:\n"
                "      case _NL_IDENTIFICATION_ADDRESS:",
                "#  ifdef _NL_IDENTIFICATION_TITLE\n"
                "      case _NL_IDENTIFICATION_TITLE:\n"
                "      case _NL_IDENTIFICATION_SOURCE:\n"
                "      case _NL_IDENTIFICATION_ADDRESS:",
            )
            replace_in_file(
                self,
                locale_source,
                "      case _NL_IDENTIFICATION_CATEGORY:\n"
                "#  ifdef USE_LOCALE_IDENTIFICATION\n"
                "        cat_index = LC_IDENTIFICATION_INDEX_;\n"
                "#  endif\n"
                "        break;",
                "      case _NL_IDENTIFICATION_CATEGORY:\n"
                "#  ifdef USE_LOCALE_IDENTIFICATION\n"
                "        cat_index = LC_IDENTIFICATION_INDEX_;\n"
                "#  endif\n"
                "        break;\n"
                "#  endif",
            )
            replace_in_file(
                self,
                locale_source,
                "#  if ! defined(HAS_SOME_LANGINFO) || ! LC_IDENTIFICATION_AVAIL_",
                "#  if defined(_NL_IDENTIFICATION_TITLE) && "
                "(! defined(HAS_SOME_LANGINFO) || ! LC_IDENTIFICATION_AVAIL_)",
            )
        configure_args = [
            "-des",
            f"-Dprefix={self.package_folder}",
            f"-Dcc={cc}",
            f"-Dld={cc}",
            f"-Dar={ar}",
            f"-Dranlib={ranlib}",
            # The OHOS libc.so is a linker script. Perl's optional nm scan
            # cannot parse it and falls through to the unavailable `bld` tool.
            "-Uusenm",
            "-Duseshrplib=false",
            "-Dman1dir=none",
            "-Dman3dir=none",
        ]
        self.run(
            f'"{shell}" Configure {" ".join(configure_args)}',
            cwd=self.source_folder,
        )
        # OHOS does not support GNU make's jobserver FIFO implementation.
        self.run("make -j1", cwd=self.source_folder)
        self.run("make test", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)
        copy(self, "Artistic", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "Copying", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
