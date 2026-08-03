#!/usr/bin/env python3
"""Conan recipe for sisc-scheme 1.16.6.

SISC Lite is a prebuilt JVM distribution: a shell launcher, sisc.jar,
and a heap image. There is no configure or compile step.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SiscSchemeConan(ConanFile):
    name = "sisc-scheme"
    version = "1.16.6"
    description = "Extensible Java based Scheme interpreter"
    license = "MPL-1.1 OR GPL-2.0-or-later"
    homepage = "https://sisc-scheme.org/"
    url = "https://downloads.sourceforge.net/project/sisc/"
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def system_requirements(self):
        if not shutil.which("java"):
            self.output.warning(
                "sisc-scheme requires a JVM at runtime. "
                "Install bishengjdk 17.0.13 on OHOS if java is not in PATH."
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "sisc-scheme")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        for filename in (
            "sisc",
            "sisc.jar",
            "sisc.shp",
            "COPYING",
            "README",
            "ChangeLog",
            "GOALS",
            "TODO",
        ):
            copy(self, filename, src=self.source_folder, dst=libexec, keep_path=False)

        real_launcher = os.path.join(libexec, "sisc")
        if os.path.exists(real_launcher):
            os.chmod(real_launcher, 0o755)

        if str(self.settings.os) == "OHOS":
            bash_path = (
                shutil.which("bash")
                or os.environ.get("CONFIG_SHELL")
                or "/storage/Users/currentUser/usr/local/bin/bash"
            )
            shebang = f"#!{bash_path}"
        else:
            shebang = "#!/usr/bin/env bash"

        wrapper = os.path.join(bindir, "sisc")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{shebang}\n")
            f.write("set -e\n")
            f.write("case \"$0\" in\n")
            f.write("  */*) wrapper_path=$0 ;;\n")
            f.write("  *) wrapper_path=$(command -v \"$0\") || exit 127 ;;\n")
            f.write("esac\n")
            f.write("case \"$wrapper_path\" in\n")
            f.write("  */*) script_dir=${wrapper_path%/*} ;;\n")
            f.write("  *) script_dir=. ;;\n")
            f.write("esac\n")
            f.write("script_dir=$(CDPATH= cd -- \"$script_dir\" && pwd)\n")
            f.write("SISC_HOME=${SISC_HOME:-\"$script_dir/../libexec/sisc-scheme\"}\n")
            f.write("JAVA_BIN=${JAVA:-java}\n")
            f.write("classpath=\"$SISC_HOME/sisc.jar\"\n")
            f.write("if [ -n \"${CLASSPATH:-}\" ]; then\n")
            f.write("  classpath=\"$classpath:$CLASSPATH\"\n")
            f.write("fi\n")
            f.write(
                "exec \"$JAVA_BIN\" ${JAVAOPT:-} -classpath \"$classpath\" "
                "-Dsisc.home=\"$SISC_HOME\" sisc.REPL -h \"$SISC_HOME/sisc.shp\" \"$@\"\n"
            )
        os.chmod(wrapper, 0o755)

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        home = os.path.join(self.package_folder, "libexec", "sisc-scheme")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define("SISC_HOME", home)
