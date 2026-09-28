import os
import socket
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import save

DOC_INDEX = '{"library": "restclient-cpp", "kind": "consumer-test-document"}'


class RestclientCppTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: consumer execution is covered by the HDC device test"
            )
            return

        doc_root = os.path.join(self.build_folder, "www")
        save(self, os.path.join(doc_root, "index.json"), DOC_INDEX)
        server, port = self._serve(doc_root)
        try:
            executable = os.path.join(self.cpp.build.bindir, "test_package")
            self.run('"%s" http://127.0.0.1:%d' % (executable, port), env="conanrun")
        finally:
            server.terminate()
            server.wait(timeout=10)

    def _serve(self, doc_root):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()
        log = open(os.path.join(self.build_folder, "http-server.log"), "w",
                   encoding="utf-8")
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            cwd=doc_root, stdout=log, stderr=log,
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                probe = socket.create_connection(("127.0.0.1", port), timeout=1)
                probe.close()
                return process, port
            except OSError:
                if process.poll() is not None:
                    raise ConanException(
                        "python http.server exited early; see %s" % log.name
                    )
                time.sleep(0.2)
        process.terminate()
        raise ConanException("python http.server did not start on port %d" % port)
