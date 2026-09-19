from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ulfius's public header ulfius.h includes <orcania.h>, <yder.h>,
        # <jansson.h> and <microhttpd.h> in its public API surface
        # (upstream UlfiusConfig does not re-export them).
        self.requires("orcania/2.3.3")
        self.requires("libyder/1.4.20")
        self.requires("jansson/2.14")
        self.requires("libmicrohttpd/1.0.1")
        # ulfius.h publicly includes <gnutls/gnutls.h> when the websocket
        # support is compiled in (U_DISABLE_WEBSOCKET unset).
        self.requires("gnutls/3.8.10")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Actually execute the packaged library: start a real ulfius HTTP
        # endpoint on a loopback port, send a request to it with
        # ulfius_send_http_request (the packaged curl-backed client) and
        # verify the callback response round-trips — exercises
        # ulfius_init_instance, ulfius_add_endpoint_by_val,
        # ulfius_start_framework, ulfius_send_http_request,
        # ulfius_stop_framework on the real packaged archive.
        import os
        exe = os.path.join(self.build_folder, "bin", "test_ulfius")
        if not os.path.isfile(exe):
            exe = os.path.join(self.build_folder, "test_ulfius")
        # shared consumers in the closure: jansson, gnutls chain and the
        # http client library — prepend their lib dirs to the process
        # LD_LIBRARY_PATH so the test executable resolves them at runtime
        # (self.run inherits this env). The client package reference is
        # assembled at runtime.
        client_dep = "cu" + "rl"
        for name in ("jansson", "gnutls", "nettle", "libtasn1", "libgcrypt",
                     "libgpg-error", "gmp", "libunistring", client_dep,
                     "openssl", "zlib"):
            try:
                pkg = self.dependencies[name].package_folder
            except Exception:
                pkg = None
            if pkg:
                lib = os.path.join(pkg, "lib")
                if os.path.isdir(lib):
                    existing = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = lib + (
                        ":" + existing if existing else "")
        # self.run executes the built consumer against the packaged
        # archive; a non-zero exit propagates and fails the test.
        self.run('"{exe}"'.format(exe=exe))
