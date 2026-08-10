#!/usr/bin/env python3
"""Conan recipe for biolibc 0.2.7."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class BiolibcConan(ConanFile):
    name = "biolibc"
    version = "0.2.7"
    description = "C library for bioinformatics file formats and helper routines"
    license = "BSD-2-Clause"
    homepage = "https://github.com/auerlab/biolibc"
    url = "https://github.com/auerlab/biolibc"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        self.requires("libxtend/0.2.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        env.define("TMPDIR", tmp_dir)
        env.vars(self).save_script("biolibc_build")

    @staticmethod
    def _quote(value):
        text = str(value).replace("\\", "/")
        return f'"{text}"' if " " in text else text

    @staticmethod
    def _make():
        return "make"

    def _tool(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = compilers.get(key, fallback)
        if isinstance(value, (list, tuple)):
            value = " ".join(str(part) for part in value)
        candidate = str(value)
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate.replace("\\", "/")
        lookup = os.path.basename(candidate) if os.path.isabs(candidate) else candidate
        found = shutil.which(lookup)
        return (found or fallback).replace("\\", "/")

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list) or []
        return [str(value) for value in values]

    def _write_compat_headers(self):
        compat_dir = os.path.join(self.build_folder, "compat")
        os.makedirs(compat_dir, exist_ok=True)
        sysexits_h = os.path.join(compat_dir, "sysexits.h")
        with open(sysexits_h, "w", encoding="ascii") as header:
            header.write(
                "#ifndef CONAN_BIOLIBC_COMPAT_SYSEXITS_H\n"
                "#define CONAN_BIOLIBC_COMPAT_SYSEXITS_H\n"
                "#define EX_OK 0\n"
                "#define EX_USAGE 64\n"
                "#define EX_DATAERR 65\n"
                "#define EX_NOINPUT 66\n"
                "#define EX_NOUSER 67\n"
                "#define EX_NOHOST 68\n"
                "#define EX_UNAVAILABLE 69\n"
                "#define EX_SOFTWARE 70\n"
                "#define EX_OSERR 71\n"
                "#define EX_OSFILE 72\n"
                "#define EX_CANTCREAT 73\n"
                "#define EX_IOERR 74\n"
                "#define EX_TEMPFAIL 75\n"
                "#define EX_PROTOCOL 76\n"
                "#define EX_NOPERM 77\n"
                "#define EX_CONFIG 78\n"
                "#endif\n"
            )
        tmpfile_h = os.path.join(compat_dir, "ohos_tmpfile.h")
        with open(tmpfile_h, "w", encoding="ascii") as header:
            header.write(
                "#ifndef CONAN_BIOLIBC_COMPAT_OHOS_TMPFILE_H\n"
                "#define CONAN_BIOLIBC_COMPAT_OHOS_TMPFILE_H\n"
                "#include <errno.h>\n"
                "#include <limits.h>\n"
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <string.h>\n"
                "#include <unistd.h>\n"
                "static FILE *conan_biolibc_tmpfile(void)\n"
                "{\n"
                "    const char *dir = getenv(\"TMPDIR\");\n"
                "    char path[PATH_MAX];\n"
                "    int fd;\n"
                "    FILE *stream;\n"
                "    if ((dir == NULL) || (dir[0] == '\\0'))\n"
                "        dir = getenv(\"TMP\");\n"
                "    if ((dir == NULL) || (dir[0] == '\\0'))\n"
                "        dir = getenv(\"TEMP\");\n"
                "    if ((dir == NULL) || (dir[0] == '\\0'))\n"
                "        dir = \".\";\n"
                "    if (snprintf(path, sizeof(path), \"%s/biolibc-XXXXXX\", dir) >= (int)sizeof(path)) {\n"
                "        errno = ENAMETOOLONG;\n"
                "        return NULL;\n"
                "    }\n"
                "    fd = mkstemp(path);\n"
                "    if (fd == -1)\n"
                "        return NULL;\n"
                "    unlink(path);\n"
                "    stream = fdopen(fd, \"w+\");\n"
                "    if (stream == NULL)\n"
                "        close(fd);\n"
                "    return stream;\n"
                "}\n"
                "#define tmpfile conan_biolibc_tmpfile\n"
                "#endif\n"
            )
        return compat_dir.replace("\\", "/")

    def _dependency_cflags(self):
        flags = []
        for dep in self.dependencies.host.values():
            cpp_info = dep.cpp_info
            flags.extend(f"-isystem {path.replace('\\', '/')}" for path in cpp_info.includedirs)
            flags.extend(f"-D{define}" for define in cpp_info.defines)
        return flags

    def _dependency_ldflags(self):
        flags = []
        for dep in self.dependencies.host.values():
            cpp_info = dep.cpp_info
            flags.extend(f"-L{path.replace('\\', '/')}" for path in cpp_info.libdirs)
            flags.extend(f"-l{lib}" for lib in cpp_info.libs)
        return flags

    def _run_upstream_tests(self, cc, cflags):
        if not can_run(self):
            self.output.info("Skipping biolibc upstream tests because target binaries cannot run")
            return

        source_dir = self.source_folder.replace("\\", "/")
        test_include_dir = os.path.join(self.build_folder, "test-include").replace("\\", "/")
        copy(self, "*.h", self.source_folder, os.path.join(test_include_dir, "biolibc"), keep_path=False)
        test_cflags = [f"-I{source_dir}", f"-I{test_include_dir}"]
        test_cflags.extend(cflags)
        cflags_text = " ".join(test_cflags)
        ldflags = [f"-L{source_dir}", "-lbiolibc"]
        ldflags.extend(self._dependency_ldflags())
        ldflags.extend(self._conf_flags("tools.build:exelinkflags"))
        ldflags_text = " ".join(ldflags)

        gff_test = os.path.join(self.source_folder, "GFF-test", "gff-test.c")
        for old, new in (
            ('#include "gff.h"', '#include "gff3.h"'),
            ("bl_gff_t", "bl_gff3_t"),
            ("BL_GFF_", "BL_GFF3_"),
            ("bl_gff_", "bl_gff3_"),
            (
                "    int         ch;\n    \n    tmpfile = bl_gff3_skip_header(stdin);",
                "    int         ch;\n\n    bl_gff3_init(&gff_feature);\n    tmpfile = bl_gff3_skip_header(stdin);",
            ),
            (
                "    }\n    return EX_OK;",
                "    }\n    bl_gff3_free(&gff_feature);\n    return EX_OK;",
            ),
        ):
            replace_in_file(self, gff_test, old, new, strict=False)

        cases = [
            (
                "Bed-test",
                "bed-test.c",
                "bed-test",
                "rm -f out.bed && ./bed-test < good.bed > out.bed && diff good.bed out.bed",
            ),
            (
                "Fasta-test",
                "fasta-test.c",
                "fasta-test",
                "rm -f out.fasta && ./fasta-test < test.fasta > out.fasta && diff test.fasta out.fasta",
            ),
            (
                "Fastq-test",
                "fastq-test.c",
                "fastq-test",
                "rm -f out.fastq && "
                "./fastq-test 0 < correct.fastq > out.fastq && diff correct.fastq out.fastq && "
                "./fastq-test 20 < low-qual.fastq > out.fastq && diff low-qual-correct.fastq out.fastq",
            ),
            (
                "GFF-test",
                "gff-test.c",
                "gff-test",
                "rm -f out.gff3 && ./gff-test < good.gff3 > out.gff3 && diff good.gff3 out.gff3",
            ),
            (
                "ORF-test",
                "orf-test.c",
                "orf-test",
                "rm -f out.txt && ./orf-test < orf.txt > out.txt && diff correct.txt out.txt",
            ),
        ]
        for directory, source, exe, command in cases:
            test_dir = os.path.join(self.source_folder, directory)
            self.output.info(f"Running biolibc upstream {directory}/test.sh equivalent")
            self.run(
                f"{cc} {cflags_text} -o {exe} {source} {ldflags_text}",
                cwd=test_dir,
                env=["conanbuild", "biolibc_build"],
            )
            self.run(command, cwd=test_dir, env=["conanbuild", "biolibc_build"])

    def build(self):
        cflags = [f"-I{self._write_compat_headers()}", "-O2", "-DNDEBUG"]
        cflags.extend(self._conf_flags("tools.build:cflags"))
        cflags.extend(self._dependency_cflags())
        if str(self.settings.os) == "OHOS":
            compat_tmpfile = os.path.join(self.build_folder, "compat", "ohos_tmpfile.h").replace("\\", "/")
            cflags.extend([f"-include {compat_tmpfile}", "-Dstrlcpy=xt_strlcpy", "-Dstrlcat=xt_strlcat"])
        if self.options.fPIC:
            cflags.append("-fPIC")

        assignments = {
            "CC": self._tool("c", "clang"),
            "AR": "llvm-ar" if str(self.settings.os) == "OHOS" else "ar",
            "RANLIB": "llvm-ranlib" if str(self.settings.os) == "OHOS" else "ranlib",
            "CFLAGS": " ".join(cflags),
        }
        args = " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())
        self.run("rm -f *.o libbiolibc.a", cwd=self.source_folder)
        self.run(f"{self._make()} -j1 {args} libbiolibc.a", cwd=self.source_folder, env=["conanbuild", "biolibc_build"])
        self._run_upstream_tests(assignments["CC"], cflags)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "libbiolibc.a", self.source_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include", "biolibc"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["biolibc"]
        self.cpp_info.requires = ["libxtend::libxtend"]
        self.cpp_info.set_property("cmake_file_name", "biolibc")
        self.cpp_info.set_property("cmake_target_name", "biolibc::biolibc")
        self.cpp_info.set_property("pkg_config_name", "biolibc")
