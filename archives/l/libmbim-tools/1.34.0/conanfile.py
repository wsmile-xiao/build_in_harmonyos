#!/usr/bin/env python3
"""Conan recipe for libmbim-tools 1.34.0 — mbimcli / mbim-proxy / mbim-network.

Upstream libmbim is *not* an independent "tools" project: the freedesktop
libmbim source tree (<https://gitlab.freedesktop.org/mobile-broadband/libmbim>)
builds its GLib library (libmbim-glib) **and** its user-facing command line
utilities (mbimcli, mbim-proxy, mbim-network) from one meson tree.  This
package (package_type="application") delivers only the tools and drops the
library/headers/pkg-config/introspection data, exactly like the proven
same-source tools-only packages libimobiledevice-progs/1.4.0 and
libcpuid-tool 0.8.0.

The tools are linked against a *static* libmbim-glib (meson
-Ddefault_library=static) so the delivered bin/ payload stays self-contained
and does not depend on a dropped lib/ directory.

Build system: meson (NOT autotools — the dispatch metadata is wrong).

Dependencies: glib-2.0 / gio-2.0 / gio-unix-2.0 / gobject-2.0 (meson.build),
all provided by the single glib package (glib/2.84.0.1).  Optional features
that need extra tooling are disabled:
  -Dbash_completion=false   (no bash-completion package)
  -Dintrospection=false     (no gobject-introspection)
  -Dman=false               (no help2man)

OHOS adaptations:
  - E091: the OHOS kernel UAPI <linux/socket.h> (pulled in via
    <linux/netlink.h>) and the C library <sys/socket.h> both define
    struct sockaddr_storage, which clashes when both are visible.  The four
    netlink/net-port-manager sources guard the UAPI struct with a rename
    macro while the kernel headers are processed (patches 0001-0004).
  - meson is provided through tool_requires(meson/1.11.0) (no meson on PATH).
  - PkgConfigDeps does not emit gio-unix-2.0.pc, but the glib package ships
    it under lib/pkgconfig; both its path and the generators folder are added
    to PKG_CONFIG_PATH / the meson machine file so dependency('gio-unix-2.0')
    resolves.
  - Dependency .pc files may carry bare "prefix=/"; the real prefix is fixed
    up in the package's own .pc files by the PkgConfigDeps output.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibmbimToolsConan(ConanFile):
    name = "libmbim-tools"
    version = "1.34.0"
    description = ("Command-line tools (mbimcli, mbim-proxy, mbim-network) from the "
                   "libmbim Mobile Broadband Interface Model project")
    license = "GPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/ModemManager/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be checked with the ("Linux", "OHOS") tuple form.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmbim-tools is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # meson.build: glib-2.0 >= 2.56, gio-2.0, gobject-2.0 and gio-unix-2.0
        # are all provided by the glib package (gio-unix-2.0.pc lives in the
        # glib package's lib/pkgconfig).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # No meson on the worker PATH; the registry provides meson/1.11.0.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly.
        source_data = self.conan_data["sources"]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""),
            strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # Optional features that the OHOS worker cannot build.
        tc.project_options["bash_completion"] = False
        tc.project_options["introspection"] = False
        tc.project_options["man"] = False
        tc.project_options["gtk_doc"] = False
        tc.project_options["fuzzer"] = False
        # No meson subproject downloads in the sandbox.
        tc.project_options["wrap_mode"] = "nodownload"
        # Static libmbim-glib so the delivered tools do not need a lib/ dir.
        tc.project_options["default_library"] = "static"
        tc.generate()

        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream meson test suite (R51): 8 libmbim-glib unit tests plus
            # the mbimcli test-quectel unit (9 registered tests total).
            meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if not os.path.isdir(os.path.join(self.package_folder, "licenses")):
            copy(self, "COPYING*", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

        # mbim-proxy is installed by upstream into libexec (it is the private
        # proxy daemon of libmbim-glib).  As a tools-only package without the
        # library, expose it on the regular bindir next to mbimcli.
        proxy_src = os.path.join(self.package_folder, "libexec", "mbim-proxy")
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isfile(proxy_src):
            os.makedirs(bin_dir, exist_ok=True)
            shutil.move(proxy_src, os.path.join(bin_dir, "mbim-proxy"))

        # Drop everything that belongs to the library package, not to the tools
        # (libimobiledevice-progs / libcpuid-tool convention).
        for leftover in ("lib", "include", "share", "libexec"):
            shutil.rmtree(os.path.join(self.package_folder, leftover),
                          ignore_errors=True)

        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    # ── helpers (patterns proven in the accountsservice 26.27.3 recipe) ──────

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        # OHOS refuses to exec unsigned ELF binaries ("Operation not permitted",
        # exit 126).  Sign every packaged executable with binary-sign-tool.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        for tool in (signer, readelf):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bin_dir):
            return
        for name in sorted(os.listdir(bin_dir)):
            path = os.path.join(bin_dir, name)
            if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
                continue
            signed = path + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=120,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True, capture_output=True, text=True, timeout=60,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(
                    f"Signed executable {name} has invalid .codesign section count")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        pkg_config_dirs = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    pkg_config_dirs.append(candidate)
        for path in reversed(pkg_config_dirs):
            environment.prepend_path("PKG_CONFIG_PATH", path)
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
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/bin"):
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
                content = content.replace("[binaries]\n",
                                          "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
