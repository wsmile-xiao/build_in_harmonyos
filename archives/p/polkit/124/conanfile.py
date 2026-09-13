#!/usr/bin/env python3
"""Conan recipe for polkit 124 — libpolkit-gobject-1 (client library) on OHOS.

polkit provides the D-Bus authorization policy framework: a system service
daemon (polkitd) + two client libraries (libpolkit-gobject-1, libpolkit-agent-1).
Downstream (accountsservice meson.build:161) only links **libpolkit-gobject-1**
to perform authorization checks, so this recipe builds with the upstream
`-Dlibs-only=true` option which SKIPS polkitd / polkitbackend / polkitagent /
programs and produces just the GObject client library.

Build strategy (Meson):
  - requirements: glib/2.84.0.1 (glib/gobject/gio/gio-unix), expat/2.8.2
  - `-Dlibs-only=true`        -> only src/polkit (libpolkit-gobject-1)
  - `-Dauthfw=shadow`         -> skip PAM (polkitd's auth framework; not built
                                 anyway). `cc.find_library('crypt')` resolves
                                 against the OHOS sysroot libcrypt.a.
  - `-Dintrospection=false -Dtests=false -Dexamples=false -Dman=false
    -Dgtk_doc=false`          -> no GIR / docs / tests
  - js_engine is auto-cleared by libs-only (no mozjs/duktape needed)
  - session_tracking defaults to ConsoleKit -> no systemd/libelogind

OHOS notes:
  - gnome.mkenums_simple needs the `glib_mkenums` pkg-config variable, which
    PkgConfigDeps does not emit -> augment glib-2.0.pc/gobject-2.0.pc (same
    pattern as atk recipe).
  - polkit's meson also queries `dependency('gio-unix-2.0')`; the glib conan
    package ships gio-unix-2.0.pc under lib/pkgconfig -> appended to the meson
    native file's pkg_config_path.
  - Built .so libraries are signed with the OHOS binary-sign-tool so the
    dynamic linker can load them (same as atk recipe).
"""
import glob
import os
import shutil
import sys
import tarfile
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# OHOS SDK LLVM toolchain root. The SDK's lld is linked against libxml2.so.16
# which it locates via RUNPATH ($ORIGIN/../lib); the OHOS dynamic loader searches
# LD_LIBRARY_PATH BEFORE RUNPATH, so a foreign libxml2.so.16 leaked into the
# environment (e.g. the CI sqlite3 shim's LD_LIBRARY_PATH) would shadow the SDK's
# bundled copy and break the linker. We prepend the SDK's llvm/lib so lld always
# resolves its own libxml2 first. Same SDK layout assumed in _inject_meson_tools.
_OHOS_SDK_LLVM_ROOT = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"


class PolkitConan(ConanFile):
    name = "polkit"
    version = "124"
    description = "PolicyKit — D-Bus authorization policy framework (client library libpolkit-gobject-1)"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/polkit/"
    url = "https://gitlab.freedesktop.org/polkit/polkit"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # expat is asserted unconditionally by polkit's top-level meson.build at
        # configure time (even in libs-only mode), but libpolkit-gobject-1 does
        # NOT link it (only polkitd's XML policy parsing uses expat). Keep it a
        # private dependency: not propagated to consumers, which also avoids the
        # Conan "direct dependency not used by cpp_info.requires" check (same
        # pattern as at-spi2-core's libxml2).
        self.requires("expat/2.8.2", visible=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly (dbus recipe pattern).
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)
        # Pre-extract the bundled mocklibc wrap archives (subprojects/packagecache/)
        # into subprojects/mocklibc-1.0/ so meson uses the local sources offline
        # (wrap_mode=nodownload) and the conandata patch can fix OHOS portability
        # (fgetgrent/fgetpwent are missing from the musl-based OHOS libc headers).
        with tarfile.open("subprojects/packagecache/mocklibc-1.0.tar.gz") as _tf:
            _tf.extractall("subprojects")
        with zipfile.ZipFile("subprojects/packagecache/mocklibc-1.0-2-wrap.zip") as _zf:
            _zf.extractall("subprojects")
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["libs-only"] = True
        toolchain.project_options["authfw"] = "shadow"
        toolchain.project_options["introspection"] = False
        # Upstream unit tests (test/polkit/: polkitunixusertest, polkitunixgrouptest,
        # polkitunixnetgrouptest, polkitidentitytest) are pure GObject client-library
        # tests that run via LD_PRELOAD mocklibc (no polkitd / D-Bus system bus).
        # mocklibc wrap files ship in the tarball's subprojects/packagecache/, so
        # wrap_mode=nodownload still resolves them offline. Built and executed below
        # in build() via meson.test().
        toolchain.project_options["tests"] = True
        toolchain.project_options["examples"] = False
        toolchain.project_options["man"] = False
        toolchain.project_options["gtk_doc"] = False
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Run the 4 upstream unit tests (test/polkit/) on the OHOS host.
            # They execute via LD_PRELOAD mocklibc (no polkitd / D-Bus system bus).
            meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._ensure_library_aliases(os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["polkit-gobject-1"]
        self.cpp_info.includedirs = ["include/polkit-1"]
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        self.cpp_info.set_property("cmake_file_name", "polkit")
        self.cpp_info.set_property("cmake_target_name", "polkit::polkit")
        self.cpp_info.set_property("pkg_config_name", "polkit-gobject-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in the atk 2.38.0.1.1 recipe) ────────────

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        sdk_llvm_lib = os.path.join(_OHOS_SDK_LLVM_ROOT, "lib")
        if os.path.isdir(sdk_llvm_lib):
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def _append_dependency_pkg_config_paths(self):
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

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
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
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _augment_glib_pkg_config(self):
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        variables = {
            "glib-2.0": [
                f"glib_mkenums={glib_mkenums}",
                f"glib_genmarshal={glib_genmarshal}",
                "gobject_query=${bindir}/gobject-query",
            ],
            "gobject-2.0": [
                f"glib_mkenums={glib_mkenums}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if not inserted:
                continue
            name_index = content.find("\nName:")
            addition = "\n" + "\n".join(inserted)
            if name_index >= 0:
                content = content[:name_index] + addition + content[name_index:]
            else:
                content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _create_python_tool_wrapper(self, tool_name):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
        wrapper_path = os.path.join(self.generators_folder, f"{tool_name}-python")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _ensure_library_aliases(self, library_dir):
        if not os.path.isdir(library_dir):
            return
        candidates = [
            path for path in glob.glob(os.path.join(library_dir, "libpolkit-gobject-1.so.*"))
            if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path)
        ]
        if not candidates:
            return
        source = sorted(candidates, key=len, reverse=True)[0]
        for alias in ("libpolkit-gobject-1.so.0", "libpolkit-gobject-1.so"):
            destination = os.path.join(library_dir, alias)
            if os.path.exists(destination):
                continue
            try:
                os.symlink(os.path.basename(source), destination)
            except (OSError, NotImplementedError):
                shutil.copy2(source, destination)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                    targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
