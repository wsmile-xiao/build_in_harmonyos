#!/usr/bin/env python3
"""Conan recipe for Flamethrower 0.1.8 (Perl MakeMaker)."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class FlamethrowerConan(ConanFile):
    name = "flamethrower"
    version = "0.1.8"
    description = "Multicast file distribution utility built on udpcast"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/flamethrower"
    url = "https://tracker.debian.org/pkg/flamethrower"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("appconfig/1.71.1")
        self.requires("udpcast/20250223")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib", "flamethrower")
        libexec_bindir = os.path.join(self.package_folder, "libexec", "flamethrower", "bin")
        etcdir = os.path.join(self.package_folder, "etc", "flamethrower")
        initdir = os.path.join(self.package_folder, "etc", "init.d")

        for path in (bindir, libdir, libexec_bindir, etcdir, initdir):
            os.makedirs(path, exist_ok=True)

        copy(self, "Flamethrower.pm", src=os.path.join(self.source_folder, "lib"), dst=libdir, keep_path=False)
        copy(self, "flamethrower", src=os.path.join(self.source_folder, "bin"), dst=libexec_bindir, keep_path=False)
        copy(self, "flamethrowerd", src=os.path.join(self.source_folder, "bin"), dst=libexec_bindir, keep_path=False)
        copy(self, "flamethrower.conf", src=os.path.join(self.source_folder, "etc"), dst=etcdir, keep_path=False)
        copy(
            self,
            "flamethrower-server",
            src=os.path.join(self.source_folder, "etc", "init.d"),
            dst=initdir,
            keep_path=False,
        )
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "HOWTO", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        for filename in ("Flamethrower.pm",):
            replace_in_file(self, os.path.join(libdir, filename), "INS_VERSION", self.version)

        for tool in ("flamethrower", "flamethrowerd"):
            real_tool = os.path.join(libexec_bindir, tool)
            replace_in_file(self, real_tool, "INS_VERSION", self.version)
            os.chmod(real_tool, os.stat(real_tool).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            self._write_wrapper(os.path.join(bindir, tool), tool)

        os.chmod(os.path.join(initdir, "flamethrower-server"), 0o755)

    def _write_wrapper(self, path, tool):
        script = (
            "#!/usr/bin/env sh\n"
            "case \"$0\" in\n"
            "  */*) self=$0 ;;\n"
            "  *) self=$(command -v \"$0\") || exit 127 ;;\n"
            "esac\n"
            "here=$(CDPATH= cd \"$(dirname \"$self\")\" && pwd) || exit 1\n"
            "prefix=$(dirname \"$here\")\n"
            "libdir=\"$prefix/lib/flamethrower\"\n"
            "export FLAMETHROWER_LIBDIR=\"$libdir\"\n"
            "if [ -n \"${PERL5LIB:-}\" ]; then\n"
            "  export PERL5LIB=\"$libdir:$PERL5LIB\"\n"
            "else\n"
            "  export PERL5LIB=\"$libdir\"\n"
            "fi\n"
            f"exec perl \"$prefix/libexec/flamethrower/bin/{tool}\" \"$@\"\n"
        )
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc", "libexec"]

        libdir = os.path.join(self.package_folder, "lib", "flamethrower")
        self.runenv_info.prepend_path("PERL5LIB", libdir)
        self.runenv_info.define_path("FLAMETHROWER_LIBDIR", libdir)
