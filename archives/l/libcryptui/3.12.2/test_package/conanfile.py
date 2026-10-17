#!/usr/bin/env python3
"""Conan test_package for libcryptui 3.12.2 — 消费者用例（L1）。

构建并**真实运行** test_libcryptui（16 项 TAP 断言）：链接被测产物
libcryptui.so、包含安装后的公共头（并按上游要求定义
LIBCRYPTUI_API_SUBJECT_TO_CHANGE）、调用库内真实逻辑 cryptui_key_get_base()
与 GObject 类型注册（CryptUIKeyStore : GtkTreeModelSort）。

用 PkgConfigDeps 而非 CMakeDeps：gtk/3.24.43 等扁平配方未声明
cpp_info.requires，CMakeDeps 无法把 pango/harfbuzz 等传递头文件传播给消费者；
pkg_check_modules(cryptui-0.0) 让 pkg-config 解析 .pc 的完整 Requires 链
（gtk+-3.0 gio-2.0 dbus-glib-1），并顺带验证被测包安装的 cryptui-0.0.pc。

运行时库存在性检查基于依赖图解出的目录（而非外部 os.environ）：缺失即失败，
避免"未执行却报 PASS"（gtkspell3 test_package 同款口径）。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibcryptuiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 必须显式带 VirtualRunEnv：显式列出 generators 会替换 conan 默认集，
    # 否则 test() 里 env="conanrun" 拿不到依赖的 LD_LIBRARY_PATH。
    generators = "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 公共头包含 gtk/glib/gio/gobject（cryptui-key-store.h → gtk/gtk.h）；
        # 显式声明直接依赖，保证 test 侧 include/link 与 pkg-config 解析完整。
        self.requires("gtk/3.24.43")
        self.requires("dbus-glib/0.114.1")
        # 上游用例（cryptui-test keyset 模式）运行期需要 session bus：
        # dbus 包提供 dbus-run-session/dbus-daemon。主配方已把依赖图统一为
        # dbus/1.14.10.1（带工具；1.14.10 配方跳过 tools 构建，1.14.10.2 自带
        # glib 会与 gtk 生态冲突），此处声明同版本保证 test 侧直接可见。
        self.requires("dbus/1.14.10.1", visible=True)

    def layout(self):
        cmake_layout(self)

    def _sdk_llvm_libdir(self):
        """定位含 libc++_shared.so 的 SDK llvm/lib（cmake 本身是 C++ 程序）。

        CI shell 前置 ~/usr/local/lib 会遮蔽 ABI 匹配版本 → cmake 启动即
        'Error relocating ... symbol not found'（gtkspell3 test_package 同款探测）。
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        expanded = []
        for cand in dict.fromkeys(candidates):
            expanded.append(cand)
            sub = os.path.join(cand, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                expanded.append(sub)
        for cand in dict.fromkeys(expanded):
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return ""

    def _resolved_lib_dirs(self):
        """解析依赖图实际提供的 lib 目录（供运行时库存在性检查）。"""
        dirs = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                if full not in dirs:
                    dirs.append(full)
        # OHOS HNP 部署布局辅助目录（平台辅助路径，不影响配方产物）
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*",
                        "libintl.so*", "libepoxy.so*", "libc++_shared.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _provides_shared(self, stem):
        """依赖图解出的 lib 目录中是否存在共享库 `stem*`（含版本后缀）。"""
        for libdir in self._resolved_lib_dirs():
            if libdir and glob.glob(os.path.join(libdir, stem + "*")):
                return True
        return False

    def _test_environment(self):
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info("Prepending OHOS SDK runtime path: {}".format(sdk_llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        # PkgConfigDeps 生成的 .pc（含全依赖图）先入 PKG_CONFIG_PATH，
        # 随后各依赖包自身的 lib/pkgconfig（真实安装产物 .pc）前置覆盖，
        # 即 cryptui-0.0.pc 取被测包安装的那一份。
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", full)
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(full, "pkgconfig"))
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*",
                        "libintl.so*", "libepoxy.so*", "libc++_shared.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                env.append_path("LD_LIBRARY_PATH", os.path.dirname(match))
        return env

    def build(self):
        envvars = self._test_environment().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _find_tool(self, name):
        """依赖图 bin/ 中定位工具绝对路径（dbus-run-session / broadwayd）。

        各配方的 cpp_info.bindirs 声明不齐（dbus 等包未声明），因此不信赖
        bindirs：直接探测每个依赖包 package_folder 下的 bin/。
        """
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            candidates = [os.path.join(dependency.package_folder, "bin", name)]
            for bindir in dependency.cpp_info.bindirs or []:
                candidates.append(bindir if os.path.isabs(bindir) else
                                  os.path.join(dependency.package_folder,
                                               bindir, name))
            for candidate in candidates:
                if candidate and os.path.isfile(candidate):
                    return candidate
        return None

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_libcryptui executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_libcryptui")
        if not os.path.isfile(exe):
            raise RuntimeError("test_libcryptui binary missing: {}".format(exe))

        required = [
            "libcryptui.so.0",
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libglib-2.0.so.0",
        ]
        # dbus-glib 在本图谱解析为静态归档（包内仅 libdbus-glib-1.a；实测构建出的
        # libcryptui.so 的 NEEDED 无 libdbus-glib-1.so.2）——符号已静态并入被测库，
        # 运行期无该 .so 可查。仅当依赖图确实提供共享库时才强制校验（若 CI 侧解析
        # 为已发布的共享二进制，本条仍生效）；其余 GTK3/glib 运行库照旧硬校验，
        # 保证 test_libcryptui 真跑（16 项断言）而非空报 PASS。
        if self._provides_shared("libdbus-glib-1.so"):
            required.append("libdbus-glib-1.so.2")
        lib_dirs = self._resolved_lib_dirs()
        missing = [lib for lib in required
                   if not any(os.path.isfile(os.path.join(d, lib))
                              for d in lib_dirs if d)]
        if missing:
            raise RuntimeError(
                "GTK3/dbus-glib runtime libs missing from dependency graph, cannot "
                "run test_libcryptui (16 checks would not execute): {}".format(missing))

        envvars = self._test_environment().vars(self)
        with envvars.apply():
            self.run(exe, env="conanrun")

        # ── 上游测试用例真实执行（rule4：0/1 豁免不再被接受）──
        # 被测包交付 tools/cryptui-test（上游 libcryptui/tests/cryptui-test-ui.c
        # 的 noinst_PROGRAMS，已随包签名）。其 main() 按 argv 选择模式：
        #   plain/normal/symmetric → 弹 GTK 对话框（需真人交互，不可自动化）
        #   keyset → 无 UI：遍历 keyset 并打印（无 seahorse 服务时 keyset
        #   为空，循环体 0 次，正常退出 0）——GTK 栈（gtk_init/broadway 后端/
        #   DBus 会话总线）全链路真实初始化
        # 运行前提三件套均来自依赖图：
        #   dbus-run-session — dbus 包 bin/（提供 session bus）
        #   broadwayd        — gtk 包 bin/（GDK broadway 无头后端守护进程）
        #   GDK_BACKEND=broadway + BROADWAY_DISPLAY=:N
        # 关键平台事实（纠正旧 MANIFEST 的「bind 被平台拒绝」结论）：broadwayd
        # 的 unix socket 落在 $XDG_RUNTIME_DIR（未设则 /tmp）——此前失败的真实
        # 根因是 E002（/tmp 在 HMDFS 只读）而非平台拒绝 unix socket。把
        # XDG_RUNTIME_DIR 指到构建目录内即可正常 bind。
        for dependency in self.dependencies.values():
            if dependency.ref.name == "libcryptui":
                pkg = dependency.package_folder
                break
        else:
            pkg = None
        upstream_bin = os.path.join(pkg or "", "tools", "cryptui-test")
        if not pkg or not os.path.isfile(upstream_bin):
            raise RuntimeError(
                "upstream test binary missing from package: {} "
                "(rule4 requires the upstream test case to actually run)".format(
                    upstream_bin))

        dbus_run_session = self._find_tool("dbus-run-session")
        broadwayd = self._find_tool("broadwayd")
        if not dbus_run_session or not broadwayd:
            raise RuntimeError(
                "dbus-run-session / broadwayd not found in dependency graph "
                "(found: dbus-run-session={}, broadwayd={}) — cannot run the "
                "upstream test case headlessly".format(
                    bool(dbus_run_session), bool(broadwayd)))
        # dbus-run-session 会按 PATH 查找并 exec dbus-daemon；dbus 包内
        # session.conf 也随包交付（share/dbus-1/session.conf）。
        dbus_bindir = os.path.dirname(dbus_run_session)
        dbus_session_conf = os.path.join(
            os.path.dirname(dbus_bindir), "share", "dbus-1", "session.conf")
        if not os.path.isfile(dbus_session_conf):
            raise RuntimeError(
                "dbus session.conf missing from dependency graph: {}".format(
                    dbus_session_conf))

        work = os.path.join(self.build_folder, "upstream-test")
        os.makedirs(work, exist_ok=True)
        # 重新套用 conanrun 环境：上面的 with envvars.apply() 已退出，直接
        # dict(os.environ) 拿到的是不含依赖库 LD_LIBRARY_PATH 的普通环境，
        # cryptui-test 的 libcryptui.so.0/glib 等只能靠 RUNPATH 解析（其
        # RUNPATH 烘焙的是 prefix=/ 的 //lib 与 freetype 等缓存目录，不含
        # libcryptui 自身 libdir）→ 运行期符号解析失败。在 apply() 上下文
        # 内复制环境即可带上完整依赖库搜索路径（消费者测试同款口径）。
        envvars = self._test_environment().vars(self)
        with envvars.apply():
            full_env = dict(os.environ)
        full_env["GDK_BACKEND"] = "broadway"
        full_env["BROADWAY_DISPLAY"] = ":{}".format(
            81 + (os.getpid() % 100))
        full_env["XDG_RUNTIME_DIR"] = work   # broadwayd socket 落点（E002）
        full_env["PATH"] = (os.path.dirname(broadwayd) + os.pathsep +
                            dbus_bindir + os.pathsep +
                            full_env.get("PATH", ""))

        # broadwayd 后台监听，display 名对应 BROADWAY_DISPLAY。必须传
        # env=full_env：其 unix socket 落在 $XDG_RUNTIME_DIR（未设则 /tmp，
        # HMDFS 只读 → bind EACCES → gtk_init 连接失败 exit 1，E002）。
        display = full_env["BROADWAY_DISPLAY"]
        broadway_log = open(os.path.join(work, "broadwayd.log"), "w")
        broadway_proc = subprocess.Popen(
            [broadwayd, display], env=full_env, stdout=broadway_log,
            stderr=subprocess.STDOUT)
        try:
            import time
            time.sleep(1.0)
            # dbus-daemon 的编译期 DATADIR 烘焙的是构建机 conan 缓存绝对路径，
            # 重编变体下失效（实测 "Failed to open <baked>/share/dbus-1/
            # session.conf"）——用 --config-file 显式指向运行时解析的包内配置。
            cmd = [dbus_run_session,
                   "--config-file={}".format(dbus_session_conf),
                   upstream_bin, "keyset"]
            self.output.info("running upstream test case: {}".format(
                " ".join(cmd)))
            with open(os.path.join(work, "upstream-test.log"), "w") as log:
                result = subprocess.run(
                    cmd, env=full_env, cwd=work, stdout=log,
                    stderr=subprocess.STDOUT, timeout=180)
            log_tail = open(
                os.path.join(work, "upstream-test.log")).read()[-600:]
            if result.returncode != 0:
                raise RuntimeError(
                    "upstream cryptui-test (keyset mode) exited {}: {}".format(
                        result.returncode, log_tail))
            self.output.info("upstream test case PASSED (exit 0, GTK/broadway "
                             "stack fully initialized; evidence in {})".format(
                                 os.path.join(work, "upstream-test.log")))
        finally:
            broadway_proc.terminate()
            try:
                broadway_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                broadway_proc.kill()
            broadway_log.close()
