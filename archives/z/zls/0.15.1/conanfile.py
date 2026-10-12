#!/usr/bin/env python3
"""Conan recipe for zls (zigtools/zls) 0.15.1.

ZLS is a non-official Zig language server: a pure-Zig project producing a
single static executable. It strictly pins Zig 0.15.x
(build.zig: minimum_build_zig_version = "0.15.1"; 0.16.x / 0.14.x hit an
@compileError), so it builds with the zig/0.15.2 tool.

Key OHOS adaptations:
  * The non-lazy build.zig.zon dependencies (known-folders, diffz, lsp-kit)
    are vendored into the source tree at the source() stage with pinned
    SHA256 (conandata.yml `zig_dependencies`) and referenced via local
    .path entries (patches/0001-...), so neither `zig build` nor the test
    steps perform network fetches on OHOS runners (minizign 0.1.13 paradigm).
  * Zig's native (host) libc probing on OHOS consults the system OHOS SDK
    clang (CC/CXX env) and injects OHOS sysroot include dirs whose stdint.h
    needs musl bits/alltypes.h which Zig cannot resolve. Clearing CC / CXX /
    CFLAGS / CPPFLAGS / ... in build() lets Zig use its bundled headers
    (flow-control 0.7.2 precedent). zls is pure Zig (no C sources), but the
    build runner and test runner are host executables, so the env is still
    cleared defensively.
  * Every spawned ELF must be code-signed on OHOS. The zig/0.15.2 wrapper
    auto-signs compiler-generated executables under ZIG_OHOS_SIGN_ROOTS
    (zig caches, zig-out); the final zig-out/bin/zls is signed again in
    package() via binary-sign-tool (flow-control/minizign paradigm).
  * Upstream tests run inside build(): `zig build test` executes the
    tests/tests.zig unit suite, the src/ module tests, the 23 analysis
    cases (tests/analysis) and — because the device build is the host
    target — the 10 build-runner cases (tests/build_runner_cases).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZlsConan(ConanFile):
    name = "zls"
    version = "0.15.1"
    description = "Zig Language Server (ZLS) - a non-official language server for Zig"
    license = "MIT"
    homepage = "https://github.com/zigtools/zls"
    url = "https://github.com/zigtools/zls"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("zig/0.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is currently prepared for Linux/OHOS native builds"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor the pinned Zig package dependencies into <source>/deps/.
        deps_dir = os.path.join(self.source_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        for dep_name, dep in self.conan_data["zig_dependencies"].items():
            get(
                self,
                dep["url"],
                filename=dep["filename"],
                sha256=dep["sha256"],
                strip_root=True,
                destination=os.path.join(deps_dir, dep_name),
            )
        # Apply conandata patches AFTER source processing: 0001 rewrites the
        # build.zig.zon dependency entries (.url + .hash) to local .path refs
        # pointing at the vendored deps/ tree above, so `zig build` performs
        # zero network fetches. (flow-control 0.7.2 L57 / minizign 0.1.13 L45
        # paradigm.)
        apply_conandata_patches(self)

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def _find_ohos_tool(self, env_name, command, fallback):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _sign_elf(self, binary):
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}" 2>/dev/null || true')
        if not signer:
            self.output.warning("binary-sign-tool not found; zls may require manual signing on OHOS")
            return
        signed = f"{binary}.signed"
        self.run(f'"{signer}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1')
        shutil.move(signed, binary)
        os.chmod(binary, 0o755)

    def _zig(self):
        zig_pkg = self.dependencies.build["zig"].package_folder
        zig = os.path.join(zig_pkg, "bin", "zig")
        if os.path.exists(zig):
            return zig
        found = shutil.which("zig")
        if found:
            return found
        raise ConanInvalidConfiguration("zig/0.15.2 is required but no zig executable was found")

    def _zig_env(self):
        # CRITICAL adaptation (flow-control 0.7.2 precedent): Zig's host libc
        # probing on OHOS consults the system OHOS SDK clang (CC/CXX env) and
        # injects OHOS sysroot includes that break musl header resolution.
        # Clear them so Zig uses its own bundled headers.
        for var in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "CPLUS_INCLUDE_PATH", "C_INCLUDE_PATH"):
            os.environ.pop(var, None)

        global_cache = os.path.join(self.build_folder, "zig-global-cache")
        local_cache = os.path.join(self.build_folder, "zig-local-cache")
        os.makedirs(global_cache, exist_ok=True)
        os.makedirs(local_cache, exist_ok=True)
        os.environ["ZIG_GLOBAL_CACHE_DIR"] = global_cache
        os.environ["ZIG_LOCAL_CACHE_DIR"] = local_cache
        # The zig/0.15.2 wrapper auto-signs compiler-spawned ELFs under these
        # roots (build runners, test binaries); zig-out holds the final zls.
        os.environ["ZIG_OHOS_SIGN_ROOTS"] = " ".join(
            [global_cache, local_cache, os.path.join(self.source_folder, "zig-out")]
        )
        return global_cache, local_cache

    def build(self):
        self._zig_env()
        zig = self._zig()
        self.run(f'"{zig}" version', env="conanbuild")
        # ReleaseSafe matches upstream's production build mode for tagged
        # releases. Dependencies are vendored (no network fetches).
        self.run(
            f'"{zig}" build -Doptimize=ReleaseSafe --summary all',
            env="conanbuild",
        )
        # Upstream official test entry point. On a native (host) build this
        # runs: tests/tests.zig unit suite, src/ module tests, the analysis
        # cases (tests/analysis) and the build-runner cases
        # (tests/build_runner_cases).
        self.run(
            f'"{zig}" build test -Doptimize=ReleaseSafe --summary all',
            env="conanbuild",
        )

    def package(self):
        # zls is a standalone application: zig-out/bin/zls.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        zls_bin = os.path.join(self.source_folder, "zig-out", "bin", "zls")
        if not os.path.exists(zls_bin):
            raise ConanInvalidConfiguration(
                "zls binary was not produced (zig-out/bin/zls missing)"
            )
        copy(self, "zls", src=os.path.join(self.source_folder, "zig-out", "bin"), dst=bin_dir)
        if self._is_ohos():
            packaged = os.path.join(bin_dir, "zls")
            self._sign_elf(packaged)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
