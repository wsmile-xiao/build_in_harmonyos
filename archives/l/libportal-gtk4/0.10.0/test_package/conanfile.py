import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibportalGtk4TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 鸿蒙特有消费者端到端用例需要一条真实 session bus：
        # dbus 包提供 dbus-daemon（TCP 监听，dbus/1.14.10.2 自身 test_package 同款模式）
        self.requires("dbus/1.14.10.2")
        # dbus 配方钉 glib/2.88.3，与被测包闭包（libportal-gtk4 → gtk4 链）
        # 钉的 glib/2.84.0.1.1 版本冲突；dbus-daemon 本体只链接 libexpat/libc
        # （不链接 glib），测试根部 override 统一为被测包钉版，运行时零影响
        # （与主配方顶层 override 同款写法）
        self.requires("glib/2.84.0.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        # Same whitespace-corrupted "/system/lib64" entry workaround as the
        # main recipe: prepend a clean /system/lib64 so host tools (cmake,
        # ninja) can resolve libc++_shared.so inside the conan build env.
        environment = Environment()
        if self.settings.os == "OHOS" and os.path.isdir("/system/lib64"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return environment

    def build(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    # 与 ci/conan 的 OHOS 会话总线一致：TCP 监听 + 匿名认证
    # （dbus/1.14.10.2 test_package 先例；OHOS 无系统 dbus-daemon/AF_UNIX 限制）
    SESSION_BUS_CONF = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <keep_umask/>
  <listen>tcp:host=127.0.0.1,port=0</listen>
  <auth>ANONYMOUS</auth>
  <allow_anonymous/>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""

        # conan's test() runs the binaries through a plain shell; the OHOS
        # musl loader needs the conan-cached shared objects on the runtime
        # library path (alkimia test_package precedent). /system/lib64
        # provides libc++_shared.so needed by the harfbuzz chain.
        lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
        ]
        if str(self.settings.os) == "OHOS":
            lib_dirs.append("/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        os.environ.setdefault("HOME", os.path.expanduser("~"))

        # run with the same clean-LD_LIBRARY_PATH workaround (the conanrun
        # env inherits the whitespace-corrupted session path)
        with self._build_environment().vars(self).apply():
            # 1) L1 断言测试（头文件/链接/符号导出/GObject 类型链，headless 可复现）
            executable = os.path.join(self.cpp.build.bindirs[0], "test_libportal_gtk4" + suffix)
            self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

            # 2) 鸿蒙特有消费者端到端用例：真实 session bus（dbus-daemon TCP）+
            #    同进程 GDBus mock portal 后端 + libportal-gtk4 公开 API 全链路
            #    往返（见 test_portal_e2e.c 头注）
            dbus_pkg = self.dependencies["dbus"].package_folder
            daemon = os.path.join(dbus_pkg, "bin", "dbus-daemon")
            if not os.path.isfile(daemon):
                raise ConanException(f"dbus-daemon not found in dbus package: {dbus_pkg}")

            expat_pkg = self.dependencies["expat"].package_folder
            conf = os.path.join(self.build_folder, "session-tcp.conf")
            with open(conf, "w") as f:
                f.write(self.SESSION_BUS_CONF)
            log_path = os.path.join(self.build_folder, "dbus-daemon.log")

            daemon_env = dict(os.environ)
            daemon_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [os.path.join(expat_pkg, "lib"), os.environ.get("LD_LIBRARY_PATH", "")]
            )
            daemon_proc = subprocess.Popen(
                [daemon, "--config-file=" + conf, "--print-address", "--nofork"],
                stdout=open(log_path, "w"),
                stderr=subprocess.STDOUT,
                env=daemon_env,
            )
            try:
                address = None
                deadline = time.time() + 10
                while time.time() < deadline and daemon_proc.poll() is None:
                    try:
                        with open(log_path, "r") as lf:
                            line = lf.readline()
                            if line and line.startswith("tcp:"):
                                address = line.strip()
                                break
                    except OSError:
                        pass
                    time.sleep(0.2)
                if not address:
                    raise ConanException(
                        f"dbus-daemon did not report a session bus address; see {log_path}"
                    )
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
                self.output.info(f"session bus ready at {address}")
                executable = os.path.join(self.cpp.build.bindirs[0], "test_portal_e2e" + suffix)
                self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
            finally:
                daemon_proc.terminate()
                try:
                    daemon_proc.wait(timeout=3)
                except Exception:
                    daemon_proc.kill()
