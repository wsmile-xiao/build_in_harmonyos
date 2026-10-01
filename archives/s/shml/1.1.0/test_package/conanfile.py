#!/usr/bin/env python3
"""shml consumer test (rule12 flow): the packaged Bash library is sourced by bash, its
ANSI output becomes the input of an OHOS aarch64 static C program that is compiled with
the profile's clang and executed (natively on aarch64, through qemu-aarch64 otherwise)."""
import os
import platform
import shlex
import shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout

# Exercises the colour, attribute, element and icon APIs of the packaged library.
DRIVER = r"""source "$1"
fgcolor red 'OHOS PC'; printf ' '
bgcolor blue 'qemu'; printf ' '
attribute bold 'B'; printf ' '
hr '*' 4; printf ' '
icon check
"""


def _find_bash():
    found = shutil.which("bash")
    if found:
        return found
    for candidate in ("/data/service/hnp/bin/bash", "/bin/bash"):
        if os.path.isfile(candidate):
            return candidate
    raise ConanException("bash is required to consume shml")


class ShmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0], "shml", "shml.sh")
        transcript = os.path.join(self.build_folder, "shml_output.bin")
        # Redirect in the shell so the escape bytes reach the file untouched.
        self.run(f"{shlex.quote(_find_bash())} -c {shlex.quote(DRIVER)} shml-consumer "
                 f"{shlex.quote(script)} > {shlex.quote(transcript)}")
        with open(transcript, "rb") as f:
            data = f.read()
        if not data:
            raise ConanException("packaged shml.sh produced no output")
        with open(os.path.join(self.build_folder, "shml_output.h"), "w",
                  encoding="ascii") as f:
            f.write("#include <stddef.h>\n"
                    "static const unsigned char shml_output[] = {"
                    + ", ".join(str(b) for b in data) + "};\n"
                    "static const size_t shml_output_len = sizeof(shml_output);\n")
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") or shutil.which("clang")
        if not cc:
            raise ConanException("no C compiler configured for the OHOS profile")
        self.run(" ".join(shlex.quote(x) for x in [
            cc, "-static", "-Wall", "-Werror", "-I", self.build_folder,
            os.path.join(self.recipe_folder, "consumer.c"),
            "-o", os.path.join(self.build_folder, "shml_consumer")]))

    def test(self):
        exe = shlex.quote(os.path.join(self.build_folder, "shml_consumer"))
        if platform.machine().lower() not in ("aarch64", "arm64"):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanException("qemu-aarch64 is required to run the OHOS aarch64 "
                                     "consumer on a non-aarch64 host")
            exe = f"{shlex.quote(qemu)} {exe}"
        self.run(exe, env="conanrun")

        # runenv_info exported by the package must locate the script, which reports its version.
        # tested_reference_str is "shml/1.1.0@user/channel" or "shml/1.1.0#<recipe revision>"
        # depending on how `conan create` was invoked, so take the version from the ref object.
        version = str(self.dependencies[self.tested_reference_str].ref.version)
        self.output.info(f"tested reference: {self.tested_reference_str} (version {version})")
        out = StringIO()
        self.run(f'{shlex.quote(_find_bash())} "$SHML_SCRIPT" -v', env="conanrun", stdout=out)
        reported = out.getvalue().strip()
        self.output.info(f"shml -v via SHML_SCRIPT: {reported}")
        if reported != f"shml version {version}":
            raise ConanException(f"unexpected shml -v output: {reported!r}")
