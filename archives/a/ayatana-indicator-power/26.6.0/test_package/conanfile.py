#!/usr/bin/env python3
"""Conan test_package for ayatana-indicator-power — R12 完整消费者端到端用例.

规则整改（rule12）：鸿蒙特有测试不能只有断言式冒烟（--version/--help），
必须提供"真实消费者程序 + 真实服务运行"的端到端用例（与已过审先例
at-spi2-core 一致）。

OHOS PC 无 dbus-daemon / session bus，因此 test_package 采用 0005 补丁
新增的 peer-bus 模式：

  1. 编译 test_consumer.c（真实消费者程序，链接 conan 依赖的 glib/gio）。
  2. 编译服务自带的 GSettings schema（glib-compile-schemas，来自 glib
     包 bin），供服务读取电池/亮度设置。
  3. 消费者用 GDBusServer 起私有进程间 peer 连接（unix:abstract= 地址，
     避开 OHOS 沙箱对文件系统型 UNIX socket 的 EPERM），把地址经
     AIP_TEST_BUS_ADDR 传给真实服务二进制。
  4. 服务在 peer-bus 模式下导出全部对象（Testing/Battery 骨架），
     消费者经真实 D-Bus 协议驱动 Testing 接口设置 mock 电池 80%，
     再断言 Battery.PowerPercentage=80 / IsDischarging=true /
     PowerLevel=ok，全程真实进程间通信。

- R34: 真实执行被测包二进制 + 真实消费者程序（均非空壳）。
- L0d: test() 使用 self.run() 执行消费者与服务二进制。
- 运行库路径：VirtualRunEnv 的 conanrun 仅聚合声明 run env 的依赖，
  generate() 显式遍历整张依赖图收集全部 lib 目录写入 conanrun_test
  环境，并追加 glib 包 bin（含 glib-compile-schemas）到 PATH。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 被测包 package_type="application"（自包含二进制），Conan 2 不向其
        # 消费者传播依赖：test_package 图中被测包的 host 依赖（glib、
        # libayatana-common）会被标记 Skip、package_folder=None，无法据此
        # 编译消费者或拼装运行库路径。这里显式声明本用例真正需要的两项
        # host 依赖（版本与主配方一致）：
        #   - glib：test_consumer.c 的头文件与链接库（gio/glib-unix 同源）
        #   - libayatana-common：被测服务二进制运行期 NEEDED 的共享库
        self.requires("glib/2.88.0.1")
        self.requires("libayatana-common/0.9.13")

    def generate(self):
        """构造 conanrun_test 环境：全部依赖 lib 目录 -> LD_LIBRARY_PATH，
        glib 包 bin（glib-compile-schemas）-> PATH。"""
        env = Environment()
        env.define_path("LD_LIBRARY_PATH", self._collect_lib_dirs())

        # PATH 聚合：glib 的 bin 提供 glib-compile-schemas/gdbus-codegen
        bin_dirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for bindir in getattr(dep.cpp_info, "bindirs", None) or ["bin"]:
                path = os.path.join(folder, bindir)
                if os.path.isdir(path) and path not in bin_dirs:
                    bin_dirs.append(path)
        if bin_dirs:
            env.append_path("PATH", os.pathsep.join(bin_dirs))

        env.vars(self).save_script("conanrun_test")

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行被测二进制，跳过端到端测试")
            return

        # 1. 定位被测服务二进制
        pkg = self._host_dep("ayatana-indicator-power").package_folder
        binary = self._find_binary(pkg)
        if not binary:
            self.output.error(f"未找到服务二进制 (pkg={pkg})")
            sys.exit(1)
        self.output.info(f"被测服务二进制: {binary}")

        # 2. 编译 GSettings schema（服务启动需要）
        schema_dir = self._prepare_schema(pkg)
        if not schema_dir:
            self.output.error("未找到/无法编译 GSettings schema")
            sys.exit(1)

        # 3. 编译真实消费者程序 test_consumer.c
        consumer = self._build_consumer()
        if not consumer:
            self.output.error("test_consumer.c 编译失败")
            sys.exit(1)

        # 4. 端到端运行：消费者拉起服务（AIP_TEST_BUS_ADDR 指向私有 peer），
        #    驱动 Testing mock 电池并断言 Battery 属性
        env = {
            "GSETTINGS_SCHEMA_DIR": schema_dir,
            "GSETTINGS_BACKEND": "memory",
        }
        env_assign = " ".join(f"{k}={v}" for k, v in env.items())
        rc = self.run(
            f'{env_assign} "{consumer}" "{binary}"',
            env="conanrun_test",
            ignore_errors=True,
        )
        if rc != 0:
            self.output.error(f"端到端消费者用例失败 (self.run 退出码 {rc})")
            sys.exit(1)

        self.output.info(
            "✅ 端到端消费者用例通过：真实消费者程序驱动真实服务，"
            "mock 电池 80% → PowerPercentage=80/IsDischarging=true/PowerLevel=ok"
        )

    # ── helpers ──────────────────────────────────────────────

    def _collect_lib_dirs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in getattr(dep.cpp_info, "libdirs", None) or ["lib"]:
                path = os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in lib_dirs:
                    lib_dirs.append(path)
        return lib_dirs

    def _find_binary(self, pkg):
        # 上游 CMake 把服务装到 libexec/ayatana-indicator-power/ 下
        candidates = [
            os.path.join(pkg, "libexec", "ayatana-indicator-power",
                         "ayatana-indicator-power-service"),
            os.path.join(pkg, "libexec", "ayatana-indicator-power-service"),
            os.path.join(pkg, "bin", "ayatana-indicator-power",
                         "ayatana-indicator-power-service"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        for root, _dirs, files in os.walk(pkg):
            if "ayatana-indicator-power-service" in files:
                return os.path.join(root, "ayatana-indicator-power-service")
        return None

    def _prepare_schema(self, pkg):
        """从包内找出 org.ayatana.indicator.power.gschema.xml，用
        glib-compile-schemas 编译到独立目录，返回该目录（失败返回 None）。"""
        schema = None
        for root, _dirs, files in os.walk(pkg):
            if "org.ayatana.indicator.power.gschema.xml" in files:
                schema = os.path.join(root, "org.ayatana.indicator.power.gschema.xml")
                break
        if not schema:
            return None

        out_dir = os.path.join(self.build_folder, "schemas")
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(schema, os.path.join(out_dir, os.path.basename(schema)))

        gcs = shutil.which("glib-compile-schemas")
        if not gcs:
            self.output.error("PATH 中找不到 glib-compile-schemas")
            return None
        rc = self.run(f'"{gcs}" "{out_dir}"', ignore_errors=True)
        if rc != 0 or not os.path.isfile(os.path.join(out_dir, "gschemas.compiled")):
            return None
        return out_dir

    def _host_dep(self, name):
        """返回 host 上下文中具有有效 package_folder 的依赖节点。

        test_package 的依赖图里同名依赖可能同时存在于 host 与 build 上下文
        （如 glib 既是 host 依赖，又经被测包的 tool_requires 出现在 build
        上下文）。build 上下文的二进制在 test_package 中被 skip，
        package_folder 为 None，直接索引 self.dependencies[name] 可能取到它，
        导致 os.path.join(None, ...) 抛 TypeError。"""
        for dep in self.dependencies.values():
            if dep.ref.name == name and getattr(dep, "package_folder", None):
                return dep
        return None

    def _build_consumer(self):
        """用 glib 的 pkg-config 元数据编译 test_consumer.c 到 build 目录。

        Conan 的 PkgConfigDeps 为显式声明的 glib 生成 .pc（含 pcre2/zlib/
        libffi 等静态传递依赖的 Libs），与主配方经 pkg_check_modules 的链接
        方式一致；直接手写 -lglib-2.0 会漏掉静态 glib 的传递依赖。"""
        glib = self._host_dep("glib")
        if glib is None:
            self.output.error("依赖图中未找到可用的 glib 包")
            return None
        pkgconfig = shutil.which("pkg-config")
        if not pkgconfig:
            self.output.error("未找到 pkg-config")
            return None

        src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "test_consumer.c")
        out = os.path.join(self.build_folder, "test_consumer")

        pc_env = {**os.environ,
                  "PKG_CONFIG_PATH": self.generators_folder,
                  "PKG_CONFIG_LIBDIR": self.generators_folder}
        modules = ["glib-2.0", "gobject-2.0", "gio-2.0"]

        def pc_flags(flag):
            proc = subprocess.run([pkgconfig, flag] + modules,
                                  capture_output=True, text=True, env=pc_env)
            if proc.returncode != 0:
                self.output.error(
                    f"pkg-config {flag} 失败: {proc.stderr.strip()}")
                return None
            return proc.stdout.split()

        cflags = pc_flags("--cflags")
        libs = pc_flags("--libs")
        if cflags is None or libs is None:
            return None
        # gio-unix-2.0 是纯头文件补充（glib 包不导出该 .pc）
        gio_unix = os.path.join(glib.package_folder, "include", "gio-unix-2.0")
        if os.path.isdir(gio_unix):
            cflags.append(f"-I{gio_unix}")

        cc = self._resolve_cc()
        cmd = [cc, "-o", out, src] + cflags + libs
        self.output.info("编译消费者: " + " ".join(cmd))
        if subprocess.call(cmd) != 0:
            return None
        return out

    def _resolve_cc(self):
        """定位 C 编译器：优先 profile 的 tools.build:compiler_executables
        （CI worker 的 clang 位于 /data/service/hnp/bin，不在 PATH 上），
        其次 CC 环境变量，最后回退 clang。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c") or os.environ.get("CC") or "clang"
