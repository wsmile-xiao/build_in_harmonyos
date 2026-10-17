import os
import subprocess
import sys
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DbusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("c") or compilers.get("cc")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_dbus",
        )
        # r07：dbus 引入 glib 依赖后，test_dbus 运行时需加载
        # libglib-2.0/libgobject-2.0/libgio-2.0 等共享库
        # （libdbus 客户端库已透传依赖），把 glib 库目录写入 os.environ，
        # 否则 "Error loading shared library libgirepository-2.0.so.0" 启动失败。
        # r09：expat 对齐 2.8.2.1 后同样需要注入 expat 库路径（libexpat.so.1）。
        # 注：Conan 2 self.run() 的 env 参数须为列表而非 dict，故直接改 os.environ。
        glib_pkg = self.dependencies["glib"].package_folder
        glib_libdir = os.path.join(glib_pkg, "lib")
        expat_pkg = self.dependencies["expat"].package_folder
        expat_libdir = os.path.join(expat_pkg, "lib")
        os.environ["LD_LIBRARY_PATH"] = (
            glib_libdir + os.pathsep + expat_libdir + os.pathsep
            + os.environ.get("LD_LIBRARY_PATH", "")
        )
        if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            self.run(test_bin, ignore_errors=False)
            return

        # 否则尝试用包内 dbus-daemon 自启动一个 TCP 会话总线并完成往返：
        # OHOS 沙箱可能禁止 AF_UNIX bind，TCP 是等价可运行路径。
        dbus_pkg = self.dependencies["dbus"].package_folder
        daemon = os.path.join(dbus_pkg, "bin", "dbus-daemon")
        if not os.path.isfile(daemon):
            self.output.warning("dbus-daemon not in package; running client-only test")
            self.run(test_bin, ignore_errors=False)
            return

        conf = os.path.join(self.build_folder, "session-tcp.conf")
        with open(conf, "w") as f:
            f.write(
                '<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n'
                ' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                "<busconfig>\n"
                "  <type>session</type>\n"
                "  <keep_umask/>\n"
                "  <listen>tcp:host=127.0.0.1,port=0</listen>\n"
                "  <auth>ANONYMOUS</auth>\n"
                "  <allow_anonymous/>\n"
                "  <policy context=\"default\">\n"
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                "  </policy>\n"
                "</busconfig>\n"
            )
        log_path = os.path.join(self.build_folder, "dbus-daemon.log")
        daemon_proc = subprocess.Popen(
            [daemon, "--config-file=" + conf, "--print-address", "--nofork"],
            stdout=open(log_path, "w"),
            stderr=subprocess.STDOUT,
            env=os.environ,
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
            if address:
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
                self.output.info(f"started dbus-daemon at {address}")
                # 在 daemon 存活期间运行消费方测试（真实会话总线往返）
                self.run(test_bin, ignore_errors=False)
            else:
                self.output.warning("dbus-daemon did not print address; running client-only test")
                self.run(test_bin, ignore_errors=False)
        finally:
            daemon_proc.terminate()
            try:
                daemon_proc.wait(timeout=3)
            except Exception:
                daemon_proc.kill()