#!/usr/bin/env python3
"""Conan recipe — libsecret 0.21.8 (Meson).

GNOME secret management library: libsecret-1 (GObject client bindings for the
org.freedesktop.Secrets D-Bus API, with a local file backend when built with
crypto support) plus the secret-tool command line utility.

Adapted to HarmonyOS PC (aarch64):
  - glib via conan (glib/2.84.0.1, shared — libsecret builds a shared library
    and must link shared glib to honor the Conan-managed dependency chain);
  - crypto backend libgcrypt enabled (file backend: the only functional secret
    store on OHOS, which has no gnome-keyring daemon);
  - introspection/vapi/manpages/gtk_doc/bash-completion/pam/tpm2 disabled;
  - 0.21.8 additions validated on OHOS: linker version script
    (libsecret.map, private symbols hidden — lld supports --version-script),
    file-backend thread safety with flock()-based keyring locking (musl
    provides flock), and the new egg test-dh-length regression test;
  - portability patch 0001: egg-testing scratch dir via g_get_tmp_dir()
    instead of hardcoded /tmp (OHOS /tmp is read-only, E002);
  - portability patch 0002: include <fcntl.h> in secret-file-collection.c —
    the new flock()-based locking uses O_CREAT/O_RDWR, which upstream
    resolves through glibc's transitive include from <sys/file.h>; musl
    headers do not do this;
  - portability patch 0003: secret-tool getpass() declaration (musl provides
    the symbol in the system libc, the SDK headers lack the declaration — same
    gap glib/2.84.0 worked around in its patch 0002).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# OHOS SDK libc.so lacks getpass(); the system musl loader
# (/lib/ld-musl-aarch64.so.1) exports it. secret-tool needs it at link time.
_MUSL_LINK_ARGS = ["-L/lib", "-l:ld-musl-aarch64.so.1"]


class LibsecretConan(ConanFile):
    name = "libsecret"
    version = "0.21.8"
    description = "GNOME library for accessing the Secret Service API (libsecret-1 + secret-tool)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libsecret"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # W0 verified published on ohpcd (conan install --requires probe):
        # glib/2.84.0.1 (pulls libffi/3.4.4, pcre2/10.45, zlib/1.3.1.1),
        # libgcrypt/1.11.0 (pulls libgpg-error/1.55).
        # transitive_headers/libs: libsecret public headers include glib.h /
        # glib-object.h / gio/gio.h — consumers must see glib's include dirs.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libgcrypt/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # NOT on its PATH; meson probes these and aborts at configure. Pin the
        # real tools by ABSOLUTE PATH and drop the broken env values
        # (same fix as glib2/2.88.0 and libsoup3/3.6.5-r2).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        # glib pc compatibility layer (accountsservice/GOA pattern): the
        # glib/2.84.0.1 package installs .pc files with prefix=/ (DESTDIR
        # install), so Cflags/Libs resolve to /include, /lib and tool
        # variables (gdbus_codegen) become //bin/... — meson then fails on
        # gnome.gdbus_codegen / dependency lookup. Copy every glib .pc into
        # the generators folder with prefix rewritten to the real package
        # folder; PKG_CONFIG_PATH resolution prefers these copies.
        self._fix_glib_pc_files()

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # OHOS: the SDK sysroot libc.so lacks getpass() (needed by
        # secret-tool's read_password_tty); the system musl loader
        # /lib/ld-musl-aarch64.so.1 exports it — link against it
        # (same approach as the glib/2.84.0 recipe _MUSL_LINK_ARGS).
        if self.settings.os == "OHOS":
            tc.c_link_args += _MUSL_LINK_ARGS
        # Never strip shared libraries: the OHOS loader verifies the embedded
        # .codesign hash against the file contents (libsoup3 lesson).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]

        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Keep the vendored file backend (crypto=libgcrypt): on OHOS there is
        # no gnome-keyring daemon, the file backend is the only functional
        # secret store (SECRET_BACKEND=file, validated by upstream
        # test-secret-tool.sh in this recipe's build()).
        tc.project_options["crypto"] = "libgcrypt"
        # Not available/needed on OHOS: introspection, vapi, man pages,
        # gtk-doc, bash completion, PAM module, TPM2 stack, gi-docgen wrap.
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["manpage"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["bash_completion"] = "disabled"
        tc.project_options["pam"] = "false"
        tc.project_options["tpm2"] = "false"
        tc.project_options["debugging"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()

        # Add glib/libgcrypt package pc dirs + generators folder to the meson
        # native machine file pkg_config_path (libsoup3 pattern), so meson
        # resolves glib-2.0/gio-unix-2.0/libgcrypt and the mkenums/gdbus
        # tool variables.
        self._inject_pkg_config_paths()

        # glib's bin/ holds the python3 codegen tools (glib-mkenums,
        # glib-genmarshal, gdbus-codegen) needed at build time.
        glib = self.dependencies["glib"]
        glib_bin = os.path.join(glib.package_folder, "bin")
        if os.path.isdir(glib_bin):
            self.buildenv_info.prepend_path("PATH", glib_bin)

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        prefix = self._ninja_env_prefix()
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self.run(
            prefix + 'meson setup --native-file "{nf}" "{bf}" "{sf}" --prefix=/'.format(
                nf=native_file, bf=self.build_folder, sf=self.source_folder),
            env="conanbuild",
        )
        self.run(prefix + 'meson compile -C "{bf}"'.format(bf=self.build_folder), env="conanbuild")
        # Upstream test suite (R34/W3): run on the OHOS build host itself
        # (this recipe is built natively). The full suite registers 17 meson
        # test targets; 8 depend on the python D-Bus mock service (requires a
        # session bus + python dbus/gi modules, absent on OHOS — documented
        # runtime limitation). The 9 runnable targets are executed here:
        # test-hex/4, test-secmem/7, test-dh/8, test-dh-length/1,
        # test-hkdf/7 (egg crypto primitives; test-dh-length is new in
        # 0.21.8 — 2000-trial DH shared-secret length regression),
        # test-attributes/12, test-value/11 (libsecret core),
        # test-file-collection/8 (file backend, incl. 0.21.8 flock-based
        # concurrent-write), test-secret-tool.sh/6 (end-to-end store/lookup/
        # search/clear through the file backend) — 64 TAP subcases total.
        if cross_building(self):
            self.output.info("cross-building: skip upstream meson tests")
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                scratch = os.path.join(self.build_folder, "tmp")
                os.makedirs(scratch, exist_ok=True)
                self.run(
                    self._ninja_env_prefix() +
                    'meson test -v -C "{b}" --timeout-multiplier=16 --no-rebuild '
                    "libsecret:test-hex libsecret:test-secmem libsecret:test-dh "
                    "libsecret:test-dh-length libsecret:test-hkdf "
                    "libsecret:test-attributes "
                    "libsecret:test-value libsecret:test-file-collection "
                    '"libsecret:test-secret-tool.sh"'.format(b=self.build_folder),
                    env="conanbuild",
                )
            else:
                self.output.info("not on OHOS host: skip upstream meson tests")

    def package(self):
        self.run(
            self._ninja_env_prefix() +
            'meson install -C "{bf}" --destdir "{pf}"'.format(
                bf=self.build_folder, pf=self.package_folder),
            env="conanbuild",
        )
        # ⚠ meson install rewrites DT_RUNPATH (overwrites the rpath strings in
        # .dynstr and drops the DT_RUNPATH entry). That modifies the .so
        # contents, invalidating the .codesign hash written at link time —
        # the OHOS loader then rejects it with EPERM/Permission denied
        # (libsoup3 3.6.5-r2 lesson, verified locally: builddir artifact
        # dlopen-OK, installed artifact Permission denied). Restore the
        # pristine link output from the build directory.
        built = os.path.join(self.build_folder, "libsecret", "libsecret-1.so.0.0.0")
        installed = os.path.join(self.package_folder, "lib", "libsecret-1.so.0.0.0")
        if os.path.exists(built):
            shutil.copy2(built, installed)
        # secret-tool keeps its link-time signature: meson install also
        # rewrites its RUNPATH; copy the build output likewise.
        built_tool = os.path.join(self.build_folder, "tool", "secret-tool")
        installed_tool = os.path.join(self.package_folder, "bin", "secret-tool")
        if os.path.exists(built_tool) and os.path.exists(installed_tool):
            shutil.copy2(built_tool, installed_tool)
            os.chmod(installed_tool, 0o755)

    def package_info(self):
        # libsecret-1.so; headers under include/libsecret-1/libsecret
        self.cpp_info.set_property("cmake_file_name", "libsecret-1")
        self.cpp_info.set_property("cmake_target_name", "libsecret-1::libsecret-1")
        self.cpp_info.set_property("pkg_config_name", "libsecret-1")
        self.cpp_info.libs = ["secret-1"]
        self.cpp_info.includedirs = ["include/libsecret-1"]
        # glib/gcrypt are linked via the public headers and the pc
        # Requires chain; Conan components propagate them.
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0",
                                  "glib::gio-2.0", "libgcrypt::libgcrypt"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # secret-tool is shipped in bin/
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ── helpers ─────────────────────────────────────────────────────────────

    def _ninja_env_prefix(self):
        """Inline 'VAR=... PATH=...' prefix for meson commands (glib/2.84
        _run_meson pattern — buildenv_info is written to disk before
        generate() runs, so defining vars there has no effect).

        hnp/bin/ninja is linked against libc++_shared.so (in /system/lib64);
        the raw binary aborts when spawned by meson's subprocess, breaking
        ninja detection. The wrapper under ~/usr/local/bin sets the needed
        LD_LIBRARY_PATH; pin it via NINJA (meson's detect_ninja honors the
        env var first) and prepend its directory to PATH.
        """
        ninja = shutil.which(
            "ninja",
            path=os.path.expanduser("~/usr/local/bin") + os.pathsep + os.environ.get("PATH", ""),
        )
        if ninja and "usr/local/bin" in ninja:
            return 'NINJA="{n}" PATH="{d}:$PATH" TMPDIR="{t}" TMP="{t}" '.format(
                n=ninja, d=os.path.dirname(ninja),
                t=os.path.join(self.build_folder, "tmp"))
        tmpdir = os.path.join(self.build_folder, "tmp")
        return 'TMPDIR="{t}" TMP="{t}" '.format(t=tmpdir)

    def _fix_glib_pc_files(self):
        glib = self.dependencies["glib"]
        glib_pc_dir = os.path.join(glib.package_folder, "lib", "pkgconfig")
        if not os.path.isdir(glib_pc_dir):
            self.output.warning("glib package has no lib/pkgconfig dir")
            return
        for pc_name in os.listdir(glib_pc_dir):
            if not pc_name.endswith(".pc"):
                continue
            src = os.path.join(glib_pc_dir, pc_name)
            dst = os.path.join(self.generators_folder, pc_name)
            with open(src, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            # Only rewrite the leading prefix= line ("/" -> real folder).
            if content.startswith("prefix=/\n"):
                content = "prefix=" + glib.package_folder.replace("\\", "/") + "\n" + content[len("prefix=/\n"):]
            # Drop Requires.private on the conan-managed transitive deps
            # (libpcre2-8/libffi/zlib): their .pc files are not resolvable in
            # the graph when the deps are Skipped binaries, and glib's shared
            # libraries already carry those symbols — the private deps only
            # matter for static linking, which this recipe does not use.
            for priv in ("libpcre2-8", "libffi", "zlib"):
                for line in content.splitlines():
                    if line.startswith("Requires.private:") and priv in line:
                        rest = [t for t in line.split(":", 1)[1].split(",") if priv not in t]
                        if rest:
                            content = content.replace(line, "Requires.private:" + ",".join(rest), 1)
                        else:
                            content = content.replace(line + "\n", "", 1)
                        break
            with open(dst, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _inject_pkg_config_paths(self):
        paths = [self.generators_folder]
        # Walk the whole graph (unfiltered values() = transitive deps too;
        # glib-2.0.pc Requires.private pulls the transitive pcre2/libffi/zlib
        # .pc files, which are not direct requirements of this recipe).
        for dependency in self.dependencies.values():
            if dependency.package_folder is None:  # skipped binaries
                continue
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
            lines = content.splitlines()
            for index, line in enumerate(lines):
                if line.startswith("pkg_config_path = "):
                    lines[index] = replacement
                    break
            else:
                lines.append(replacement)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
