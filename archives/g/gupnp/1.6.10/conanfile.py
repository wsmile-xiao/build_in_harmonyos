#!/usr/bin/env python3
"""Conan recipe — gupnp 1.6.10 (Meson).

GUPnP — a GObject-based UPnP library, the core of the GUPnP stack on top of
GSSDP. Adapted to HarmonyOS PC (aarch64, musl, clang).

Build/downstream handling inherits the verified approaches of gssdp 1.6.6 /
libsoup3 3.6.5-r1 (same GLib meson stack):
  - static-only glib2 on ohpcd -> single GObject copy doctrine (g_* stay UND
    and resolve at runtime against the full glib symbol table exported by
    libsoup-3.0.so);
  - never strip shared libraries (embedded .codesign hash breaks, dlopen
    Permission denied);
  - meson install rewrites DT_RUNPATH -> overwrite installed .so with the
    build-tree artifact;
  - OHOS sysroot conflict between linux/netlink.h and sys/socket.h.

gupnp-specific extras (see notes.md):
  - patch 0001 hardens the upstream netlink detection: a standalone
    cc.has_header('linux/rtnetlink.h') is a false positive on OHOS, the
    realistic TU probe fails and the build falls back to the upstream unix
    context manager (ifaddrs based) — no functionality removed;
  - gupnp uses two glib/gio APIs that libsoup-3.0.so does not export
    (g_uuid_string_random, g_zlib_compressor_new): the recipe links a
    recipe-built minimal archive containing exactly those two upstream
    translation units (guuid.c.o + gzlibcompressor.c.o) so their symbols
    resolve at link time while GObject itself stays single-copy.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain

# glib static-lib tokens that must NEVER reach a link command line (the
# single-copy GObject doctrine). See gssdp 1.6.6 notes for the SIGABRT root
# cause analysis behind this list.
GLIB_STATIC_TOKENS = {
    "-lglib-2.0", "-lgobject-2.0", "-lgio-2.0", "-lgmodule-2.0",
    "-lgthread-2.0", "-lffi", "-lintl",
}


class GupnpConan(ConanFile):
    name = "gupnp"
    version = "1.6.10"
    description = "GUPnP — GObject-based UPnP library (core of the GUPnP stack)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gupnp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gupnp meson.build deps: glib-2.0/gio-2.0/gmodule-2.0/gobject-2.0 and
        # gio-unix-2.0 (glib2), libsoup-3.0 (libsoup3), gssdp-1.6 >= 1.6.5
        # (gssdp), libxml-2.0 (libxml2).
        # ⚠️ zlib root-level override pins the PIC variant (1.3.1.1): the
        # published zlib/1.3.1 libz.a is not -fPIC and breaks when linked into
        # a shared .so. Same rationale as gssdp 1.6.6 / libsoup3 3.6.5-r1.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        # Match the exact libsoup3 revision gssdp/1.6.6 was built against —
        # otherwise the graph resolves two libsoup3 recipe revisions.
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("libxml2/2.15.3.1")

    def build_requirements(self):
        # meson probes `ninja --version` at configure time; the build profile
        # PATH already carries a static ninja on this host and CI workers ship
        # their own. Do NOT tool_require the registry ninja (needs
        # libc++_shared.so at load time and fails a clean-env probe) — same
        # decision as gssdp 1.6.6.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # pkg-config surgery helpers                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _build_glib2_pc_fix(self, glib2_pkg, pc_fix_dir):
        """Copies of the glib2 package .pc files with prefix fixed to the real
        package folder, Libs stripped and libffi dropped from Requires.

        The published glib2 package installs its .pc files with prefix=/, so
        Cflags/Libs resolve to /include and /lib. libffi is only reachable via
        the raw glib2 .pc whose own prefix is broken (-L//lib -lffi, unresolvable
        at link time) and nothing needs to link libffi: GObject stays dynamic
        via libsoup-3.0.so (single-copy doctrine).
        """
        src_dir = os.path.join(glib2_pkg, "lib", "pkgconfig")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for pc in os.listdir(src_dir):
            if not pc.endswith(".pc"):
                continue
            text = self._read(os.path.join(src_dir, pc))
            text = re.sub(r"^prefix=.*$", "prefix={}".format(glib2_pkg), text,
                          count=1, flags=re.M)
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            text = re.sub(r"^Libs\.private:.*$", "Libs.private: ", text, flags=re.M)

            def _drop_libffi(match):
                toks = [t.strip() for t in match.group(1).split(",")]
                toks = [t for t in toks if t and t != "libffi"]
                return "Requires: " + ", ".join(toks)

            text = re.sub(r"^Requires:(.*)$", _drop_libffi, text, flags=re.M)
            self._write(os.path.join(pc_fix_dir, pc), text)

    def _strip_glib_from_generated_pc(self, name):
        """Token-level removal of the static-glib list that PkgConfigDeps
        inlines into the libsoup-3.0.pc / gssdp-1.6.pc generators output (the
        published libsoup3 recipe appends the whole glib static lib list to
        its cpp_info.libs). Keeps -lsoup-3.0 / -lgssdp-1.6 themselves.
        """
        path = os.path.join(self.generators_folder, name)
        if not os.path.isfile(path):
            return
        out = []
        for line in self._read(path).splitlines(True):
            match = re.match(r"^(Libs:)(.*)$", line)
            if match:
                kept = [t for t in match.group(2).split()
                        if t not in GLIB_STATIC_TOKENS]
                line = "Libs: " + " ".join(kept) + "\n"
            match = re.match(r"^(Requires:)(.*)$", line)
            if match:
                toks = [t for t in match.group(2).split() if t != "glib-2.0"]
                line = "Requires: " + " ".join(toks) + "\n"
            out.append(line)
        self._write(path, "".join(out))

    def _build_glib_min_archive(self, glib2_pkg, tools):
        """gupnp calls two glib/gio APIs that libsoup-3.0.so does not export:
        g_uuid_string_random (gupnp-service.c SID generation) and
        g_zlib_compressor_new (http-headers.c gzip body support). With the
        static-glib link lists stripped, those two symbols would stay
        unresolved under meson's default -Wl,--no-undefined.

        Instead of pulling whole static archives (which cascades into most of
        glib/gio), extract exactly the two upstream translation units that
        define them — guuid.c.o (libglib-2.0.a) and gzlibcompressor.c.o
        (libgio-2.0.a) — into a recipe-local archive. GObject itself is NOT
        part of that archive: the GType system stays single-copy (all
        g_type_*/g_object_* references of both members resolve against the
        libsoup-3.0.so exports, verified with nm against the published stack).
        """
        glib_lib = os.path.join(glib2_pkg, "lib")
        members_dir = os.path.join(self.build_folder, "glib-min-members")
        os.makedirs(members_dir, exist_ok=True)
        extractions = (
            ("libglib-2.0.a", "guuid.c.o"),
            ("libgio-2.0.a", "gzlibcompressor.c.o"),
        )
        for archive, member in extractions:
            src = os.path.join(glib_lib, archive)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(
                    "glib2 package is missing {}: {}".format(archive, src))
            subprocess.run([tools["ar"], "x", src, member],
                           cwd=members_dir, check=True)
        subprocess.run([tools["ar"], "qc", "libglib-min.a",
                        "guuid.c.o", "gzlibcompressor.c.o"],
                       cwd=members_dir, check=True)
        return members_dir

    # ------------------------------------------------------------------ #

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # not on its PATH; meson probes them and aborts. Pin the real tools by
        # absolute PATH and drop the broken env values (same as
        # glib2/2.88.0, libsoup3/3.6.5-r1, gssdp/1.6.6).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name)
                 for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not in PATH: {}".format(", ".join(missing)))

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ never strip shared libraries: the OHOS loader verifies the
        # embedded .codesign hash against the file content; strip rewrites the
        # .so and dlopen fails with Permission denied (libsoup3 evidence).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = \
            "shared" if self.options.shared else "static"
        # gupnp meson options: introspection/vapi are gobject-introspection
        # (cross-compile disable), gtk_doc needs gi-docgen, examples are demos
        # (library package; test_package is the real consumer). context_manager
        # keeps its upstream default 'system': patch 0001 makes the netlink
        # probe honest, so this selects the upstream unix context manager.
        for opt in ("gtk_doc", "introspection", "vapi", "examples"):
            tc.project_options[opt] = "false"

        glib2 = self.dependencies.get("glib2")
        if not (glib2 and glib2.package_folder):
            raise ConanInvalidConfiguration("glib2 dependency not resolved")
        glib2_pkg = glib2.package_folder

        # 1) glib2 .pc copies with fixed prefix / stripped Libs / no libffi.
        pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
        self._build_glib2_pc_fix(glib2_pkg, pc_fix_dir)

        # 2) generators post-processing (PkgConfigDeps output):
        #    - glib-2.0.pc: Libs must not carry the static-glib list; point it
        #      at the minimal members archive instead; Requires emptied
        #      (pcre2/zlib static archives must not enter the link either);
        #      append the gnome.mkenums tool variables meson looks up via
        #      pkg-config when it resolves glib_mkenums.
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        members_dir = self._build_glib_min_archive(glib2_pkg, tools)
        if not os.path.isfile(glib_pc):
            raise ConanInvalidConfiguration(
                "PkgConfigDeps did not generate glib-2.0.pc in {}".format(
                    self.generators_folder))
        text = self._read(glib_pc)
        text = re.sub(r"^Libs:.*$",
                      'Libs: -L"{}" -lglib-min'.format(members_dir),
                      text, flags=re.M)
        text = re.sub(r"^Requires:.*$", "Requires: ", text, flags=re.M)
        glib_bin = os.path.join(glib2_pkg, "bin")
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                     "glib-compile-resources", "glib-compile-schemas"):
            if os.path.isfile(os.path.join(glib_bin, tool)):
                var = "glib_mkenums" if tool == "glib-mkenums" \
                    else tool.replace("-", "_")
                text += "{}={}/{}\n".format(var, glib_bin, tool)
        self._write(glib_pc, text)
        # 3) libsoup-3.0.pc / gssdp-1.6.pc: token-strip the inlined static-glib
        #    list (keeps -lsoup-3.0 / -lgssdp-1.6 / -lxml2 and system libs).
        for name in ("libsoup-3.0.pc", "gssdp-1.6.pc"):
            self._strip_glib_from_generated_pc(name)

        # meson needs the gobject-2.0/gio-2.0/gio-unix-2.0/gmodule-*.pc modules
        # gupnp requests individually — only the glib2 package ships them
        # (PkgConfigDeps generates a single glib-2.0.pc). Prepend the fixed
        # copies so the broken prefix=/ raw ones are never used.
        extra_pc = [pc_fix_dir, os.path.join(glib2_pkg, "lib", "pkgconfig")]
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        # gnome.mkenums() also honours the native-file [binaries] section; pin
        # the glib2 package tools there as well (gssdp precedent).
        if os.path.isdir(glib_bin):
            self.buildenv_info.prepend_path("PATH", glib_bin)
            for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                         "glib-compile-resources", "glib-compile-schemas"):
                tool_path = os.path.join(glib_bin, tool)
                if os.path.isfile(tool_path):
                    tc.binaries[tool] = tool_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not "
                "runnable on the build host)")
        else:
            if hasattr(os, "uname") and \
                    os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # Upstream tests do SSDP/UPnP over loopback; run them
                    # natively on the OHOS device with a generous timeout
                    # (CI workers are slow; service-proxy alone took ~30 s
                    # locally).
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild".format(build_folder)
                    )

                meson.test = _ohos_meson_test
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install cleans DT_RUNPATH by overwriting bytes inside
        # .dynstr and dropping the entry, which invalidates the embedded
        # .codesign hash -> dlopen Permission denied (libsoup3 evidence).
        # Overwrite the installed .so with the untouched build-tree artifact.
        if self.options.shared:
            _lib = "libgupnp-1.6.so.0.106.10"
            _src = os.path.join(self.build_folder, "libgupnp", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["gupnp-1.6"]
        # headers install to include/gupnp-1.6/libgupnp/; consumers use
        #   #include <libgupnp/gupnp.h>
        self.cpp_info.includedirs = ["include/gupnp-1.6"]
        # the package also ships the upstream gupnp-binding-tool-1.6 CLI
        # (pure-python, installed to bin/) — declare it so consumers get the
        # bin path and the package self-describes as lib+CLI (PF8/R38 pairing
        # with the software-level commands.json).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # ⚠️ CMakeDeps generates empty data for TRANSITIVE deps (conan 2.29),
        # so expose the dependency include dirs here to let consumers compile:
        # gupnp public headers include glib/gio/gobject, libsoup, gssdp and
        # libxml2 headers. libs stay "gupnp-1.6" only — glib/gobject/soup/xml
        # symbols resolve through the NEEDED chain (single GObject copy).
        for depname in ("glib2", "libsoup3", "gssdp", "libxml2"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.cpp_info.includedirs.append(
                    os.path.join(dep.package_folder, "include"))
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                if depname == "glib2":
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "include", "glib-2.0"))
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "lib", "glib-2.0",
                                     "include"))
                self.cpp_info.libdirs.append(
                    os.path.join(dep.package_folder, "lib"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps needs the cmake
        # names explicitly (same as gssdp).
        self.cpp_info.set_property("pkg_config_name", "gupnp-1.6")
        self.cpp_info.set_property("cmake_file_name", "gupnp-1.6")
        self.cpp_info.set_property("cmake_target_name", "gupnp-1.6::gupnp-1.6")
