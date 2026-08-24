#!/usr/bin/env python3
"""Conan recipe for autodocksuite 4.2.6 — molecular docking suite (C++).

autodocksuite（Scripps，GPL-2.0）是分子对接工具套件：autodock（对接
主程序）+ autogrid（格点计算）。Debian orig tarball 顶层为 src/，
autodock 与 autogrid 各自独立 Autotools 构建（自带 configure）。

OHOS 适配:
- 跳过 X11/图形依赖（--without-x，核心对接计算无需 GUI）；
- config.guess 不识别 `aarch64-linux-ohos` → --build/--host=aarch64-linux；
- 依赖注入 Environment（无外部运行时依赖，纯 C++）；
- 测试: test_package 运行 autodock --help 验证可执行。
"""
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain


class AutodocksuiteConan(ConanFile):
    name = "autodocksuite"
    version = "4.2.6"
    description = "AutoDock/AutoGrid molecular docking suite (headless)"
    license = "GPL-2.0"
    homepage = "https://ccsb.scripps.edu/autodock/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 老 C++ 代码（2011）用 register 关键字，C++17 禁止 → -Wno-register
        tc.extra_cxxflags = ["-Wno-register"]
        tc.configure_args.extend(
            [
                "--build=aarch64-linux",
                "--host=aarch64-linux",
                "--without-x",
            ]
        )
        tc.generate()

    def _patch_configure_umask(self, build):
        """configure 运行前移除 umask 077（同 bogofilter 修复）。

        上游 configure 用 `umask 077 && mktemp -d ./confXXXXXX` 创建 ac_tmp
        临时目录，077 权限使脚本子进程写 subs1.awk 被鸿蒙 HMDFS 拦截。必须
        在 configure **运行前** patch configure 脚本本身。"""
        path = os.path.join(build, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        fixed = content.replace("umask 077 && mktemp", "mktemp")
        fixed = fixed.replace("umask 077 && mkdir", "mkdir")
        if fixed != content:
            save(self, path, fixed)
            self.output.info("patched configure: removed umask 077 (ac_tmp)")

    def _fix_config_status(self, build):
        """config.status ac_tmp 指向可写目录（鸿蒙安全框架拦脚本子进程
        写 TMPDIR，同 abook/globus-common 模式）。"""
        path = os.path.join(build, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        save(self, path, content)

    def _pregen_default_parameters(self, src_dir, build_dir):
        """预生成 default_parameters.h（鸿蒙无 csh）。

        上游 Makefile 用 `csh paramdat2h.csh AD4_parameters.dat AD4.1_bound.dat`
        生成 default_parameters.h；鸿蒙无 csh → 用等价 sh 命令预生成，
        使 make 认为目标已最新而跳过该规则。"""
        import subprocess
        out_path = os.path.join(build_dir, "default_parameters.h")
        if os.path.exists(out_path):
            return
        cmd = (
            "echo 'const char *param_string_4_0[MAX_LINES] = {';\n"
            f"grep -vE '^#|^$' {src_dir}/AD4_parameters.dat | "
            "sed 's/\\(.*\\)$/\"\\1\\\\n\", /';\n"
            "echo ' };';\n"
            "echo 'const char *param_string_4_1[MAX_LINES] = {';\n"
            f"grep -vE '^#|^$' {src_dir}/AD4.1_bound.dat | "
            "sed 's/\\(.*\\)$/\"\\1\\\\n\", /';\n"
            "echo ' };';\n"
            "echo '// EOF';\n"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            # conan build 环境 PATH 不含 /bin——用绝对路径调用 sh
            subprocess.run(["/bin/sh", "-c", cmd], stdout=f, check=True)
        self.output.info("pre-generated default_parameters.h (sh, no csh)")

    def build(self):
        # autodock 与 autogrid 各自独立 configure（src/ 下）
        for sub in ("autodock", "autogrid"):
            src_dir = os.path.join(self.source_folder, "src", sub)
            build_dir = os.path.join(self.build_folder, sub)
            os.makedirs(build_dir, exist_ok=True)
            # 先修 configure 脚本（umask 077 → 可写 ac_tmp），再运行 configure
            self._patch_configure_umask(src_dir)
            self.run(
                f"cd {build_dir} && {src_dir}/configure --build=aarch64-linux "
                f"--host=aarch64-linux --without-x",
                env="conanbuild",
            )
            self._fix_config_status(build_dir)
            # 无 csh → 预生成 default_parameters.h（autogrid 复用 autodock 的数据）
            data_dir = os.path.join(self.source_folder, "src", "autodock")
            if sub == "autodock":
                self._pregen_default_parameters(src_dir, build_dir)
            else:  # autogrid
                self._pregen_default_parameters(data_dir, build_dir)
                # autogrid Makefile 引用部分 .cpp，但源码在 autodock 为 .cc
                # （Debian orig 包裁剪）——批量复制补齐
                autogrid_src = os.path.join(self.source_folder, "src", "autogrid")
                for f in ("timesys", "timesyshms", "printhms", "printdate",
                          "read_parameter_library", "parse_param_line",
                          "mingw_getrusage", "stop"):
                    src_cc = os.path.join(data_dir, f + ".cc")
                    dst_cpp = os.path.join(autogrid_src, f + ".cpp")
                    if os.path.exists(src_cc) and not os.path.exists(dst_cpp):
                        with open(src_cc, "rb") as fin, open(dst_cpp, "wb") as fout:
                            fout.write(fin.read())
            self.run(f"cd {build_dir} && make -j4", env="conanbuild")

    def package(self):
        # 拷贝构建产物（autodock4/autogrid4 可执行 + 参数文件）
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for sub, exe_name in (("autodock", "autodock4"), ("autogrid", "autogrid4")):
            exe = os.path.join(self.build_folder, sub, exe_name)
            if os.path.exists(exe):
                self.run(f"install -m 755 {exe} {bindir}/")
        # 参数数据文件（运行时必需）
        for dat in ("AD4_parameters.dat", "AD4.1_bound.dat",
                    "AD4.1_compact.dat", "AD4.1_extended.dat",
                    "AD4_PARM99.dat"):
            src = os.path.join(self.source_folder, "src", "autodock", dat)
            if os.path.exists(src):
                self.run(f"install -m 644 {src} {bindir}/")
        # 鸿蒙可执行需 ELF 签名才能运行（同 qtdeclarative 先例）
        self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
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
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(".codesign" in line.split() for line in section_table.splitlines())

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate):
            resolved = candidate
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool '{executable}' not found in PATH"
            )
        return resolved

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
