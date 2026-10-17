#!/usr/bin/env python3
"""Conan recipe for libxtend 0.2.1."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class LibxtendConan(ConanFile):
    name = "libxtend"
    version = "0.2.1"
    description = "Portable C utility library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/outpaddling/libxtend"
    url = "https://github.com/outpaddling/libxtend"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tools_dir = os.path.join(self.build_folder, "test-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for tool_name in ("zcat", "gzcat"):
            tool_path = os.path.join(tools_dir, tool_name)
            with open(tool_path, "w", encoding="ascii") as script:
                script.write("#!/bin/sh\nexec gzip -dc \"$@\"\n")
            os.chmod(tool_path, 0o755)
        env = Environment()
        if os.name == "nt":
            env.prepend_path("PATH", "E:/Git/usr/bin")
            env.prepend_path("PATH", "E:/mingw64/bin")
        env.prepend_path("PATH", tools_dir)
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        env.define("TMPDIR", tmp_dir)
        env.vars(self).save_script("libxtend_build")

    @staticmethod
    def _quote(value):
        text = str(value).replace("\\", "/")
        return f'"{text}"' if " " in text else text

    def _make(self):
        if os.name == "nt":
            candidate = "E:/mingw64/bin/mingw32-make.exe"
            return candidate if os.path.exists(candidate) else "mingw32-make"
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
                "#ifndef CONAN_LIBXTEND_COMPAT_SYSEXITS_H\n"
                "#define CONAN_LIBXTEND_COMPAT_SYSEXITS_H\n"
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
        return compat_dir.replace("\\", "/")

    def _patch_ohos_sources(self):
        if str(self.settings.os) != "OHOS":
            return
        replace_in_file(
            self,
            os.path.join(self.source_folder, "fast-file.c"),
            'snprintf(cmd, XT_CMD_MAX_CHARS, "zcat %s", filename);',
            'snprintf(cmd, XT_CMD_MAX_CHARS, "gzip -dc %s", filename);',
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "fast-file.c"),
            "stream->disk_block_size = st.st_blksize;",
            "stream->disk_block_size = (st.st_blksize > 0) ? st.st_blksize : 32768;",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "fast-file.c"),
            "if ( (stream->bytes_read = read(stream->fd, stream->start_ptr,\n\t\t\t\t    stream->disk_block_size)) == 0 )",
            "if ( (stream->bytes_read = read(stream->fd, stream->start_ptr,\n\t\t\t\t    stream->disk_block_size)) <= 0 )",
            strict=False,
        )

    def _run_upstream_tests(self, cc, cflags):
        if not can_run(self):
            self.output.info("Skipping libxtend upstream tests because target binaries cannot run")
            return

        test_cflags = list(cflags)
        if str(self.settings.os) == "OHOS":
            test_cflags.extend(["-Dstrlcpy=xt_strlcpy", "-Dstrlcat=xt_strlcat"])
        cflags_text = " ".join(test_cflags)
        source_dir = self.source_folder.replace("\\", "/")
        ldflags = f"-L{source_dir} -lxtend"
        exelinkflags = " ".join(self._conf_flags("tools.build:exelinkflags"))

        test_dir = os.path.join(self.source_folder, "Test")
        fast_file_dir = os.path.join(test_dir, "Fast-file")

        self.output.info("Running libxtend upstream Test/main-test.c")
        self.run(
            f"{cc} {cflags_text} -o main-test main-test.c {ldflags} {exelinkflags}",
            cwd=test_dir,
            env=["conanbuild", "libxtend_build"],
        )
        self.run("./main-test", cwd=test_dir, env=["conanbuild", "libxtend_build"])

        # The upstream script hard-codes /tmp and includes interactive/download
        # throughput checks.  Keep the automated assertions local to the build dir.
        replace_in_file(
            self,
            os.path.join(fast_file_dir, "hl-test.c"),
            'template[] = "/tmp/temp.XXXXXX"',
            'template[] = "temp.XXXXXX"',
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(fast_file_dir, "hl-test.c"),
            "    xt_ff_read(infile, string, 1, strlen(TWO_LINE));\n"
            "    xt_ff_close(infile);",
            "    xt_ff_read(infile, string, 1, strlen(TWO_LINE));\n"
            "    string[strlen(TWO_LINE)] = '\\0';\n"
            "    xt_ff_close(infile);",
            strict=False,
        )
        self.output.info("Running libxtend upstream Fast-file automated checks")
        tools_dir = os.path.join(self.build_folder, "test-tools").replace("\\", "/")
        for source, exe in (("iotest-ffile.c", "iotest-ffile"), ("hl-test.c", "hl-test")):
            self.run(
                f"{cc} {cflags_text} -Wno-implicit-function-declaration "
                f"-o {exe} {source} {ldflags} {exelinkflags}",
                cwd=fast_file_dir,
                env=["conanbuild", "libxtend_build"],
            )
        self.run(
            f"PATH={self._quote(tools_dir)}:$PATH && export PATH && "
            "rm -f temp.sh temp.sh.gz temp.sh.copy temp-write-output temp-read-output && "
            "./iotest-ffile test.sh temp.sh.copy && diff test.sh temp.sh.copy && "
            "./iotest-ffile test.sh temp.sh.gz && ./iotest-ffile temp.sh.gz temp.sh && diff test.sh temp.sh && "
            "./hl-test",
            cwd=fast_file_dir,
            env=["conanbuild", "libxtend_build"],
        )

    def build(self):
        self._patch_ohos_sources()
        compat_dir = self._write_compat_headers()
        cflags = [f"-I{compat_dir}", "-O2", "-DNDEBUG", "-DLIBXTEND_LIBRARY_BUILD"]
        cflags.extend(self._conf_flags("tools.build:cflags"))
        if self.options.fPIC:
            cflags.append("-fPIC")
        assignments = {
            "CC": self._tool("c", "clang"),
            "AR": "llvm-ar" if str(self.settings.os) == "OHOS" else "ar",
            "RANLIB": "llvm-ranlib" if str(self.settings.os) == "OHOS" else "ranlib",
            "CFLAGS": " ".join(cflags),
        }
        args = " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())
        self.run("rm -f *.o libxtend.a", cwd=self.source_folder)
        self.run(f"{self._make()} -j1 {args} libxtend.a", cwd=self.source_folder, env=["conanbuild", "libxtend_build"])
        self._run_upstream_tests(assignments["CC"], cflags)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "libxtend.a", self.source_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include", "xtend"), keep_path=False)
        private_header = os.path.join(self.package_folder, "include", "xtend", "dsv-private.h")
        if os.path.exists(private_header):
            os.remove(private_header)

    def package_info(self):
        self.cpp_info.libs = ["xtend"]
        if str(self.settings.os) == "OHOS":
            self.cpp_info.defines = ["strlcpy=xt_strlcpy", "strlcat=xt_strlcat"]
        self.cpp_info.set_property("cmake_file_name", "libxtend")
        self.cpp_info.set_property("cmake_target_name", "libxtend::libxtend")
