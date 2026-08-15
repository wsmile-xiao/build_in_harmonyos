#!/usr/bin/env python3
"""Conan recipe for V 0.5.2.

V is a self-hosted programming language compiler. Upstream bootstraps the
compiler from the external vlang/vc repository, then rebuilds V with V itself.
This recipe vendors the vc C bootstrap source during source() so OHOS CI does
not clone from the network during build().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

class VConan(ConanFile):
    name = "vlang"
    version = "0.5.2"
    description = "Simple, fast, safe, compiled programming language"
    license = "MIT"
    homepage = "https://vlang.io"
    url = "https://github.com/vlang/v"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        vc_tmp = os.path.join(self.source_folder, "_vc_src")
        get(
            self,
            **self.conan_data["vc_sources"],
            destination=vc_tmp,
            strip_root=True,
        )
        vc_dir = os.path.join(self.source_folder, "vc")
        os.makedirs(vc_dir, exist_ok=True)
        copy(self, "v.c", src=vc_tmp, dst=vc_dir)
        copy(self, "v_win.c", src=vc_tmp, dst=vc_dir)
        shutil.rmtree(vc_tmp)

        makefile = os.path.join(self.source_folder, "Makefile")
        self._replace_required_once(
            makefile,
            "LDFLAGS ?=\n\nall:",
            "LDFLAGS ?=\nOHOS_SIGN_TOOL ?=\nVCFILE ?= v.c\nEXE_EXT ?=\n\nall:",
        )
        self._replace_required_once(
            makefile, "-o v1 vc/v.c", "-o v1$(EXE_EXT) vc/$(VCFILE)"
        )
        self._replace_required_once(
            makefile, "set -- ./v1 -no-parallel", "set -- ./v1$(EXE_EXT) -no-parallel"
        )
        self._replace_required_once(makefile, "set -- ./v2 -o v", "set -- ./v2$(EXE_EXT) -o v$(EXE_EXT)")
        self._replace_required_once(makefile, "rm -rf v1 v2;", "rm -rf v1$(EXE_EXT) v2$(EXE_EXT);")
        self._replace_required_alternative(
            makefile,
            [
                (
                    "./v run ./cmd/tools/detect_tcc.v;",
                    "if [ -z \"$(OHOS_SIGN_TOOL)\" ]; then ./v$(EXE_EXT) $$bootstrap_gcflags run ./cmd/tools/detect_tcc.v; fi;",
                ),
                (
                    "./v$(EXE_EXT) $$bootstrap_gcflags run ./cmd/tools/detect_tcc.v;",
                    "if [ -z \"$(OHOS_SIGN_TOOL)\" ]; then ./v$(EXE_EXT) $$bootstrap_gcflags run ./cmd/tools/detect_tcc.v; fi;",
                ),
            ],
        )
        self._replace_required_once(makefile, "./v version;", "./v$(EXE_EXT) version;")
        self._replace_required_alternative(
            makefile,
            [
                (
                    "./v run .github/problem-matchers/register_all.vsh",
                    "if [ -z \"$(OHOS_SIGN_TOOL)\" ]; then ./v$(EXE_EXT) $$bootstrap_gcflags run .github/problem-matchers/register_all.vsh; fi",
                ),
                (
                    "./v$(EXE_EXT) $$bootstrap_gcflags run .github/problem-matchers/register_all.vsh",
                    "if [ -z \"$(OHOS_SIGN_TOOL)\" ]; then ./v$(EXE_EXT) $$bootstrap_gcflags run .github/problem-matchers/register_all.vsh; fi",
                ),
            ],
        )
        self._replace_required_once(
            makefile,
            "$(CC) $$bootstrap_ccflags -std=gnu11 -w -o v1$(EXE_EXT) vc/$(VCFILE) -lm -lpthread $$ldflags || cmd/tools/cc_compilation_failed_non_windows.sh; \\",
            "$(CC) $$bootstrap_ccflags -std=gnu11 -w -o v1$(EXE_EXT) vc/$(VCFILE) -lm -lpthread $$ldflags || cmd/tools/cc_compilation_failed_non_windows.sh; \\\n"
            "\tif [ -n \"$(OHOS_SIGN_TOOL)\" ]; then $(OHOS_SIGN_TOOL) sign -inFile v1$(EXE_EXT) -outFile v1$(EXE_EXT).signed -selfSign 1 -signAlg SHA256withECDSA; mv v1$(EXE_EXT).signed v1$(EXE_EXT); chmod +x v1$(EXE_EXT); fi; \\",
        )
        self._replace_required_once(
            makefile,
            "\t\"$$@\"; \\\n\tset -- ./v2$(EXE_EXT) -o v$(EXE_EXT) $$bootstrap_gcflags $(VFLAGS); \\",
            "\t\"$$@\"; \\\n"
            "\tif [ -n \"$(OHOS_SIGN_TOOL)\" ]; then $(OHOS_SIGN_TOOL) sign -inFile v2$(EXE_EXT) -outFile v2$(EXE_EXT).signed -selfSign 1 -signAlg SHA256withECDSA; mv v2$(EXE_EXT).signed v2$(EXE_EXT); chmod +x v2$(EXE_EXT); fi; \\\n"
            "\tset -- ./v2$(EXE_EXT) -o v$(EXE_EXT) $$bootstrap_gcflags $(VFLAGS); \\",
        )
        self._replace_required_once(
            makefile,
            "\t\"$$@\"; \\\n\trm -rf v1$(EXE_EXT) v2$(EXE_EXT); \\",
            "\t\"$$@\"; \\\n"
            "\tif [ -n \"$(OHOS_SIGN_TOOL)\" ]; then $(OHOS_SIGN_TOOL) sign -inFile v$(EXE_EXT) -outFile v$(EXE_EXT).signed -selfSign 1 -signAlg SHA256withECDSA; mv v$(EXE_EXT).signed v$(EXE_EXT); chmod +x v$(EXE_EXT); fi; \\\n"
            "\trm -rf v1$(EXE_EXT) v2$(EXE_EXT); \\",
        )
        for vc_file in ["v.c", "v_win.c"]:
            self._replace_optional_alternative(
                os.path.join(vc_dir, vc_file),
                [
                    (
                        "V_CRT_LINKAGE void * V_CRT_CALL _aligned_malloc(size_t size, size_t alignment);\n"
                        "V_CRT_LINKAGE void * V_CRT_CALL _aligned_realloc(void *memory, size_t size, size_t alignment);\n"
                        "V_CRT_LINKAGE void V_CRT_CALL _aligned_free(void *memory);",
                        "#if !((defined(__MINGW32__) || defined(__MINGW64__)) && defined(__V_GCC__))\n"
                        "V_CRT_LINKAGE void * V_CRT_CALL _aligned_malloc(size_t size, size_t alignment);\n"
                        "V_CRT_LINKAGE void * V_CRT_CALL _aligned_realloc(void *memory, size_t size, size_t alignment);\n"
                        "V_CRT_LINKAGE void V_CRT_CALL _aligned_free(void *memory);\n"
                        "#endif",
                    ),
                ],
            )
        self._replace_required_once(
            os.path.join(self.source_folder, "vlib", "v", "gen", "c", "cheaders.v"),
            "V_CRT_LINKAGE void * V_CRT_CALL _aligned_malloc(size_t size, size_t alignment);\n"
            "V_CRT_LINKAGE void * V_CRT_CALL _aligned_realloc(void *memory, size_t size, size_t alignment);\n"
            "V_CRT_LINKAGE void V_CRT_CALL _aligned_free(void *memory);",
            "#if !((defined(__MINGW32__) || defined(__MINGW64__)) && defined(__V_GCC__))\n"
            "V_CRT_LINKAGE void * V_CRT_CALL _aligned_malloc(size_t size, size_t alignment);\n"
            "V_CRT_LINKAGE void * V_CRT_CALL _aligned_realloc(void *memory, size_t size, size_t alignment);\n"
            "V_CRT_LINKAGE void V_CRT_CALL _aligned_free(void *memory);\n"
            "#endif",
        )

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        make_program = self.conf.get("tools.gnu:make_program", default=None)
        if not make_program:
            make_program = (
                self._ohos_tool_path("make")
                if str(self.settings.os) == "OHOS"
                else "make"
            )
        is_windows = str(self.settings.os) == "Windows"
        vc_file = "v_win.c" if is_windows else "v.c"
        exe_ext = ".exe" if is_windows else ""
        shell_arg = ""
        posix_tools_dir = None
        if is_windows:
            make_shell = self._find_posix_shell()
            if not make_shell:
                raise ConanException(
                    "Windows native V bootstrap requires a POSIX sh in PATH "
                    "for the upstream Makefile"
                )
            posix_tools_dir = os.path.dirname(make_shell)
            shell_arg = f' SHELL="{make_shell.replace(os.sep, "/")}"'

        cflags = "-O1 -municode" if is_windows else "-O1"
        ldflags = ""
        sign_tool_arg = ""
        if str(self.settings.os) == "OHOS":
            ldflags = f"-fuse-ld={self._ohos_tool_path('ld.bfd')}"
            sign_tool_arg = f' OHOS_SIGN_TOOL="{self._ohos_sign_tool()}"'

        # Run only the local bootstrap target. The default target tries to clone
        # or pull vlang/vc; source() has already supplied vc/v.c deterministically.
        os.makedirs(os.path.join(self.build_folder, "vmodules"), exist_ok=True)
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        env.define("VMODULES", os.path.join(self.build_folder, "vmodules"))
        env.define("TMPDIR", tmp_dir)
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        if posix_tools_dir:
            env.prepend_path("PATH", posix_tools_dir)
        with env.vars(self).apply():
            self.run(
                f'{make_program} -f Makefile -j1 v{shell_arg} VCFILE="{vc_file}" '
                f'EXE_EXT="{exe_ext}" CC="{cc}" '
                f'CFLAGS="{cflags}" LDFLAGS="{ldflags}" VFLAGS="-cc {cc}"'
                f"{sign_tool_arg}",
                cwd=self.source_folder,
            )

    def package(self):
        root_dir = os.path.join(self.package_folder, "share", "v")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(root_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        for dirname in ["cmd", "thirdparty", "vlib"]:
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, dirname),
                dst=os.path.join(root_dir, dirname),
            )
        for filename in ["LICENSE", "README.md", "TESTS.md", "v.mod"]:
            copy(self, filename, src=self.source_folder, dst=root_dir)

        exe_name = "v.exe" if str(self.settings.os) == "Windows" else "v"
        shutil.copy2(self._find_built_v(), os.path.join(root_dir, exe_name))
        real_v = os.path.join(root_dir, exe_name)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_binary(real_v)

        if str(self.settings.os) == "Windows":
            wrapper = os.path.join(bin_dir, "v.bat")
            with open(wrapper, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(
                    "@echo off\r\n"
                    "set \"bindir=%~dp0\"\r\n"
                    "\"%bindir%..\\share\\v\\v.exe\" %*\r\n"
                )
        else:
            wrapper = os.path.join(bin_dir, "v")
            shell_path = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"
            gc_args = " -gc none" if str(self.settings.os) == "OHOS" else ""
            ohos_tmp_setup = ""
            if str(self.settings.os) == "OHOS":
                ohos_tmp_setup = (
                    'if [ -z "${TMPDIR:-}" ] && [ -z "${TMP:-}" ] && [ -z "${TEMP:-}" ]; then\n'
                    '  tmpdir="${HOME:-$bindir}/.cache/v"\n'
                    '  if mkdir -p "$tmpdir"; then\n'
                    '    export TMPDIR="$tmpdir" TMP="$tmpdir" TEMP="$tmpdir"\n'
                    "  fi\n"
                    "fi\n"
                )
            with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    f"#!{shell_path}\n"
                    "bindir=$(CDPATH= cd \"$(dirname \"$0\")\" && pwd)\n"
                    f"{ohos_tmp_setup}"
                    f"exec \"$bindir/../share/v/v\"{gc_args} \"$@\"\n"
                )
            os.chmod(wrapper, 0o755)
            os.chmod(real_v, 0o755)

    def _sign_ohos_binary(self, binary_path):
        sign_tool = self._ohos_sign_tool()
        signed_path = f"{binary_path}.signed"
        self.run(
            f'{sign_tool} sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1 -signAlg SHA256withECDSA',
            quiet=True,
        )
        if not os.path.isfile(signed_path):
            raise ConanException(f"OHOS binary signing did not create {signed_path}")
        os.replace(signed_path, binary_path)

    def _ohos_sign_tool(self):
        sign_tool = self._ohos_tool_path("binary-sign-tool")
        if not os.path.isfile(sign_tool):
            raise ConanException(f"OHOS binary sign tool not found: {sign_tool}")
        return sign_tool

    def _ohos_tool_path(self, filename):
        tool_dir = self.conf.get("user.ohos:tool_dir", default=None)
        if tool_dir:
            return os.path.join(str(tool_dir), filename)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if cc and os.path.isabs(str(cc)):
            tool_dir = os.path.dirname(str(cc))
            return os.path.join(tool_dir, filename)

        raise ConanException(
            "OHOS tool directory not configured; set user.ohos:tool_dir or "
            "tools.build:compiler_executables['c'] to an absolute OHOS compiler path"
        )

    def _find_built_v(self):
        for filename in ["v.exe", "v"]:
            candidate = os.path.join(self.source_folder, filename)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("V compiler binary was not produced by bootstrap build")

    def _find_posix_shell(self):
        for name in ["sh", "sh.exe"]:
            shell = shutil.which(name)
            if shell:
                return shell
        for candidate in [
            r"C:\Program Files\Git\usr\bin\sh.exe",
            r"C:\Program Files\Git\bin\sh.exe",
        ]:
            if os.path.isfile(candidate):
                return candidate
        return None

    def _replace_required_once(self, path, old, new):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count(old)
        if count != 1:
            raise ConanException(f"Expected one occurrence of {old!r} in {path}, found {count}")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(old, new))

    def _replace_required_alternative(self, path, replacements):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        matched = []
        for old, new in replacements:
            count = content.count(old)
            if count > 1:
                raise ConanException(
                    f"Expected at most one occurrence of {old!r} in {path}, found {count}"
                )
            if count == 1:
                matched.append((old, new))
        if len(matched) != 1:
            candidates = ", ".join(repr(old) for old, _ in replacements)
            raise ConanException(
                f"Expected exactly one replacement candidate in {path}; candidates: {candidates}"
            )
        old, new = matched[0]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(old, new))

    def _replace_optional_alternative(self, path, replacements):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        matched = []
        for old, new in replacements:
            count = content.count(old)
            if count > 1:
                raise ConanException(
                    f"Expected at most one occurrence of {old!r} in {path}, found {count}"
                )
            if count == 1:
                matched.append((old, new))
        if len(matched) > 1:
            candidates = ", ".join(repr(old) for old, _ in replacements)
            raise ConanException(
                f"Expected at most one replacement candidate in {path}; candidates: {candidates}"
            )
        if not matched:
            return
        old, new = matched[0]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(old, new))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
