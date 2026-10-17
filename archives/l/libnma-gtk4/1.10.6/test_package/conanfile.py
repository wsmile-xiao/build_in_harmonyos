import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibnmaGtk4TestConan(ConanFile):
    """Consumer test — pkg-config/meson 拼法（gtk4 test_package 同款）。

    CMakeDeps 拼法会把 libnma-gtk4 的传递依赖 targets 全展开，实测
    graphene→glib2/2.88.0 的静态库（libglib-2.0.a/libgobject-2.0.a）
    与 glib/2.84.0.1.1 的动态库同时排进链接行——静态 glib 2.88 符号
    进二进制 + 运行时加载动态 glib 2.84 → GType 双状态 abort
    （g_type_register_static assertion failed，实测复现）。pkg-config
    拼法（dependency('libnma-gtk4')）只展开上游 libnma-gtk4.pc 的
    Libs/Requires 链（requires: libnm → gio-2.0 动态链），无静态
    glib2 介入。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # glib 组件名代际桥接（主配方 _bridge_glib_component_names 同款）：
        # libnm/1.58.0 以 glib/2.88.3+ 新组件名（glib::gobject 等）声明
        # requires，本图 override 钉住 glib/2.84.0.1.1（旧名 gobject-2.0）
        # ——PkgConfigDeps 延迟解析组件引用时 not found，生成前先改写。
        mapping = {"glib": "glib-2.0", "gobject": "gobject-2.0",
                   "gio": "gio-2.0", "gmodule": "gmodule-2.0"}
        for dep in self.dependencies.host.values():
            if dep.ref.name != "libnm":
                continue
            patched = []
            for req in (dep.cpp_info.requires or []):
                if req.startswith("glib::"):
                    comp = req.split("::", 1)[1]
                    req = "glib::" + mapping.get(comp, comp)
                patched.append(req)
            dep.cpp_info.requires = patched
        PkgConfigDeps(self).generate()
        # MesonToolchain 不写 ar/ranlib（tools.build:compiler_executables
        # 只声明 c/cpp）——gtk4 test_package 同款修复：从 PATH 解析真实
        # 工具绝对路径写入 machine file。
        tc = MesonToolchain(self)
        for name in ("ar", "as", "strip", "nm", "ranlib"):
            path = shutil.which(name)
            if path:
                if name == "ar":
                    tc.ar = path
                elif name == "as":
                    tc.as_ = path
                elif name == "strip":
                    tc.strip = path
                else:
                    tc.binaries[name] = path
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    # ── OHOS runtime helpers ──────────────────────────────────────────
    #
    # The OHOS (musl-based) dynamic loader refuses to resolve a DT_NEEDED
    # entry whose file is a symbolic link ("Error loading shared library
    # libfoo.so.N: (needed by ...)", exit 127, empty strerror). Several
    # runtime dependencies are packaged with symlinked sonames, so the run
    # needs the link targets materialised into a private directory that is
    # searched FIRST (libnm/gtk4 test_package precedent).

    def _dependency_libdirs(self):
        libdirs = []
        for dependency in self.dependencies.values():
            # 排除 glib2/2.88.0（graphene 传递，静态包同 soname 布局）
            try:
                ref_name = str(dependency.ref.name)
            except Exception:
                ref_name = ""
            if ref_name == "glib2":
                continue
            try:
                declared = list(dependency.cpp_info.libdirs or [])
            except Exception:
                continue
            for libdir in declared:
                if not libdir:
                    continue
                if not os.path.isabs(libdir):
                    libdir = os.path.join(str(dependency.package_folder), libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _materialize_runtime_libs(self):
        runtime_dir = os.path.join(self.build_folder, "ohos-runtime-lib")
        os.makedirs(runtime_dir, exist_ok=True)
        materialized = []
        for libdir in self._dependency_libdirs():
            try:
                names = os.listdir(libdir)
            except OSError:
                continue
            for name in names:
                if ".so" not in name:
                    continue
                path = os.path.join(libdir, name)
                if not os.path.islink(path):
                    continue
                real = os.path.realpath(path)
                if os.path.isfile(real):
                    destination = os.path.join(runtime_dir, name)
                    if not os.path.exists(destination):
                        shutil.copy2(real, destination)
                        materialized.append(name)
        if materialized:
            self.output.info(
                "OHOS consumer runtime: materialised %d symlinked .so file(s): %s"
                % (len(materialized), ", ".join(sorted(materialized)))
            )
        return runtime_dir

    def test(self):
        executable = os.path.join(self.build_folder, "test_libnma_gtk4")
        if str(self.settings.os) == "OHOS":
            runtime_dir = self._materialize_runtime_libs()
            paths = [runtime_dir] + self._dependency_libdirs()
            current = os.environ.get("LD_LIBRARY_PATH", "")
            if current:
                paths.extend(p for p in current.split(":") if p and p not in paths)
            os.environ["LD_LIBRARY_PATH"] = ":".join(paths)
            os.environ.pop("LD_PRELOAD", None)
        if not can_run(self):
            return
        self.run(f'"{executable}"', cwd=self.build_folder,
                 env=None if str(self.settings.os) == "OHOS" else "conanrun")
