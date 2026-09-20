#!/usr/bin/env python3
"""Conan recipe — libvdpau 1.5 (Meson).

VDPAU wrapper library (Video Decode and Presentation API for Unix),
MIT, https://gitlab.freedesktop.org/vdpau/libvdpau

The wrapper dispatches every public entry point through dlopen(): it loads a
backend driver (libvdpau_<driver>.so.1) from VDPAU_DRIVER_PATH/VDPAU_MODULEDIR
and, when VDPAU_TRACE is set, the libvdpau_trace.so.1 trace module. Upstream
meson.build therefore hardcodes shared_library() for both targets; no static
option is offered (a static build is architecturally impossible, not trimmed).

Both optional features are kept enabled:
  * DRI2 driver-name query (-Ddri2=true): needs dri2proto/xorgproto headers
    and libxext (mesa_dri2.c is compiled in, Xext extension client path).
  * trace library: always built by upstream, installed to lib/vdpau/.
Documentation (doxygen html) is disabled; it is not part of the library API.
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibvdpauConan(ConanFile):
    name = "libvdpau"
    version = "1.5"
    description = "VDPAU wrapper library: Video Decode and Presentation API for Unix"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/vdpau/libvdpau"
    url = "https://gitlab.freedesktop.org/vdpau/libvdpau"

    # dlopen dispatch design → always shared; static is architecturally
    # impossible (upstream hardcodes shared_library(), not trimmed here).
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    # No `shared` option: upstream meson.build hardcodes shared_library() for
    # both targets; a static build is not possible.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libvdpau.so DT_NEEDED libX11.so.6; vdpau_x11.h includes <X11/Xlib.h>
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        # DRI2 path links libXext (Xext.h/extutil.h extension client helpers)
        self.requires("libxext/6.4.0.1", transitive_libs=True)
        # dri2proto.pc + X11/extensions/dri2{proto,tokens}.h for mesa_dri2.c
        self.requires("xorgproto/2025.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libvdpau supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # Runtime env (deps' libdirs in LD_LIBRARY_PATH) for the upstream
        # meson test in build(): the default conanbuild env does not carry
        # host dependencies' libdirs.
        VirtualRunEnv(self).generate()
        tc = MesonToolchain(self)
        # No trimming: DRI2 driver-name query stays enabled (deps resolved
        # from conan: x11 / xext / dri2proto pkg-config modules).
        tc.project_options["dri2"] = "true"
        # doxygen/dot are not tool_requires material; docs are not the API
        tc.project_options["documentation"] = "false"
        # Dependencies come from conan only; never fetch subprojects
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()
        self._extend_meson_pkg_config_path()

    def _extend_meson_pkg_config_path(self):
        """Make dependency-shipped .pc files visible to meson.

        MesonToolchain hardcodes ``pkg_config_path = <generators folder>`` in
        the machine file, and meson REPLACES (not appends) the env
        PKG_CONFIG_PATH with that value when it invokes pkg-config
        (mesonbuild/dependencies/pkgconfig.py, _get_env: env.set(...)).
        .pc directories that a dependency exposes via buildenv_info — e.g.
        xorgproto ships 29 proto pc files (dri2proto.pc, ...) in
        share/pkgconfig — therefore stay invisible to meson even though the
        aggregated conanbuild env lists them. Rewrite the machine-file value
        into a list: generators folder first (conan-generated pc files keep
        precedence), then every dependency's own pkgconfig directories.
        """
        pc_dirs = []
        for dep in self.dependencies.values():
            pkg_folder = getattr(dep, "package_folder", None)
            if not pkg_folder:
                continue
            for sub in ("share/pkgconfig", "lib/pkgconfig"):
                d = os.path.join(pkg_folder, sub)
                if os.path.isdir(d) and glob.glob(os.path.join(d, "*.pc")):
                    pc_dirs.append(d)
        if not pc_dirs:
            return
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            ini = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(ini):
                continue
            with open(ini, encoding="utf-8") as handle:
                content = handle.read()
            m = re.search(r"^(pkg_config_path\s*=\s*)'([^']*)'", content, flags=re.MULTILINE)
            if not m:
                continue
            all_dirs = [m.group(2)] + [d for d in pc_dirs if d != m.group(2)]
            all_dirs = list(dict.fromkeys(all_dirs))
            listing = ", ".join("'%s'" % d for d in all_dirs)
            content = content[: m.start()] + f"{m.group(1)}[{listing}]" + content[m.end() :]
            with open(ini, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _inject_meson_archiver(self):
        """Name the SDK archiver explicitly; CI does not put it on PATH.

        MesonToolchain.generate() may or may not write an ``ar =`` line into
        the native file (depends on whether ``ar`` is in
        ``tools.build:compiler_executables`` conf).  Either way, we must
        ensure the full SDK path is present so Meson does not fall back to
        the bare name ``llvm-ar`` (which is not on PATH on CI workers).
        """
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            compiler = compiler_exes.get("c", "")
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
        if not ar:
            # Fallback: check known OHOS SDK locations
            for sdk_dir in [
                "/data/service/hnp/bin",
                "/usr/local/bin",
                "/usr/bin",
            ]:
                candidate = os.path.join(sdk_dir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(sdk_dir, "llvm-ranlib")
                    ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
                    break
        if not ar:
            raise ConanException("Unable to locate an archiver for Meson")

        ar_path = ar.replace("\\", "/")
        ranlib_path = ranlib.replace("\\", "/") if ranlib else None

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()

            # Case 1: an ar= line already exists → replace it
            if re.search(r"^ar\s*=", content, flags=re.MULTILINE):
                content = re.sub(
                    r"^ar\s*=.*$",
                    f"ar = '{ar_path}'",
                    content,
                    flags=re.MULTILINE,
                )
            # Case 2: [binaries] section exists but no ar= → insert after it
            elif "[binaries]" in content:
                content = content.replace(
                    "[binaries]\n",
                    f"[binaries]\nar = '{ar_path}'\n",
                    1,
                )
            # Case 3: no [binaries] section at all → append one
            else:
                content += f"\n[binaries]\nar = '{ar_path}'\n"

            # Handle ranlib the same way
            if ranlib_path:
                if re.search(r"^ranlib\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^ranlib\s*=.*$",
                        f"ranlib = '{ranlib_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif f"ar = '{ar_path}'\n" in content:
                    content = content.replace(
                        f"ar = '{ar_path}'\n",
                        f"ar = '{ar_path}'\nranlib = '{ranlib_path}'\n",
                        1,
                    )

            with open(native_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream test suite (test/dlclose.c, meson test 'dlclose'): the
        # FD-leak check needs a running X server; without one XOpenDisplay()
        # returns NULL and the test exits 77 (SKIP) by design, so meson
        # reports it as skipped and test() passes. Run it with the run env
        # so the wrapper's dlopen()s of libXext.so.6 and the build-tree
        # libvdpau.so actually resolve (see notes.md, R51 inventory).
        self.run(f'meson test -v -C "{self.build_folder}"', env="conanrun")

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Re-sign installed .so files for OHOS XPM.

        meson install rewrites each installed .so (strips the build rpath),
        which invalidates the linker's embedded OHOS self-signature; the
        loader then rejects every load (dlopen and DT_NEEDED alike) with
        "Permission denied" (ML-0043 scenario, same as cairo). Strip the
        stale .codesign section and self-sign again. Follows symlinks is
        unnecessary: only the real files are rewritten, links keep pointing
        at them. Covers lib/libvdpau.so* and lib/vdpau/libvdpau_trace.so*.
        """
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        sos = [s for s in sos if os.path.isfile(s) and not os.path.islink(s)]
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            # .codesign 段可能不存在，移除为尽力而为；下一步重签硬失败兜底
            self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        # Linkable library is libvdpau.so only; lib/vdpau/libvdpau_trace.so*
        # is a runtime module dlopen()ed by the wrapper (not for -l linking).
        self.cpp_info.libs = ["vdpau"]
        # Public headers: include/vdpau/{vdpau.h,vdpau_x11.h}
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "vdpau")
        self.cpp_info.set_property("cmake_file_name", "vdpau")
        self.cpp_info.set_property("cmake_target_name", "vdpau::vdpau")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
