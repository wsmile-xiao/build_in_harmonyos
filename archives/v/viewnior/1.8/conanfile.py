#!/usr/bin/env python3
"""Conan recipe for viewnior 1.8 — simple, fast, elegant GTK+2 image viewer (meson).

HarmonyOS PC (aarch64) adaptation.  Build notes:

* Meson build, C + one C++ TU (uni-exiv2.cpp), GNOME stack deps:
  ``gtk+-2.0`` / ``glib-2.0`` / ``gio-2.0`` / ``gdk-pixbuf-2.0`` /
  ``shared-mime-info``(探测) / ``exiv2`` (all resolved through PkgConfigDeps).
* The dependency graph reuses the published OHOS binaries: gtk2/2.24.33
  (canonical GTK+2 consumer graph, xsane precedent), glib/2.84.0.1,
  gdk-pixbuf/2.44.6.1.1 (W0), exiv2/0.28.7.
* shared-mime-info is NOT a conan requirement: the meson.build only asks
  ``dependency('shared-mime-info', '>= 0.20')`` for a version probe, and its
  conan package ships no .pc / cpp_info.  Adding it to requirements() would
  drag in its glib/2.84.0 pin, which after the force-converge to glib/2.84.0.1
  (blogc/0.20.1 precedent) invalidates the published ohpcd binary's package_id
  and forces a CI source build (build-tests=true) that hits the injected
  tree-magic target's missing gio/gobject link.  A synthesised .pc (below)
  satisfies the probe without the dependency.
* meson's ``gnome.genmarshal`` reads the ``glib_genmarshal`` pkg-config
  variable from glib-2.0.pc; PkgConfigDeps does not emit it, so the variable
  is injected pointing at a python-wrapped copy of glib's glib-genmarshal
  (accountsservice/atk pattern — the OHOS loader rejects bare `#!/usr/bin/env`
  shebangs, so a `#!<python>` wrapper is required).
* ``i18n.gettext('viewnior', preset: 'glib')`` + ``i18n.merge_file`` (desktop
  file) need msgfmt/xgettext → gettext/0.22.5.1 tool_require (VirtualBuildEnv).
* shared-mime-info's conan package ships no .pc and declares no cpp_info, so
  ``shared-mime-info.pc`` is synthesised in generate() (meson needs the
  ``>= 0.20`` version probe).
* exiv2 is a static library (expat+zlib linked in); its PkgConfigDeps .pc has
  no Requires, so ``Requires: expat zlib`` is appended (both .pc are emitted
  as visible transitive deps).
* OHOS has no X server.  Patch 0001 lets ``viewnior --version`` print the
  version before GTK opens the display (output identical to the display path),
  enabling L2 smoke on headless workers (bluefish --selftest precedent).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ViewniorConan(ConanFile):
    name = "viewnior"
    version = "1.8"
    description = "Simple, fast and elegant image viewer (GTK+2)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/hellosiyan/Viewnior"
    url = "https://github.com/hellosiyan/Viewnior"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("viewnior supports OHOS armv8 only")

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        # gtk2 is the canonical GTK+2 consumer entry point (xsane precedent);
        # it transitively brings glib/pango/gdk-pixbuf/cairo/atk/X11.
        self.requires("gtk2/2.24.33", transitive_headers=True, transitive_libs=True)
        # gtk2 链 pin glib/2.84.0.1；shared-mime-info/2.5.1 pin glib/2.84.0 →
        # 以 force 收敛（blogc/0.20.1 同法）。
        self.requires("glib/2.84.0.1", force=True, transitive_headers=True, transitive_libs=True)
        # gdk-pixbuf 经 gtk2 链 pin 为 2.44.6.1（ohpcd 已发布二进制），直接声明
        # 以便 PkgConfigDeps 生成 gdk-pixbuf-2.0.pc（meson dependency）；不 force，
        # 与 gtk2 链保持一致可复用已发布 gtk2 二进制。
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("exiv2/0.28.7")
        # shared-mime-info 仅用于 meson dependency('shared-mime-info', '>= 0.20')
        # 版本探测：其 conan 包不装 .pc 也不声明 cpp_info，_synthesize_shared_mime_info_pc
        # 已合成 Version 2.5.1 的 .pc（nothing is linked），故不引入 requires —— 否则
        # 依赖图会拖入 shared-mime-info 的 glib/2.84.0 pin，与 gtk2 链 glib/2.84.0.1
        # force 收敛后其 ohpcd 已发布二进制（基于 glib/2.84.0）package_id 失效，
        # CI 被迫源码构建（build-tests=true）撞 tree-magic 链接缺陷（缺 gio/gobject）。

    def build_requirements(self):
        # i18n.gettext / i18n.merge_file need the GNU gettext tools
        # (msgfmt/xgettext) on the build PATH.
        self.tool_requires("gettext/0.22.5.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._synthesize_shared_mime_info_pc()
        self._augment_exiv2_pc()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        self._inject_libcxx_include(tc)
        tc.generate()
        self._inject_meson_tools()

    def _build_environment(self):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_elf_files()

    def package_info(self):
        # R38: application with an executable → bin/ + bindirs.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ── glib pkg-config tools (accountsservice/atk pattern) ────────────────

    def _create_python_tool_wrapper(self, tool_name):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return "${bindir}/%s" % tool_name
        wrapper_path = os.path.join(self.generators_folder, "%s-python" % tool_name)
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!%s\n"
                "import runpy\n"
                "import sys\n"
                "sys.argv = [%r] + sys.argv[1:]\n"
                "runpy.run_path(%r, run_name='__main__')\n"
                % (sys.executable, tool_path, tool_path)
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _augment_glib_pkg_config(self):
        # gnome.genmarshal reads the glib_genmarshal variable from glib-2.0.pc;
        # PkgConfigDeps does not emit *_tool variables. Also add -lintl so the
        # g_libintl_* proxy symbols resolve (glib proxy-libintl pattern).
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        variables = {
            "glib-2.0": [f"glib_genmarshal={glib_genmarshal}"],
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
            if inserted:
                addition = "\n" + "\n".join(inserted)
                name_index = content.find("\nName:")
                if name_index >= 0:
                    content = content[:name_index] + addition + content[name_index:]
                else:
                    content = "\n".join(inserted) + "\n" + content
            libs_line = next((line for line in content.splitlines()
                              if line.startswith("Libs:")), None)
            if libs_line is not None and "-lintl" not in libs_line.split():
                content = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _synthesize_shared_mime_info_pc(self):
        # shared-mime-info recipe declares no cpp_info → PkgConfigDeps emits
        # nothing; meson.build asks dependency('shared-mime-info', >= 0.20),
        # so synthesise the .pc (version only — nothing is linked).
        pc_file = os.path.join(self.generators_folder, "shared-mime-info.pc")
        if os.path.isfile(pc_file):
            return
        content = (
            "prefix=/usr\n"
            "\n"
            "Name: shared-mime-info\n"
            "Description: Freedesktop.org shared MIME-info database\n"
            "Version: 2.5.1\n"
        )
        with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _augment_exiv2_pc(self):
        # exiv2 is a static lib; its PkgConfigDeps .pc has no Requires, so the
        # link would miss expat/zlib (both emitted as visible transitive .pc).
        pc_file = os.path.join(self.generators_folder, "exiv2.pc")
        if not os.path.isfile(pc_file):
            self.output.warning("exiv2.pc not generated; skipping Requires patch")
            return
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        if "Requires:" not in content:
            content = content.replace("Libs:", "Requires: expat zlib\nLibs:", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _inject_libcxx_include(self, toolchain):
        # viewnior has one C++ TU (src/uni-exiv2.cpp) which needs the OHOS
        # SDK libc++ headers (<exception> etc.).  The CI profile
        # (ci/conan/profiles/ohos-aarch64) does NOT carry
        # tools.build:cxxflags, so MesonToolchain never adds the include
        # path; only the local ohos-aarch64-local profile does.  Probe the
        # known OHOS SDK libcxx-ohos layouts and inject -isystem into the
        # meson cpp_args so the C++ compile works under both profiles.
        if str(self.settings.os) != "OHOS":
            return
        candidates = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1",
            "/storage/Users/currentUser/ohos-sdk/include/libcxx-ohos/include/c++/v1",
        )
        for include_dir in candidates:
            if not os.path.isfile(os.path.join(include_dir, "__config_site")):
                continue
            if "-isystem" not in toolchain.cpp_args and include_dir not in toolchain.cpp_args:
                toolchain.cpp_args.extend(["-isystem", include_dir])
                self.output.info(
                    "OHOS libc++ include path injected: %s" % include_dir)
            return

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            cpp = compilers.get("cpp") or ""
            # The profile's compiler_executables point at the CI worker layout
            # (/data/service/hnp/bin); on machines where that path does not
            # exist, fall back to the same compiler resolved from PATH (the
            # profile buildenv prepends the real toolchain bin/ to PATH).
            # DRAFT-9639 pattern (minibwa 0.4 _compiler_tools()).
            if cc and not os.path.isfile(cc) and os.path.basename(cc):
                resolved = shutil.which(os.path.basename(cc))
                if resolved:
                    cc = resolved
            if cpp and not os.path.isfile(cpp) and os.path.basename(cpp):
                resolved = shutil.which(os.path.basename(cpp))
                if resolved:
                    cpp = resolved
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir,
                              "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
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
            changed = False
            if cc:
                original_c = f"c = '{compilers.get('c', '')}'"
                if original_c != f"c = '{cc}'":
                    content = content.replace(original_c, f"c = '{cc}'")
                    changed = True
            if cpp:
                original_cpp = f"cpp = '{compilers.get('cpp', '')}'"
                if original_cpp != f"cpp = '{cpp}'":
                    content = content.replace(original_cpp, f"cpp = '{cpp}'")
                    changed = True
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                changed = True
            if changed:
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _sign_elf_files(self):
        # meson install may rewrite the RPATH (dynstr), invalidating the
        # toolchain's link-time .codesign; the OHOS loader then rejects the
        # ELF (EPERM). Re-sign with binary-sign-tool (gdk-pixbuf pattern).
        # The CI worker keeps the tools under /data/service/hnp/bin; on other
        # machines the profile buildenv puts the same toolchain bin/ on PATH,
        # so fall back to PATH resolution (DRAFT-9639 pattern).
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or signer
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy") or objcopy
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        targets = []
        for top in ("bin", "lib"):
            base = os.path.join(self.package_folder, top)
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    path = os.path.join(root, fname)
                    if top == "lib" and not fname.startswith("lib"):
                        continue
                    targets.append(path)
        for f in targets:
            if os.path.islink(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except Exception:
                continue
            if os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=f),
                         env=None, quiet=True, ignore_errors=True)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f),
                     env=None)
