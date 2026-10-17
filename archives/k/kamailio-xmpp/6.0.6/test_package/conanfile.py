#!/usr/bin/env python3
"""Conan test_package — kamailio-xmpp（xmpp.so）消费者视角验证。

xmpp.so 由 kamailio 二进制运行时 loadmodule 加载，故消费者验证分两层：

1. check_module.py —— 产物与平台契约：AArch64/ET_DYN ELF、core 契约符号动态导出、
   模块接口表（exports）、**装载契约串**（SER_FULL_VERSION="kamailio 6.0.6
   (aarch64/linux)" 与 SER_COMPILE_FLAGS：USE_TCP 在 / USE_SCTP 不在 /
   HAVE_RESOLV_RES 不在 —— core 侧严格 strcmp）、expat 依赖链接证据（NEEDED
   含 libexpat.so + 未解析 XML_* + 无本地桩）、NEEDED 全裸名可重定位、无
   RPATH/RUNPATH 宿主路径泄漏、COPYING 与模块 README 随包。

2. test_consumer.c —— 消费者用例：按 kamailio core 的装载协议消费模块 ——
   先 dlopen libexpat.so（依赖在目标机可加载），再 dlopen xmpp.so（RTLD_NOW：
   全部重定位当场解析），dlsym 契约符号（module_version / module_flags 是模块内
   char * 数据符号，core 侧按 (char **) 解引用，本用例同口径），并**真实调用模块
   自身的 XMPP stanza 解析 API**（xode_from_str → 内部走 expat
   XML_ParserCreate/XML_Parse → xode_get_name/xode_get_attrib/xode_to_str/
   xode_free），含非法 XML 负例。

   模块对 core 符号（cfg_*、_shm_root、find_export、dprint_* 等）的引用本由
   kamailio 宿主进程提供；独立消费者进程里这些符号无处解析，dlopen 会因重定位
   失败。故本配方采集模块未解析动态符号，剔除 ① 本进程已能解析的部分（libc 等）
   与 ② **依赖库自身导出的符号**（expat 的 XML_* 等），为剩余 core 符号生成强定义桩
   一并链入可执行文件（--export-dynamic 导出），等价于 kamailio 可执行文件导出
   core 符号。② 不可省：可执行文件位于全局作用域首位，若把 XML_* 也打成空桩，
   模块重定位会绑定到空桩而非 libexpat，测试将失去意义甚至崩溃。

   生成的桩与消费者二进制放在 $TMPDIR 下的独立工作目录（不写入归档树），
   test() 结束即清理。

交叉编译：消费者程序由本配方 build() 调用 profile 声明的交叉 C 编译器
（tools.build:compiler_executables → AutotoolsToolchain 导出的 $CC）编译，
依赖路径全部来自依赖包 cpp_info，未注入任何共享前缀（R49）。
"""
import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import save
from conan.tools.gnu import AutotoolsToolchain

MODULE_RELPATH = os.path.join("lib", "kamailio", "modules", "xmpp.so")
CORE_STUB_NAME = "core_stubs.c"
CONSUMER_NAME = "test_consumer"
# C 标识符校验：nm 输出可能带 C++ 修饰名 / 版本后缀，非标识符直接丢弃
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class KamailioXmppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式直接依赖：被测包的传递依赖在测试图谱中可能呈 skip 态
        # （package_folder=None，VirtualRunEnv 无法聚合其 libdir）→ 消费者
        # dlopen libexpat.so 失败。声明为直接依赖后获得完整二进制解析
        # （与被测包同 ref 自动归并节点，无冲突）。
        self.requires("expat/2.8.2.1.1")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # 生成 conanrun.sh 运行时环境：聚合全部依赖（含传递依赖）的 LD_LIBRARY_PATH
        from conan.tools.env import VirtualRunEnv
        VirtualRunEnv(self).generate(scope="run")

    # ── 工具 ────────────────────────────────────────────────────────────────
    def _workdir(self):
        """消费者桩/二进制的独立工作目录（$TMPDIR 下，不写入归档树）。"""
        d = os.path.join(tempfile.gettempdir(), "kamailio-xmpp-test-build")
        os.makedirs(d, exist_ok=True)
        return d

    def _libdirs(self):
        """全部依赖的库目录（绝对路径）。"""
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # 被测包（本地构建态依赖）无 package_folder，跳过
                continue
            for d in dep.cpp_info.libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p) and p not in libdirs:
                    libdirs.append(p)
            std_lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(std_lib) and std_lib not in libdirs:
                libdirs.append(std_lib)
        return libdirs

    def _nm(self):
        return shutil.which("llvm-nm") or shutil.which("nm")

    def _undefined_symbols(self, module):
        """采集模块动态符号表中未解析（UND）的符号名；nm 不可用/失败返回 None。"""
        nm = self._nm()
        if not nm:
            self.output.warning("未找到 nm/llvm-nm，无法采集模块未解析符号")
            return None
        proc = subprocess.run([nm, "-D", "--undefined-only", module],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            self.output.warning(f"{nm} -D --undefined-only 失败（rc={proc.returncode}）")
            return None
        names = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("nm:"):
                continue
            name = line.split()[-1].split("@")[0]
            if _IDENT_RE.fullmatch(name) and name not in names:
                names.append(name)
        return names

    def _dependency_symbols(self, libdirs):
        """依赖库（expat 等）动态导出的符号名集合。这些符号绝不可打桩。"""
        symbols = set()
        nm = self._nm()
        if not nm:
            return symbols
        for libdir in libdirs:
            for entry in sorted(os.listdir(libdir)):
                if ".so" not in entry:
                    continue
                path = os.path.join(libdir, entry)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                proc = subprocess.run([nm, "-D", "--defined-only", path],
                                      capture_output=True, text=True)
                if proc.returncode != 0:
                    continue
                for line in proc.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[-2].upper() != "U":
                        symbols.add(parts[-1].split("@")[0])
        return symbols

    def _host_missing(self, names):
        """剔除本进程动态作用域已能解析的符号（dlsym(RTLD_DEFAULT) 判定）。"""
        libc = ctypes.CDLL(None)
        libc.dlsym.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        libc.dlsym.restype = ctypes.c_void_p
        return [n for n in names if not libc.dlsym(None, n.encode())]

    def _core_stub_source(self):
        """生成 core 符号桩源码；返回 None 表示降级（跳过运行时消费者用例）。"""
        module = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                              MODULE_RELPATH)
        names = self._undefined_symbols(module)
        if not names:
            return None
        libdirs = self._libdirs()
        dep_symbols = self._dependency_symbols(libdirs)
        candidates = [n for n in names if n not in dep_symbols]
        skipped = len(names) - len(candidates)
        missing = self._host_missing(candidates)
        if not missing:
            self.output.warning("模块无宿主缺失符号，无需 core 桩")
            return None
        self.output.info(f"core 桩：宿主缺失符号 {len(missing)} 个"
                         f"（模块未解析符号 {len(names)} 个，其中依赖库提供 {skipped} 个已排除）")
        body = "\n".join(f'__attribute__((visibility("default"))) void {n}(void) {{}}'
                         for n in missing)
        return ("/* 自动生成：xmpp.so 引用的 kamailio core 符号桩（模拟宿主进程导出\n"
                " * core 符号）。仅覆盖本进程无法解析、且依赖库不提供的符号；\n"
                " * 依赖库导出的符号（如 expat 的 XML_*）不得进入本文件，否则可执行文件\n"
                " * 的空桩会在全局作用域优先绑定，顶替真实依赖实现。本用例不调用这些桩。 */\n"
                f"{body}\n")

    def build(self):
        # 消费者只 dlopen 模块并经 dlsym 调用其导出符号，故意不链接 expat 库：
        # 若链接，消费者会自带副本，掩盖「模块 → expat 运行路径」的真问题。
        workdir = self._workdir()
        sources = [f'"{os.path.join(self.source_folder, "test_consumer.c")}"']
        stub_src = os.path.join(workdir, CORE_STUB_NAME)
        stub = self._core_stub_source()
        if stub:
            save(self, stub_src, stub)
            sources.append(f'"{stub_src}"')
        # --export-dynamic：core 桩须进入可执行文件动态符号表，模块 dlopen 时才可解析
        self.run(
            '"$CC" -std=c99 -Wall -Wextra $CFLAGS {sources} -o "{out}" '
            '-Wl,--export-dynamic $LDFLAGS'.format(
                sources=" ".join(sources),
                out=os.path.join(workdir, CONSUMER_NAME)),
            cwd=workdir,
        )

    def test(self):
        tested = self.dependencies[self.tested_reference_str]
        package_folder = tested.package_folder
        module = os.path.join(package_folder, MODULE_RELPATH)
        assert os.path.isfile(module), f"xmpp.so not found at {module}"
        self.output.info(f"xmpp.so found: {module}")

        # 消费者运行时需依赖包 libdir（libexpat.so 为共享库，musl 无 rpath）：
        # 显式注入 LD_LIBRARY_PATH（sems-dsm 已验证模式）；尾部保留 $LD_LIBRARY_PATH
        # （conanrun 注入的传递依赖路径），避免同名覆盖丢路径。
        libdirs = self._libdirs()
        self.output.info(f"[diag] consumer libdirs={libdirs}")

        workdir = self._workdir()
        checker = os.path.join(self.source_folder, "check_module.py")
        env = Environment()
        env.define("KAMAILIO_XMPP_MODULE", module)
        env.define("KAMAILIO_XMPP_PACKAGE_FOLDER", package_folder)
        try:
            with env.vars(self).apply():
                self.run(f'"{sys.executable}" "{checker}"', cwd=workdir)

            # 运行时用例需要 core 符号桩；桩生成失败即降级跳过，
            # 避免把「检查工具缺失」误报成「模块不可用」
            stub_src = os.path.join(workdir, CORE_STUB_NAME)
            consumer = os.path.join(workdir, CONSUMER_NAME)
            if not os.path.isfile(stub_src):
                self.output.warning("core 符号桩缺失，跳过运行时消费者用例")
                return
            if not can_run(self):
                self.output.warning("cross-building environment: 跳过运行时消费者用例")
                return
            self.run(f'LD_LIBRARY_PATH="{":".join(libdirs)}:$LD_LIBRARY_PATH" '
                     f'"{consumer}" "{module}"', cwd=workdir)
        finally:
            # 清理临时产物（不进入归档树；日志已由 conan 留存）
            for name in (CORE_STUB_NAME, CONSUMER_NAME):
                p = os.path.join(workdir, name)
                if os.path.isfile(p):
                    os.remove(p)
