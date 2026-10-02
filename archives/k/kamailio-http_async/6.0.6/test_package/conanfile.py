#!/usr/bin/env python3
"""Conan test_package — kamailio-http_async（http_async_client.so）消费者视角验证。

http_async_client.so 由 kamailio 二进制运行时 loadmodule 加载，故消费者验证分两层：

1. check_module.py —— 产物与平台契约：AArch64 ELF、core 契约符号动态导出、
   模块接口表（exports 或 _http_async_client_exports 回退）、libcurl/libevent
   静态并入证据（NEEDED 无 libcurl/libevent + curl API 动态导出）、NEEDED 无
   glibc 专名库（musl 契约）、无 RPATH/RUNPATH 宿主路径泄漏、COPYING 随包。
2. test_consumer.c —— 消费者用例：按 kamailio core 的装载协议消费模块 —— dlopen
   装入 → dlsym module_version / module_flags / mod_register / exports 接口表 →
   经 dlsym 调用模块静态并入的 libcurl API（curl_easy_init/setopt/cleanup）
   真实创建销毁 handle（证明静态并入的 libcurl 在 OHOS aarch64 上确实可运行）。

   模块对 core 符号（log_function_call / dbg 等）的引用本由 kamailio 宿主进程
   提供；独立消费者进程里这些符号无处解析，dlopen 会因重定位失败。故本配方
   采集模块未解析动态符号，剔除本进程已能解析的部分（libc 等），为剩余 core
   符号生成强定义桩一并链入可执行文件（--export-dynamic 导出），等价于
   kamailio 可执行文件导出 core 符号；桩不含 libc 已有符号，真实实现不会被顶掉。

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

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import save
from conan.tools.gnu import AutotoolsToolchain

MODULE_RELPATH = os.path.join("lib", "kamailio", "modules", "http_async_client.so")
CORE_STUB_NAME = "core_stubs.c"
# C 标识符校验：nm 输出可能带 C++ 修饰名 / 版本后缀，非标识符直接丢弃
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class KamailioHttpAsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式直接依赖：被测包的传递依赖 libevent 在测试图谱中呈 skip 态
        # （package_folder=None，create20 诊断插桩实证），VirtualRunEnv 无法
        # 聚合其 libdir → 消费者 dlopen libevent-2.1.so.7 失败。声明为直接
        # 依赖后获得完整二进制解析（与被测包同 ref 自动归并节点，无冲突）。
        self.requires("libevent/2.1.12")
        self.requires("curl/8.15.0.1")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # 生成 conanrun.sh 运行时环境：聚合全部依赖（含传递依赖）的
        # LD_LIBRARY_PATH。此前 test() 一直传 env="conanrun" 但从未生成该
        # 脚本，消费者进程只有 SDK 默认路径——libcurl/libevent 加载失败的
        # 根因（create13-17 实测链）
        from conan.tools.env import VirtualRunEnv
        VirtualRunEnv(self).generate(scope="run")

    def _undefined_symbols(self, module):
        """采集模块动态符号表中未解析（UND）的符号名；nm 不可用/失败返回 None。"""
        nm = shutil.which("llvm-nm") or shutil.which("nm")
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
        missing = self._host_missing(names)
        if not missing:
            self.output.warning("模块无宿主缺失符号，无需 core 桩")
            return None
        self.output.info(f"core 桩：宿主缺失符号 {len(missing)} 个"
                         f"（模块未解析符号共 {len(names)} 个）")
        body = "\n".join(f'__attribute__((visibility("default"))) void {n}(void) {{}}'
                         for n in missing)
        return ("/* 自动生成：http_async_client.so 引用的 kamailio core 符号桩"
                "（模拟宿主进程导出\n * core 符号）。仅覆盖本进程无法解析的符号，"
                "本用例不调用这些桩。 */\n"
                f"{body}\n")

    def build(self):
        # 消费者只 dlopen 模块并经 dlsym 调用其导出符号，故意不链接 curl/event
        # 库：若链接，消费者会自带副本，掩盖"模块静态并入不可用"的真问题。
        sources = [f'"{os.path.join(self.source_folder, "test_consumer.c")}"']
        stub_src = os.path.join(self.build_folder, CORE_STUB_NAME)
        stub = self._core_stub_source()
        if stub:
            save(self, stub_src, stub)
            sources.append(f'"{stub_src}"')
        # --export-dynamic：core 桩须进入可执行文件动态符号表，模块 dlopen 时才可解析
        self.run(
            '"$CC" -std=c99 -Wall -Wextra $CFLAGS {sources} -o "{out}" '
            '-Wl,--export-dynamic $LDFLAGS'.format(
                sources=" ".join(sources),
                out=os.path.join(self.build_folder, "test_consumer")),
            cwd=self.build_folder,
        )

    def test(self):
        tested = self.dependencies[self.tested_reference_str]
        package_folder = tested.package_folder
        module = os.path.join(package_folder, MODULE_RELPATH)
        assert os.path.isfile(module), f"http_async_client.so not found at {module}"
        self.output.info(f"http_async_client.so found: {module}")

        checker = os.path.join(self.source_folder, "check_module.py")
        # 共享依赖模型：消费者运行时需依赖包 libdir（libcurl/libevent 共享库，
        # musl 无 rpath），显式注入 LD_LIBRARY_PATH（sems-dsm 已验证模式）。
        # cpp_info.libdirs 可能是相对路径（如 "lib"），相对 cwd 解析会失效——
        # 一律转 package_folder 绝对路径；并保留原 $LD_LIBRARY_PATH（conanrun
        # 注入的传递依赖路径），避免同名覆盖丢路径（schism CPATH 同款坑）
        libdirs = []
        # 诊断插桩：显式记录 libevent/curl 依赖条目查找结果（create13-19 六轮
        # dlopen 失败的定位盲区——libevent libdir 始终未进 LD_LIBRARY_PATH，
        # 需拿异常原文判断是 lookup 失败还是路径形态问题）
        for dep_name in ("libevent", "curl"):
            try:
                dep = self.dependencies[dep_name]
                self.output.info(
                    f"[diag] dep {dep_name}: package_folder={dep.package_folder} "
                    f"libdirs={dep.cpp_info.libdirs}")
                if dep.package_folder:
                    std_lib = os.path.join(dep.package_folder, "lib")
                    if os.path.isdir(std_lib) and std_lib not in libdirs:
                        libdirs.append(std_lib)
            except Exception as e:  # noqa: BLE001 — 诊断分支，需打印原文
                self.output.error(f"[diag] dep {dep_name} lookup FAILED: {e!r}")
        # 其余依赖兜底遍历
        for dep in self.dependencies.values():
            # tested_reference（本地 editable/构建态依赖）无 package_folder，跳过
            if not dep.package_folder:
                continue
            for d in dep.cpp_info.libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p) and p not in libdirs:
                    libdirs.append(p)
            std_lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(std_lib) and std_lib not in libdirs:
                libdirs.append(std_lib)
        env = Environment()
        env.define("KAMAILIO_HTTPASYNC_MODULE", module)
        env.define("KAMAILIO_HTTPASYNC_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"', cwd=self.build_folder)

        # 运行时用例需要 core 符号桩；桩生成失败即降级跳过，
        # 避免把"检查工具缺失"误报成"模块不可用"
        if not os.path.isfile(os.path.join(self.build_folder, CORE_STUB_NAME)):
            self.output.warning("core 符号桩缺失，跳过运行时消费者用例")
            return
        if not can_run(self):
            self.output.warning("cross-building environment: 跳过运行时消费者用例")
            return
        consumer = os.path.join(self.build_folder, "test_consumer")
        # conan 2 中 env="conanrun" 不产生内联前缀（create21 RUN 行实证：命令行
        # 无任何环境包装），消费者进程只有 SDK 默认路径 → libevent 加载失败。
        # 改为显式内联 LD_LIBRARY_PATH：libdirs 现已包含 libevent（create21
        # [diag] 实测 package_folder 正确解析），尾部 $LD_LIBRARY_PATH 保留
        # conan 已注入的路径
        self.run(f'LD_LIBRARY_PATH="{":".join(libdirs)}:$LD_LIBRARY_PATH" '
                 f'"{consumer}" "{module}"')
