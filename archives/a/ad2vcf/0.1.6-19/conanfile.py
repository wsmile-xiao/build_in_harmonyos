#!/usr/bin/env python3
"""Conan recipe for ad2vcf 0.1.6-19."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class Ad2vcfConan(ConanFile):
    name = "ad2vcf"
    version = "0.1.6-19"
    description = "Adds allelic depth information from SAM input to a single-sample VCF"
    license = "BSD-2-Clause"
    homepage = "https://github.com/auerlab/ad2vcf"
    url = "https://github.com/auerlab/ad2vcf"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        self.requires("biolibc/0.2.7")
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
        env.vars(self).save_script("ad2vcf_build")

    @staticmethod
    def _quote(value):
        text = str(value)
        return f'"{text}"' if " " in text else text

    @staticmethod
    def _make():
        return "make"

    def _tool(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = compilers.get(key, fallback)
        if isinstance(value, (list, tuple)):
            value = " ".join(str(part) for part in value)
        return self._resolve_tool(str(value), fallback)

    @staticmethod
    def _resolve_tool(candidate, fallback):
        if candidate and os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate.replace("\\", "/")
        lookup = os.path.basename(candidate) if candidate and os.path.isabs(candidate) else candidate
        found = shutil.which(lookup or fallback)
        if found:
            return found.replace("\\", "/")
        return fallback.replace("\\", "/")

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list) or []
        return [str(value) for value in values]

    def _write_compat_headers(self):
        compat_dir = os.path.join(self.build_folder, "compat")
        sys_dir = os.path.join(compat_dir, "sys")
        os.makedirs(sys_dir, exist_ok=True)
        sysexits_h = os.path.join(compat_dir, "sysexits.h")
        with open(sysexits_h, "w", encoding="ascii") as header:
            header.write(
                "#ifndef CONAN_AD2VCF_COMPAT_SYSEXITS_H\n"
                "#define CONAN_AD2VCF_COMPAT_SYSEXITS_H\n"
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
        param_h = os.path.join(sys_dir, "param.h")
        with open(param_h, "w", encoding="ascii") as header:
            header.write(
                "#ifndef CONAN_AD2VCF_COMPAT_SYS_PARAM_H\n"
                "#define CONAN_AD2VCF_COMPAT_SYS_PARAM_H\n"
                "#ifndef MIN\n"
                "#define MIN(a, b) ((a) < (b) ? (a) : (b))\n"
                "#endif\n"
                "#ifndef MAX\n"
                "#define MAX(a, b) ((a) > (b) ? (a) : (b))\n"
                "#endif\n"
                "#endif\n"
            )
        return compat_dir.replace("\\", "/")

    def _dependency_flags(self):
        cflags = []
        ldflags = []
        for name in ("biolibc", "libxtend"):
            cpp_info = self.dependencies[name].cpp_info
            cflags.extend(f"-isystem {path.replace('\\', '/')}" for path in cpp_info.includedirs)
            cflags.extend(f"-D{define}" for define in cpp_info.defines)
            ldflags.extend(f"-L{path.replace('\\', '/')}" for path in cpp_info.libdirs)
            ldflags.extend(f"-l{lib}" for lib in cpp_info.libs)
        return cflags, ldflags

    def _write_make_dependencies(self):
        with open(os.path.join(self.source_folder, "Makefile.depend"), "w", encoding="ascii") as makefile:
            makefile.write(
                "ad2vcf.o: ad2vcf.c ad2vcf.h ad2vcf-protos.h\n"
                "\t${CC} -c ${CFLAGS} ad2vcf.c\n\n"
            )

    def _sign_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = self._resolve_tool(os.environ.get("BINARY_SIGN_TOOL"), "binary-sign-tool")
        objcopy = self._resolve_tool(os.environ.get("LLVM_OBJCOPY"), "llvm-objcopy")
        if not os.path.exists(sign_tool):
            raise ConanInvalidConfiguration("OHOS binary-sign-tool is required to sign ad2vcf")
        if os.path.exists(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true', quiet=True)
        tmp_signed = path + ".signed"
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{tmp_signed}" -selfSign 1', quiet=True)
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def _run_positive_fixture(self):
        if not can_run(self):
            self.output.info("Skipping upstream positive fixture because target binaries cannot run")
            return
        command = (
            "rm -f test-ad.vcf && "
            "../ad2vcf test.vcf 10 < test.sam && "
            "diff -u test-ad-correct.vcf test-ad.vcf"
        )
        self.run(command, cwd=os.path.join(self.source_folder, "Test"), env=["conanbuild", "ad2vcf_build"])

    def build(self):
        self._write_make_dependencies()
        dep_cflags, dep_ldflags = self._dependency_flags()
        cflags = [
            f"-I{self._write_compat_headers()}",
            "-DVERSION='\\\"0.1.6\\\"'",
            "-O2",
            "-DNDEBUG",
        ]
        cflags.extend(self._conf_flags("tools.build:cflags"))
        cflags.extend(dep_cflags)
        ldflags = list(dep_ldflags)
        ldflags.extend(self._conf_flags("tools.build:exelinkflags"))
        if str(self.settings.os) == "OHOS":
            cflags.extend(["-fPIE", "-Dstrlcpy=xt_strlcpy", "-Dstrlcat=xt_strlcat"])
            ldflags.insert(0, "-pie")

        assignments = {
            "CC": self._tool("c", "clang"),
            "LD": self._tool("c", "clang"),
            "CFLAGS": " ".join(cflags),
            "LDFLAGS": " ".join(ldflags),
        }
        args = " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())
        self.run(f"{self._make()} -j1 {args} ad2vcf", cwd=self.source_folder, env=["conanbuild", "ad2vcf_build"])
        self._sign_binary(os.path.join(self.source_folder, "ad2vcf"))
        self._run_positive_fixture()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "ad2vcf"), keep_path=False)
        copy(self, "ad2vcf", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "ad2vcf.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        test_src = os.path.join(self.source_folder, "Test")
        test_dst = os.path.join(self.package_folder, "share", "ad2vcf", "Test")
        for fixture in ("test.vcf", "test.sam", "test-ad-correct.vcf"):
            copy(self, fixture, test_src, test_dst, keep_path=False)
        self._sign_binary(os.path.join(self.package_folder, "bin", "ad2vcf"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
