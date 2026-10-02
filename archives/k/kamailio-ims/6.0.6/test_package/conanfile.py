#!/usr/bin/env python3
"""test_package — kamailio-ims 6.0.6（16 个 IMS 模块，Kamailio 经典 Makefile 体系）。

消费者测试分两层，均为**对打包产物的真实使用**：

1) check_ims_modules.py —— 静态契约层（纯 Python 解析 ELF，无外部工具依赖）：
   16 个 .so 的身份/契约符号/DT_NEEDED 闭包/无 RPATH/未定义符号全量归类。

2) test_ims_modules_e2e.c —— 运行期消费者层（与 kamailio 加载器同源的加载序列）：
   dlopen(模块, RTLD_NOW|RTLD_GLOBAL) → dlsym(exports) 校验契约名/dlflags/cfg 命令表
   /modparam 表 → dlsym(mod_register) 调用并观察 core 侧 sr_kemi_modules_add 收到的
   KEMI 表 → ims_ipsec_pcscf 的 SPI 链表真实算法行为用例。

模块是 kamailio core 插件，引用大量 core 符号；OHOS/musl 加载器不做惰性绑定（dlopen
即等价 RTLD_NOW），故 core 符号需在测试进程内可解析：
   - kamailio_core_stub.c/-.h —— 手写「真实语义」子集（sr_kemi_modules_add 采集、
     shm_* 内存后端、日志路径）；
   - gen_core_stub.py 在测试时按被测 .so 的未定义符号面自动生成其余 core 符号弱桩
     （扣除 sysroot libc.so 与 conan 依赖包已提供的符号；含 libc 遮蔽硬闸）。
"""

import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"

# 本包归档的 16 个 IMS 模块（与 checks/上游 APKBUILD _mod_list_ims 一致）
MODULE_NAMES = (
    "cdp", "cdp_avp", "ims_auth", "ims_charging", "ims_dialog",
    "ims_diameter_server", "ims_icscf", "ims_ipsec_pcscf", "ims_isc", "ims_ocs",
    "ims_qos", "ims_qos_npn", "ims_registrar_pcscf", "ims_registrar_scscf",
    "ims_usrloc_pcscf", "ims_usrloc_scscf",
)

# 直接依赖包（checker 需要按名解析各自产物目录做符号闭包核验）
DIRECT_DEPS = ("libxml2", "libmnl", "openssl")


class KamailioImsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ───────────────────────── 环境探测 ─────────────────────────

    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器（profile conf → OHOS SDK 兜底 → CC/cc/gcc）。"""
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:  # conf 跨上下文不可读时退化为路径探测
            pass
        tried = []
        for cand in (exes.get("c"), OHOS_SDK_CLANG, os.environ.get("CC"),
                     "clang", "cc", "gcc"):
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
            tried.append(cand)
        raise ConanException(f"e2e: no usable C compiler (tried: {', '.join(tried)})")

    def _writable_tmpdir(self):
        """返回一个可写的临时目录供编译器放置中间文件。

        必须显式提供：鸿蒙目标机 /tmp 只读，若沿用环境里的 TMPDIR，clang 会直接
        `unable to make temporary file: No such file or directory` 而编译失败。
        """
        cand = os.environ.get("TMPDIR")
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
        fallback = os.path.join(self.build_folder, "build", "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _sysroot_candidates(self, cc):
        """推导目标 sysroot（不硬编码绝对路径：conf → 编译器路径相对推导）。"""
        cands = []
        for key in ("tools.build:cflags", "tools.build:cxxflags"):
            try:
                flags = self.conf.get(key, default=[], check_type=list) or []
            except Exception:
                continue
            for fl in flags:
                if isinstance(fl, str) and fl.startswith("--sysroot="):
                    cands.append(fl.split("=", 1)[1])
        try:
            sr = self.conf.get("tools.build:sysroot", default=None, check_type=str)
        except Exception:
            sr = None
        if sr:
            cands.append(sr)
        # 相对编译器目录推导 SDK 布局：<ccdir>/../<sdk>.<org>/<sdk-ver>/ohos/native/sysroot
        ccdir = os.path.dirname(os.path.abspath(cc))
        cands += glob.glob(os.path.join(ccdir, "..", "*", "*", "ohos", "native", "sysroot"))
        return [c for c in cands if c and os.path.isdir(c)]

    def _libc_so(self, cc):
        """定位目标 libc.so（gen_core_stub 的提供方过滤依据）。

        找不到则返回 None —— 此时 gen_core_stub.py 的 libc 遮蔽硬闸会硬失败，
        而不是静默生成顶替 libc 的桩（宁可红，不可假绿）。
        """
        for sr in self._sysroot_candidates(cc):
            for pat in ("usr/lib/*/libc.so", "lib/*/libc.so", "usr/lib/libc.so"):
                hits = sorted(glob.glob(os.path.join(sr, pat)))
                if hits:
                    return hits[0]
        return None

    def _dep_folders(self):
        """直接依赖包 + 全部宿主传递依赖的产物目录（供运行时 LD_LIBRARY_PATH 与
        提供方过滤使用）。"""
        folders = {}
        for name in DIRECT_DEPS:
            try:
                folders[name] = self.dependencies[name].package_folder
            except Exception:
                folders[name] = None
        try:
            for _ref, dep in self.dependencies.host.items():
                if dep.package_folder:
                    folders.setdefault(dep.ref.name, dep.package_folder)
        except Exception as exc:  # 传递依赖枚举失败不影响直连依赖
            self.output.warning(f"e2e: enumerate host deps failed: {exc}")
        return folders

    def _so_files(self, folders):
        """各依赖包产物目录下的 .so（含 lib/ 下一层），用于「符号提供方」过滤。"""
        out = []
        for folder in folders.values():
            if not folder:
                continue
            for pat in ("lib/*.so*", "lib/*/*.so*"):
                out += [p for p in glob.glob(os.path.join(folder, pat)) if os.path.isfile(p)]
        return sorted(set(out))

    # ───────────────────────── 测试主体 ─────────────────────────

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        package_folder = dep.package_folder
        modules_dir = os.path.join(package_folder, "lib", "kamailio", "modules")

        missing = [m for m in MODULE_NAMES
                   if not os.path.isfile(os.path.join(modules_dir, m + ".so"))]
        assert not missing, f"IMS 模块缺失（{len(missing)} 个）: {missing}"
        self.output.info(f"16 个 IMS 模块就位: {modules_dir}")

        dep_folders = self._dep_folders()
        # OHOS 侧 libmnl/openssl 预编译包为**静态形态**（仅 libmnl.a / libssl.a /
        # libcrypto.a）：不构成被测包的运行时闭包，conan 会把其 binary 标记为
        # skipped → 此处 package_folder 为空。故只对「conan 暴露了产物目录」的
        # 依赖断言目录存在，静态依赖仅记录（其符号已内嵌模块 .so，由 checker 按
        # 内嵌定义核验真被使用）。
        static_or_skipped = [n for n in DIRECT_DEPS if not dep_folders.get(n)]
        if static_or_skipped:
            self.output.info(f"静态/未入运行时闭包的依赖（无需产物目录）: {static_or_skipped}")
        for name, folder in dep_folders.items():
            if folder:
                assert os.path.isdir(folder), f"依赖 {name} 产物目录不存在: {folder}"
        self.output.info(f"依赖产物目录: {dep_folders}")

        # [1/4] 静态契约层：16 模块 ELF 身份/契约符号/依赖闭包/未定义符号归类
        checker = os.path.join(self.source_folder, "check_ims_modules.py")
        env = Environment()
        env.define("KAMAILIO_IMS_MODULES_DIR", modules_dir)
        env.define("KAMAILIO_IMS_PACKAGE_FOLDER", package_folder)
        for name in DIRECT_DEPS:
            if dep_folders.get(name):
                env.define(f"KAMAILIO_IMS_DEP_{name.upper()}", dep_folders[name])
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # [2/4] 生成 core 符号弱桩（按被测 .so 的未定义符号面，扣除 libc/依赖提供方）
        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")
        libc = self._libc_so(cc)
        self.output.info(f"libc provider: {libc or '(未找到——桩生成器将硬失败)'}")
        providers = ([libc] if libc else []) + self._so_files(dep_folders)
        providers = [p for p in providers if p]
        self.output.info(f"符号提供方 .so（{len(providers)} 个）: {providers}")

        work = os.path.join(self.build_folder, "build")
        os.makedirs(work, exist_ok=True)
        generated = os.path.join(work, "core_stub_generated.c")
        gen_cmd = [sys.executable, os.path.join(self.source_folder, "gen_core_stub.py"),
                   "--modules-dir", modules_dir, "--out", generated]
        for p in providers:
            gen_cmd += ["--provided-so", p]
        self.output.info("生成 core 弱桩: " + " ".join(f'"{c}"' if " " in c else c
                                                      for c in gen_cmd))
        subprocess.run(gen_cmd, check=True)

        # [3/4] 编译 e2e（桩层 + 自动生成弱桩 + 用例，导出符号供 dlopen 解析）
        e2e_dir = work
        e2e_bin = os.path.join(e2e_dir, "test_ims_modules_e2e")
        lib_dirs = []
        for cand in [modules_dir, os.path.join(package_folder, "lib")] + \
                [os.path.join(f, "lib") for f in dep_folders.values() if f]:
            if cand and os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        e2e_tmpdir = self._writable_tmpdir()
        self.output.info(f"e2e 运行时 LD_LIBRARY_PATH entries: {lib_dirs}")

        # 编译/链接环境只注入 TMPDIR：**绝不能**把 conan 运行库目录塞进链接器的
        # LD_LIBRARY_PATH。SDK 的 lld 自身 DT_NEEDED libxml2.so.16（RUNPATH 为
        # $ORIGIN/../lib，指向 SDK 自带副本），而 LD_LIBRARY_PATH 的优先级高于
        # RUNPATH——一旦前置 conan 的 libxml2 目录，lld 就会改载该副本；在 CI worker
        # 上该副本加载失败（Error loading shared library libxml2.so.16 → lld 的 xml*
        # 符号全部 not found），lld 启动即挂，clang 报 "unable to execute command:
        # No such file or directory"（PR #13949 CI 实测根因）。
        build_env = Environment()
        build_env.define("TMPDIR", e2e_tmpdir)
        with build_env.vars(self).apply():
            cmd = [cc, "-std=c11",
                   os.path.join(self.source_folder, "test_ims_modules_e2e.c"),
                   os.path.join(self.source_folder, "kamailio_core_stub.c"),
                   generated, "-o", e2e_bin,
                   "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
            subprocess.run(cmd, check=True)

        # 运行环境才需要 conan 依赖的运行时 .so（模块 DT_NEEDED libxml2.so.16）
        run_env = Environment()
        run_env.define("TMPDIR", e2e_tmpdir)
        for lib_dir in lib_dirs:
            run_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with run_env.vars(self).apply():
            # [4/4] 运行：16 模块契约 + 表结构 + KEMI 注册 + SPI 链表真实算法行为
            self.run(f'"{e2e_bin}" "{modules_dir}"')
