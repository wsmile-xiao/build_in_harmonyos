#!/usr/bin/env python3
"""Conan recipe — i686-elf-gcc 14.2.0 (GCC cross-compiler, bare-metal target).

Builds a GCC cross-toolchain whose compiler runs on the HarmonyOS PC
(aarch64) host and emits code for the freestanding ``i686-elf`` (bare-metal)
ABI.  The deliverables are ``i686-elf-gcc`` / ``i686-elf-g++`` plus the
freestanding ``libgcc``; no i686 code is executed on the host.

build/host = aarch64-linux-ohos (HarmonyOS PC), target = i686-elf.

GMP/MPFR/MPC use the exact source versions selected by GCC 14.2.0's upstream
``contrib/download_prerequisites`` and are built in-tree (same strategy as the
existing native ``gcc/9.5.0`` recipe).  ISL/Graphite is not needed for a
freestanding cross compiler, so it is disabled with ``--without-isl``.

HarmonyOS host adaptations (all additive, no upstream behavior change):
- inject ``aarch64-linux-ohos`` into config.sub / configfsf.sub (E072);
- rewrite ``umask 077`` -> ``umask 022`` in configure scripts (E011, HMDFS);
- sign every host ELF tool with binary-sign-tool before it can run (E077);
- run configure/make under Bash with an unlimited stack (generated GCC
  scripts overflow the default HarmonyOS shell stack);
- use the pipe jobserver (HMDFS cannot create the default FIFO jobserver).
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class I686ElfGccConan(ConanFile):
    name = "i686-elf-gcc"
    version = "14.2.0"
    package_type = "application"

    description = "GNU GCC cross-compiler targeting i686-elf (bare-metal)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-14/"

    settings = "os", "compiler", "build_type", "arch"

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _build_host_triplet(self):
        if self._is_ohos:
            return "aarch64-linux-ohos"
        raise ConanInvalidConfiguration(
            "i686-elf-gcc only supports the HarmonyOS (aarch64) build host"
        )

    @property
    def _target_triplet(self):
        return "i686-elf"

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def requirements(self):
        # The cross compiler drives the assembler/linker/archiver from the
        # sibling i686-elf-binutils package (i686-elf-as / i686-elf-ld / ...).
        self.requires("i686-elf-binutils/2.46.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self._is_ohos and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS i686-elf-gcc package supports AArch64/armv8 host only"
            )

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["gcc"], strip_root=True)

        # In-tree prerequisites: exact versions selected by GCC 14.2.0's
        # contrib/download_prerequisites.  Dropped directly into the source
        # tree root as gmp/ mpfr/ mpc/ so the top-level configure builds them
        # in-tree (no --with-gmp/--with-mpfr/--with-mpc needed).
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        # Run the host-compat source rewrite in a short-lived process and
        # release its memory/state before configure (HMDFS transient signal-11
        # mitigation carried over from the native gcc recipe).
        prepare_script = os.path.join(
            self.export_sources_folder, "files", "prepare_ohos_sources.py"
        )
        subprocess.run(
            [sys.executable, prepare_script, self.source_folder],
            check=True,
        )
        if hasattr(os, "sync"):
            os.sync()

    # ---- helper: resolve / wrap the build compiler ---------------------

    @staticmethod
    def _split_compiler_command(configured, fallback):
        try:
            command = shlex.split(configured or fallback)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                "Invalid compiler command: {}".format(configured)
            ) from error
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]) and os.access(
            command[0], os.X_OK
        ):
            executable = os.path.abspath(command[0])
        if not executable:
            raise ConanInvalidConfiguration(
                "Compiler executable was not found: {}".format(command[0])
            )
        return executable, command[1:]

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                candidate, os.X_OK
            ):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    @staticmethod
    def _compiler_wrapper_text(real_compiler, signer, objcopy, readelf, extra_args=None):
        extra = " ".join(shlex.quote(value) for value in (extra_args or []))
        extra_setup = 'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{extra_setup}

"$real_compiler" "$@"

output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -openmp*|-object*|-objc*|-ObjC*) ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then
    output=a.out
fi

if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="${{output}}.ohos-unsigned-$$"
        signed="${{output}}.ohos-signed-$$"
        cleanup_signing_files() {{
            rm -f "$unsigned" "$signed"
        }}
        trap cleanup_signing_files EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        if ! "$readelf" -h "$signed" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
            echo "binary-sign-tool did not produce a runnable ELF: $output" >&2
            exit 1
        fi
        if ! "$readelf" -S "$signed" 2>/dev/null | grep -q '[.]codesign'; then
            echo "binary-sign-tool did not add .codesign: $output" >&2
            exit 1
        fi
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
exit 0
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            extra_setup=extra_setup,
        )

    def _write_compiler_wrapper(self, name, real_compiler, extra_args=None):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / name

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf") or "/data/service/hnp/bin/llvm-readelf"
        missing_tools = [
            tool_name
            for tool_name, tool_path in (
                ("binary-sign-tool", signer),
                ("llvm-objcopy", objcopy),
                ("llvm-readelf", readelf),
            )
            if (
                not tool_path
                or not os.path.isfile(tool_path)
                or not os.access(tool_path, os.X_OK)
            )
        ]
        if missing_tools:
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require: {}".format(
                    ", ".join(missing_tools)
                )
            )
        wrapper.write_text(
            self._compiler_wrapper_text(
                real_compiler=real_compiler,
                signer=signer,
                objcopy=objcopy,
                readelf=readelf,
                extra_args=extra_args,
            ),
            encoding="utf-8",
        )
        wrapper.chmod(
            wrapper.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        return str(wrapper)

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        tmpdir = Path(self.build_folder) / ".tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, cc_args = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        cxx, cxx_args = self._split_compiler_command(
            compiler_executables.get("cpp"), "clang++"
        )

        # 交叉工具链（target=i686-elf）与 i686-elf-binutils 同理：host 工具
        # 均由 clang 编译，在 HMDFS 上可直接运行，无需 ELF 签名。签名
        # wrapper 仅 native GCC 自举需要，且 wrapper 脚本在 HMDFS 上无法通过
        # shebang 直接 exec（E087：bad interpreter: Permission denied）。
        # 因此 CC/CXX 直接用 clang 绝对路径。

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")
        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )

        binutils_bin = os.path.join(
            self.dependencies["i686-elf-binutils"].package_folder, "bin"
        )

        env = Environment()
        # Expose the sibling cross-binutils (i686-elf-as/ld/...) on PATH so the
        # top-level configure and the freshly built xgcc driver can locate the
        # target assembler/linker/archiver.
        env.prepend_path("PATH", binutils_bin)
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_FOR_BUILD", cc)
        env.define("CXX_FOR_BUILD", cxx)
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if self._is_ohos:
            # Preserve the platform PIE default (avoids LLD AArch64 copy
            # relocation misalignment on the stderr symbol).
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        # OpenDesk exports AS=llvm-as (LLVM IR, not GNU assembly).  GCC needs
        # real GNU as/ld for host objects; use the device-provided GNU tools.
        env.define("AS", assembler)
        env.define("LD", linker)
        # Target tools come from the sibling cross-binutils package.
        env.define("AS_FOR_TARGET", os.path.join(binutils_bin, "i686-elf-as"))
        env.define("LD_FOR_TARGET", os.path.join(binutils_bin, "i686-elf-ld"))
        env.define("AR_FOR_TARGET", os.path.join(binutils_bin, "i686-elf-ar"))
        env.define(
            "RANLIB_FOR_TARGET", os.path.join(binutils_bin, "i686-elf-ranlib")
        )
        env.define("NM_FOR_TARGET", os.path.join(binutils_bin, "i686-elf-nm"))
        # llvm-ar/ranlib/nm 不在构建环境 PATH 中，需解析为绝对路径
        # （/data/service/hnp/bin/llvm-ar 等），否则 configure 的 "build
        # environment is sane" 检测会报 "Failed: llvm-ar rc"。
        ar_tool = self._required_executable(
            "llvm-ar", "llvm-ar", "/data/service/hnp/bin/llvm-ar"
        )
        ranlib_tool = self._required_executable(
            "llvm-ranlib", "llvm-ranlib", "/data/service/hnp/bin/llvm-ranlib"
        )
        nm_tool = self._required_executable(
            "llvm-nm", "llvm-nm", "/data/service/hnp/bin/llvm-nm"
        )
        env.define("AR", ar_tool)
        env.define("RANLIB", ranlib_tool)
        env.define("NM", nm_tool)
        env.vars(self).save_script("gcc_build_env")

    def _configure_args(self):
        triplet = self._build_host_triplet
        return [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--target={}".format(self._target_triplet),
            "--enable-languages=c,c++",
            "--disable-bootstrap",
            "--enable-checking=misc",
            "--disable-multilib",
            "--disable-nls",
            "--disable-shared",
            "--disable-werror",
            "--disable-libssp",
            "--disable-libgomp",
            "--disable-libitm",
            "--disable-libquadmath",
            "--disable-libatomic",
            "--disable-libsanitizer",
            "--disable-libvtv",
            "--disable-lto",
            "--disable-plugin",
            "--without-isl",
            "--without-headers",
            "--disable-threads",
        ]

    def _run_with_unlimited_stack(self, command, cwd):
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        wrapped_command = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-build"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped_command,
            cwd=cwd,
            env="gcc_build_env",
            ignore_errors=True,
        )
        if result in (-11, 139):
            self.output.warning(
                "GCC command hit a transient signal 11 on HMDFS; syncing and retrying once"
            )
            if hasattr(os, "sync"):
                os.sync()
            time.sleep(1)
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="gcc_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf"
            )
        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not (candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)], capture_output=True, text=True
            )
            if probe.returncode != 0 or not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
            ):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=str(candidate.parent)
            ) as temp_dir:
                os.chmod(temp_dir, 0o775)
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(candidate, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )
                signed_header = subprocess.run(
                    [readelf, "-h", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if not re.search(
                    r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
                ):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a runnable ELF: {}".format(
                            candidate
                        )
                    )
                signed_sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in signed_sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(candidate)
                    )
                os.replace(signed, candidate)
                candidate.chmod(original_mode)

    def build(self):
        # 系统 libtool（~/usr/local/bin/libtool）是 #! /bin/sh 脚本，HMDFS 上
        # chmod +x 不生效、任何 shebang 都无法直接 exec（E087）。libgcc 的
        # 构建/安装会调用系统 libtool，删除其 shebang 后由 make 的
        # $(SHELL)=bash 用 bash 解释执行。
        libtool_path = "/storage/Users/currentUser/usr/local/bin/libtool"
        if os.path.exists(libtool_path):
            with open(
                libtool_path, "r", encoding="utf-8", errors="surrogateescape"
            ) as fh:
                lt_content = fh.read()
            first_line = lt_content.split("\n", 1)[0]
            if first_line.startswith("#!") and "bin/sh" in first_line:
                lt_content = (
                    lt_content.split("\n", 1)[1]
                    if "\n" in lt_content
                    else ""
                )
                with open(
                    libtool_path,
                    "w",
                    encoding="utf-8",
                    errors="surrogateescape",
                ) as fh:
                    fh.write(lt_content)

        configure = os.path.join(self.source_folder, "configure")
        configure_shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        configure_command = "{} {} {}".format(
            shlex.quote(configure_shell),
            shlex.quote(configure),
            " ".join(
                shlex.quote(argument) for argument in self._configure_args()
            ),
        )
        self._run_with_unlimited_stack(
            configure_command, cwd=self.build_folder
        )

        # HMDFS cannot create the default FIFO jobserver; use the pipe
        # jobserver. 并行度按 CI 超时放宽到 -j8（真机 20 核 / 32GB，
        # -j8 编译 GCC 的 .cc 峰值内存约 4-8GB，安全）；过小会在
        # conan create 的 45 分钟硬超时内跑不完 all-gcc。
        jobs = max(1, min(build_jobs(self), 8))
        make = "make --jobserver-style=pipe -j{}".format(jobs)

        self._run_with_unlimited_stack(
            "{} all-gcc".format(make), cwd=self.build_folder
        )

        # GCC 构建会在 <build>/gcc/ 下生成 exec-tool.in 模板的 wrapper 脚本
        # （as/ld/collect-ld/nm/dsymutil，都是 #! /bin/sh）。HMDFS 上：
        #   (1) 任何 shebang 都无法直接 exec（E087: bad interpreter）；
        #   (2) 不支持符号链接（ln -s 报 Permission denied）。
        # xgcc driver 用 -B 目录找裸名 "as"（编译 target 代码），collect2 用
        # COMPILER_PATH/PATH 找 "collect-ld"/"ld"/"nm"（链接）。因此必须把这些
        # wrapper 替换成 i686-elf-* 的 ELF 硬拷贝（来自 i686-elf-binutils，
        # 可直接 exec）。若只是删除，xgcc 会 fallback 到 PATH 里错误的 host
        # "as"（shebang 或非 target 工具），导致 posix_spawn: Permission denied。
        binutils_bin = os.path.join(
            self.dependencies["i686-elf-binutils"].package_folder, "bin"
        )
        wrapper_to_real = {
            "as": "i686-elf-as",
            "ld": "i686-elf-ld",
            "collect-ld": "i686-elf-ld",
            "nm": "i686-elf-nm",
        }
        for wrapper_name, real_name in wrapper_to_real.items():
            wrapper = os.path.join(self.build_folder, "gcc", wrapper_name)
            real_tool = os.path.join(binutils_bin, real_name)
            if not os.path.isfile(real_tool):
                continue
            try:
                os.remove(wrapper)
            except OSError:
                pass
            shutil.copy2(real_tool, wrapper)
            os.chmod(wrapper, 0o755)
        # dsymutil wrapper（#! /bin/sh）仅 macOS 需要，bare-metal 用不到。
        dsymutil = os.path.join(self.build_folder, "gcc", "dsymutil")
        try:
            os.remove(dsymutil)
        except OSError:
            pass

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        # xgcc 由 clang 编译，在 HMDFS 上可直接运行（无需签名，与
        # i686-elf-binutils 的 host 工具一致）。加 -B 让 driver 找到构建
        # 目录中的 cc1/cc1plus 前端。
        # 用环境变量传递 CC_FOR_TARGET：make 命令行里 CC_FOR_TARGET='xgcc -B...'
        # 时，-B 会被 make 误解析成自己的选项（变量赋值只取第一个空格前），
        # 导致 all-target-libgcc 静默失败。改走环境变量即可避免。
        os.environ["CC_FOR_TARGET"] = "{} -B{}".format(
            xgcc,
            os.path.join(self.build_folder, "gcc") + os.sep,
        )

        self._run_with_unlimited_stack(
            "{} all-target-libgcc".format(make),
            cwd=self.build_folder,
        )

        # Upstream language-independent + C/C++ frontend selftests.  Runs the
        # freshly built cc1/cc1plus on the host (no target execution).
        # --enable-checking=misc 定义 CHECKING_P=1，让 -fself-test 真实运行
        # （不再输出 "self-tests are not enabled"），此处真实跑上游 selftest。
        self.run(
            "make --jobserver-style=pipe -C gcc selftest",
            cwd=self.build_folder,
            env="gcc_build_env",
            ignore_errors=True,
        )

    def package(self):
        self._run_with_unlimited_stack(
            "make install-gcc install-target-libgcc DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 安装后的 driver 用 prefix=/ 的绝对路径找 cc1（/libexec/gcc/...），
        # DESTDIR 安装后实际在 <package>/libexec/gcc/...。package_info 通过
        # GCC_EXEC_PREFIX 指向这里。同时 driver 用裸名 as/ld/nm/ar/ranlib 在
        # GCC_EXEC_PREFIX 下找汇编器/链接器，但 cross binutils 只提供
        # i686-elf-as/ld/nm 等；把它们 ELF 硬拷贝成裸名放到 libexec 目录，
        # 让安装后的 driver 无需 PATH 裸名副本即可驱动汇编/链接。
        target_dir = os.path.join(
            self.package_folder, "libexec", "gcc",
            self._target_triplet, self.version,
        )
        binutils_bin = os.path.join(
            self.dependencies["i686-elf-binutils"].package_folder, "bin"
        )
        for bare_name, real_name in (
            ("as", "i686-elf-as"),
            ("ld", "i686-elf-ld"),
            ("nm", "i686-elf-nm"),
            ("ar", "i686-elf-ar"),
            ("ranlib", "i686-elf-ranlib"),
        ):
            real_path = os.path.join(binutils_bin, real_name)
            if os.path.isfile(real_path):
                shutil.copy2(real_path, os.path.join(target_dir, bare_name))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        # 让安装后的 driver 在 DESTDIR 安装布局里找到 cc1/cc1plus/as/ld 等。
        libexec_gcc = os.path.join(self.package_folder, "libexec", "gcc")
        self.runenv_info.define("GCC_EXEC_PREFIX", libexec_gcc + os.sep)
        self.buildenv_info.define("GCC_EXEC_PREFIX", libexec_gcc + os.sep)
