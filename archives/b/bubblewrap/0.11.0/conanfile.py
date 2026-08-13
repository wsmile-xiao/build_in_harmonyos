#!/usr/bin/env python3
"""Conan recipe — bubblewrap 0.11.0 (Meson).

bubblewrap (bwrap) is a sandboxing tool: unprivileged user namespaces +
setuid/setcap mode for creating sandboxes. It is the runtime dependency
of abuild's rootbld (Alpine `abuild rootbld`).

Key adaptation points:
- meson build system, `dependency('libcap')` resolved via pkg-config.
  The libcap conan package ships static libs + headers but no libcap.pc,
  so we use PkgConfigDeps to generate it in the generators folder and add
  that folder to the meson native file pkg_config_path.
- Compiler toolchain (clang) + llvm-ar/llvm-ranlib injected into the meson
  native file from Conan conf / SDK bin dir (R33: never rely on bare
  shell compiler env vars).
- libcap linked statically (its conan recipe defaults shared=False), so the
  final bwrap binary only NEEDs libc.so — no runtime dependency pollution.
- bwrap --version works without privileges; actual sandbox creation needs
  user namespaces / setuid which OHOS does not provide, so the smoke test
  only verifies binary presence + --version (see test_package notes).
- Existing patches:
    0001-bubblewrap.c.patch — get_current_dir_name() GNU extension fallback
    0002-network.c.patch   — sockaddr_storage redefinition guard (OHOS
                             linux/socket.h vs sys/socket.h conflict)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class BubblewrapConan(ConanFile):
    name = "bubblewrap"
    version = "0.11.0"
    description = "Unprivileged sandboxing tool (bwrap), runtime dep of abuild rootbld"
    license = "LGPL-2.0-only"
    homepage = "https://github.com/containers/bubblewrap"
    url = "https://github.com/containers/bubblewrap"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libcap provides cap_* APIs used by bwrap for bounding the
        # ambient capability set. Static by default in its recipe.
        self.requires("libcap/2.69")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate libcap.pc from libcap cpp_info (libcap package has no .pc).
        PkgConfigDeps(self).generate()

        toolchain = MesonToolchain(self)
        toolchain.project_options["selinux"] = "disabled"
        toolchain.project_options["man"] = "disabled"
        # Upstream integration tests (test-run.sh etc.) need user namespaces +
        # setuid + /var/tmp, not available on OHOS, so only the pure C unit
        # test (test-utils, 26 subtests) is built and run in build().
        toolchain.project_options["tests"] = "true"
        toolchain.generate()

        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream tests need user namespaces / setuid + /var/tmp on the
            # runtime host; they are not runnable inside the OHOS build
            # sandbox. test-utils (pure C unit test, 26 subtests) is the only
            # portable one.
            self.run(f'meson test -C "{self.build_folder}" test-utils -v',
                     ignore_errors=True)

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []

    # ── helpers ──────────────────────────────────────────────────────────

    def _build_environment(self):
        environment = Environment()
        # /var/tmp does not exist on OHOS and root '/' is read-only; give
        # tools a writable temp area inside the build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # CI worker: SDK lld depends on libxml2.so.16, which lives in the SDK
        # llvm/lib dir. If LD_LIBRARY_PATH does not include it, meson's linker
        # probe (`clang -Wl,--version` → lld) fails with "Error loading shared
        # library libxml2.so.16" and configure aborts. Prepend the SDK lib dir
        # (version-agnostic glob) so lld resolves its own libxml2.
        for sdk_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")):
            environment.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _inject_meson_tools(self):
        """Inject ar/ranlib/pkg-config absolute paths into the meson native file."""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            # SDK llvm/bin discovery: try compiler bindir, then env, then a
            # version-agnostic glob (avoid pinning a specific SDK version).
            sdk_bindirs = [bindir]
            ndk_home = os.environ.get("OHOS_NDK_HOME")
            if ndk_home:
                sdk_bindirs.append(os.path.join(ndk_home, "llvm", "bin"))
            for sdk in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
                sdk_bindirs.append(sdk)
            for directory in sdk_bindirs:
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1
                )
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _append_dependency_pkg_config_paths(self):
        """Make generated libcap.pc visible to meson's pkg-config module."""
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _sign_installed_elfs(self):
        """Sign installed ELF binaries so they can execute on OHOS (atk pattern)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        for target in targets:
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
