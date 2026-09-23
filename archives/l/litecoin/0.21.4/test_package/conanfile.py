#!/usr/bin/env python3
"""Conan test_package — litecoin 0.21.4 consumer verification.

L1 test: compile a consumer against the packaged libbitcoinconsensus and
run it (real API calls), then execute the shipped litecoind --version as
the binary smoke test (L2).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LitecoinTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_env(self):
        """LD_LIBRARY_PATH covering every .so the consumer and the node
        binaries need: the litecoin package itself (libbitcoinconsensus),
        the conan shared deps (fmt, libevent, openssl, db), and the OHOS
        SDK libc++_shared.so (fmt links libc++ and the dynamic loader
        resolves it lazily — without it, __gxx_personality_v0 fails to
        relocate)."""
        env = Environment()
        litecoin = self.dependencies["litecoin"].package_folder
        for p in (os.path.join(litecoin, "lib"),):
            if os.path.isdir(p):
                env.append_path("LD_LIBRARY_PATH", p)
        for dep in ("fmt", "libevent", "openssl", "db"):
            if dep in [d.ref.name for d in self.dependencies.values()]:
                lib_dir = os.path.join(self.dependencies[dep].package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.append_path("LD_LIBRARY_PATH", lib_dir)
        libcxx_dirs = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++",
        ]
        for d in libcxx_dirs:
            if os.path.isdir(d):
                env.append_path("LD_LIBRARY_PATH", d)
        return env

    def test(self):
        # NOTE: self.run(..., env="conanrun") *replaces* the environment
        # (dropping the LD_LIBRARY_PATH built below) — the OHOS dynamic
        # loader then cannot find libc++_shared.so / the conan .so deps.
        # Run inside the composed env block instead (inherits PATH etc).
        env = self._runtime_env()
        # upstream unit-test binary is fully statically linked (-static in
        # test_test_litecoin_LDFLAGS: musl libc.a + libc++.a/libunwind.a)
        # — no LD_LIBRARY_PATH needed for it; TMPDIR must point at a
        # writable, correctly-owned dir (bitcoin 31.1.1 precedent: the
        # HMDFS uid-mapped temp dirs under the conan cache make the first
        # test case fail with posix_stat Permission denied, which then
        # cascades AddArg SIGABRT through the whole run).
        env.define("TMPDIR", "/data/storage/el2/base/cache")

        # 1) consumer program (links libbitcoinconsensus, real API calls)
        consumer_bin = os.path.join(self.cpp.build.bindirs[0], "test_litecoin")
        self.output.info(f"Running consumer {consumer_bin}")
        with env.vars(self).apply():
            self.run(f'"{consumer_bin}"')

        # 2) binary smoke test: litecoind --version (full node binary init
        # path incl. bundled leveldb/secp256k1-zkp/libmw link chain)
        package_folder = self.dependencies["litecoin"].package_folder
        litecoind = os.path.join(package_folder, "bin", "litecoind")
        if os.path.isfile(litecoind):
            self.output.info(f"Running {litecoind} --version")
            with env.vars(self).apply():
                self.run(f'"{litecoind}" --version')
        else:
            raise RuntimeError(f"litecoind not found under {package_folder}/bin")

        # 3) UPSTREAM UNIT TESTS — full run of test_litecoin (462 cases:
        # 404 src/test BOOST_AUTO/FIXTURE_TEST_CASE compiled per upstream
        # BITCOIN_TESTS list + 58 MWEB libmw/test cases; wallet/test 36
        # excluded by --disable-wallet). The binary runs natively on
        # OHOS arm64. bitcoin 31.1.1 precedent (archives/b/bitcoin/31.1.1)
        # validated the TMPDIR strategy on this platform; litecoin 0.21's
        # BasicTestingSetup roots every fixture at
        # fs::temp_directory_path()/test_common_litecoin/<rand> (no
        # -testdatadir arg in this vintage — TMPDIR is the only lever).
        test_bin = os.path.join(package_folder, "bin", "test_litecoin")
        if os.path.isfile(test_bin):
            self.output.info(f"Running upstream unit tests: {test_bin}")
            with env.vars(self).apply():
                self.run(f'"{test_bin}"')
        else:
            raise RuntimeError(f"test_litecoin not found under {package_folder}/bin")
