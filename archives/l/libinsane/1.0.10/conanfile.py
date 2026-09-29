#!/usr/bin/env python3
"""Conan recipe - libinsane 1.0.10 (Meson).

OpenPaperwork's scanner image access library: one C API over SANE/TWAIN/WIA plus
a GObject wrapper. Core subproject needs sane-backends unconditionally off-Windows.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibinsaneConan(ConanFile):
    name = "libinsane"
    version = "1.0.10"
    description = (
        "Document scanner image access library that normalises SANE, TWAIN and WIA "
        "device APIs behind one C interface, plus its GObject wrapper"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/World/OpenPaperwork/libinsane"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Hard dependency: subprojects/libinsane/src/meson.build resolves
        # dependency('sane-backends') on every non-Windows host.
        self.requires("sane-backends/1.2.1", transitive_headers=True, transitive_libs=True)
        # subprojects/libinsane-gobject/src/meson.build resolves dependency('gobject-2.0').
        # glib 2.88.x pulls zlib/1.3.2 and the sane-backends graph pins zlib/1.3.1.1
        # ("Version conflict ... originates from glib/2.88.3.1"); 2.84.0.2 is the
        # newest glib that resolves in one graph. Verified by conan install probes.
        self.requires("glib/2.84.0.2", transitive_headers=True, transitive_libs=True)
        # Upstream gates its whole CUnit suite behind dependency('cunit'); it is a
        # build/test-time only dependency, hence private (visible=False).
        self.requires("cunit/2.1.3", visible=False)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _merge_glib_pc_variables(self):
        """Hand meson's gnome module the glib build tools it asks pkg-config for.

        gnome._find_tool('glib-mkenums') reads the 'glib_mkenums' variable of
        glib-2.0 and asks for it with no default, so a .pc without that line
        aborts configure ("Could not get pkg-config variable and no default
        provided for <PkgConfigDependency glib-2.0>", seen at
        src/meson.build:17). Conan's PkgConfigDeps renders glib-2.0.pc out of
        package_info only, so the tool and data variables of glib's own .pc are
        missing; they are merged in here from the dependency's real
        lib/pkgconfig/glib-2.0.pc, which keeps them prefix-relative (the
        generated file already pins prefix to the package folder, so ${bindir}
        resolves inside the cache).

        Naming the tool through PATH is not an option: PATH carries
        /data/service/hnp/bin/glib-mkenums, a glib 2.38.2 perl script whose
        shebang is the literal '#! /usr/bin/perl'. OHOS ships no /usr/bin/perl,
        so meson reports "Program glib-mkenums found: YES" during configure and
        ninja then dies generating enums.h with FileNotFoundError on that very
        path. The absolute path inside the glib package -- a python3 script that
        runs here -- is what the ecosystem already does for this (ayatana-ido
        0.10.4 injects the same file for find_program(GLIB_MKENUMS)). The cached
        dependency package is never mutated; only this build's own copy of the
        .pc is extended.
        """
        origin = None
        for ref in self.dependencies.host.values():
            if str(ref).startswith("glib/"):
                origin = os.path.join(ref.package_folder, "lib", "pkgconfig",
                                      "glib-2.0.pc")
        if not origin or not os.path.isfile(origin):
            raise ConanException("glib-2.0.pc of the glib dependency not found: "
                                 "cannot expose the glib build tools")
        target = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(target):
            hits = glob.glob(os.path.join(self.generators_folder, "**",
                                          "glib-2.0.pc"), recursive=True)
            if not hits:
                raise ConanException("generated glib-2.0.pc not found under %s"
                                     % self.generators_folder)
            target = hits[0]
        current = load(self, target)
        have = set()
        for line in current.splitlines():
            if "=" in line and ":" not in line.split("=", 1)[0]:
                have.add(line.split("=", 1)[0].strip().lower())
        add = []
        for line in load(self, origin).splitlines():
            if "=" not in line or ":" in line.split("=", 1)[0]:
                continue
            key = line.split("=", 1)[0].strip()
            if key.lower() not in have:
                add.append(line.strip())
        if not add:
            return
        if not current.endswith("\n"):
            current += "\n"
        save(self, target, current + "\n".join(add) + "\n")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._merge_glib_pc_variables()
        tc = MesonToolchain(self)
        # Upstream declares no wraps, but nodownload keeps the build hermetic.
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # gnome.generate_gir() resolves dependency('gobject-introspection-1.0')
        # while *configure* runs and gnome.generate_vapi() additionally needs
        # vapigen; neither tool exists in this build environment, so the whole
        # libinsane-gobject subproject aborted at src/meson.build:46 with
        # 'Dependency "gobject-introspection-1.0" not found'. Upstream declares
        # no switch for either, so patches 0001-0003 add the subproject's own
        # 'introspection' and 'gtk_doc' booleans and turn them off here, which
        # is what the sibling GNOME-family recipes do with the options upstream
        # *did* give them (template-glib 3.36.2, libnotify 0.8.3.1, libpeas2
        # 2.2.1). Only build-time artefacts disappear: the typelib, the Vala
        # binding and the gtk-doc HTML. The C and GObject C libraries, headers
        # and pkg-config files are built and installed exactly as upstream.
        # Subproject options must go through MesonToolchain.subproject_options
        # (machine-file section "[libinsane-gobject:project options]"); putting
        # them in project_options is a hard meson error, and booleans are used
        # instead of feature options because the project declares
        # meson_version >=0.37.1 and feature_option.allowed() would add a
        # "uses feature introduced in 0.59.0" warning.
        tc.subproject_options["libinsane-gobject"] = [{"introspection": False},
                                                      {"gtk_doc": False}]
        tc.generate()

    @staticmethod
    def _find_ohos_archiver():
        """meson 的 archiver 探测只认可发现的绝对路径，裸名会直接把 configure 打死。

        现象（CI 实测，两次首错逐字相同）：
            ../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]
            Running `llvm-ar --version` gave "[Errno 2] No such file or directory: 'llvm-ar'"
            → ERROR: libinsane/1.0.10: Error in build() method, line 169
          证据：build #63803（worker OpenHarmonyPCDeveloper-CI-009）与
                build #63820（worker OpenHarmonyPCDeveloper-CI-011）；同一步骤、同一首错。
        根因：框架 `ci/conan/build_and_test.sh:566/:1320` 把 `AR` 导出成 llvm-* **裸名**，
              而 `ci/conan/profiles/ohos-aarch64:29` 只声明 `c/cpp` executable、未声明 `ar`
              ⇒ meson 只能去 worker PATH 找裸名。本机 B 机有 `/data/service/hnp/bin/llvm-ar`
              所以本地一直绿；CI worker 上没有 ⇒ 挂。不是配方逻辑缺陷、也不是网络/源码下载
              （同日志 `curl` 缺失只是 `[WARN] ... will rely on conan's download` 非阻塞）。
        修法：弹掉裸名、改锁可发现的绝对路径 —— **同 babl-tools/0.1.126 与
              at-spi2-core/2.60.5 的 generate() 写法（两者均 merged 且 ci=passed）**。
        """
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)
        for name in ("ar", "as", "strip", "nm", "ranlib"):
            # CI worker 若带 llvm-* 就用 llvm-*（与本机 HNP 工具链一致），否则退回 binutils 同名工具。
            found = shutil.which("llvm-%s" % name) or shutil.which(name)
            if found:
                os.environ[name.upper()] = found

    def build(self):
        apply_conandata_patches(self)
        self._find_ohos_archiver()
        meson = Meson(self)
        meson.configure()
        # Default targets include every upstream CUnit test executable, so the
        # suite is proven to compile here; it is executed against the build dir
        # afterwards (the package itself is libraries only). See notes.md.
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # libtool archives leak absolute build-machine paths and are useless here.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # OHOS 内核只加载签名有效的共享库：meson 装出来的 .so 携带的 .codesign 是
        # 链接期占位/失效签名，消费者 test() 直接报
        # `Error loading shared library libinsane.so.1: (needed by …)` 且 errno 为空、rc=127
        # （一手四臂复现：原样 127 / 只加 LD_LIBRARY_PATH 仍 127 / 平铺实体文件仍 127 /
        #  remove-section + selfSign 后 rc=0）。同仓 glib/2.84.0.2 的 _sign_shared_libs()
        # 与 1149 个配方同款处置，见 knowledge/graph/E452.kv、E517.kv、E077.kv。
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """E077 四步重签（此处只需后三步）：去掉旧 .codesign -> selfSign -> 保持可执行位。

        Native OHOS worker 才有 binary-sign-tool；交叉 SDK 环境（oh_compile）下工具缺失时
        跳过并告警，不把配方判死——同 glib/2.84.0.2 的处置。
        """
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates = ["/data/service/hnp/bin/llvm-objcopy", shutil.which("llvm-objcopy") or ""]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((x for x in candidates if x and os.path.isfile(x)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
            os.chmod(so, os.stat(so).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libinsane")
        self.cpp_info.set_property("cmake_target_name", "libinsane::libinsane")
        self.cpp_info.set_property("pkg_config_name", "libinsane")
        # libinsane core + GObject wrapper; meson versions the soname with the
        # project version (1.0.10).
        self.cpp_info.libs = ["insane", "insane_gobject"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
