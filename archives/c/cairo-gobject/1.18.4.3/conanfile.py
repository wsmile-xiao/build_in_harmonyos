import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CairoGObjectConan(ConanFile):
    name = "cairo-gobject"
    version = "1.18.4.3"
    description = "Cairo GObject bindings"
    license = "LGPL-2.1-or-later OR MPL-1.1"
    homepage = "https://www.cairographics.org/"
    url = "https://gitlab.freedesktop.org/cairo/cairo"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pixman/0.46.4", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58", transitive_headers=True, transitive_libs=True)
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # 本地重建（gtk 3.24.52 X11 后端）：启用 xlib surface，使本包打包的
        # libcairo.so 带 cairo_xlib_surface_* 符号——否则 test_package 链接时
        # 与本地方案重建的 cairo 包同名 SONAME 去重后命中无 xlib 的 libcairo
        # libx11 用 override 压掉 libxrender/0.9.12 配方的 libx11/1.8.13 传递 pin
        # （libxext/6.4.0 同族精确 pin 6.4.0，二者无法共存，统一 6.4.0 覆盖）
        self.requires("libx11/6.4.0", override=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/0.9.12", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build_requirements(self):
        # 制品仓配方依赖 CI 全局 meson；本地重建需显式 tool_requires
        self.tool_requires("meson/1.11.0")

    def source(self):
        staged = os.path.expanduser("~/Download/cairo-1.18.4.tar.xz")
        if os.path.isfile(staged):
            from conan.tools.files import check_sha256, unzip

            check_sha256(self, staged, self.conan_data["sources"]["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["png"] = "enabled"
        toolchain.project_options["freetype"] = "enabled"
        toolchain.project_options["fontconfig"] = "enabled"
        toolchain.project_options["zlib"] = "enabled"
        toolchain.project_options["glib"] = "enabled"
        # 本地重建：启用 xlib surface（见 requirements 注释）
        toolchain.project_options["xlib"] = "enabled"
        toolchain.project_options["xcb"] = "disabled"
        toolchain.project_options["xlib-xcb"] = "disabled"
        toolchain.project_options["quartz"] = "disabled"
        toolchain.project_options["dwrite"] = "disabled"
        toolchain.project_options["lzo"] = "disabled"
        toolchain.project_options["spectre"] = "disabled"
        toolchain.project_options["symbol-lookup"] = "disabled"
        toolchain.project_options["tests"] = "disabled"
        # OHOS/static-glib: libglib-2.0.a 引用 g_libintl_* 符号，需链接 glib 包自带的
        # proxy-libintl（静态 glib 下 cairo-gobject 自身链接不通过 -> 补 -lintl）。
        # 复用 E318/1.18.4.1 的绝对路径方案：避免拾取系统 gettext 的 libintl。
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                for _name in ("libintl.a", "libintl.so"):
                    _path = os.path.join(dep.package_folder, "lib", _name)
                    if os.path.isfile(_path):
                        toolchain.c_link_args.extend([_path.replace("\\", "/")])
                        break
                break
        toolchain.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        self._patch_meson_helpers()
        self._prepare_build_environment()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        libdir = os.path.join(self.package_folder, "lib")
        self._ensure_library_aliases(libdir, "libcairo", "2")
        self._ensure_library_aliases(libdir, "libcairo-gobject", "2")
        self._remove_libtool_archives()
        if self.settings.os == "OHOS":
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["cairo-gobject", "cairo"]
        self.cpp_info.includedirs = ["include/cairo", "include"]
        self.cpp_info.requires = [
            "glib::gobject-2.0",
            "glib::glib-2.0",
            "pixman::pixman",
            "libpng::libpng",
            "freetype::freetype",
            "fontconfig::fontconfig",
            "zlib::zlib",
            # libx11 为 override 版本钉版（压 libxrender 的 1.8.13 传递 pin），
            # 不被视为直接依赖，不能出现在 cpp_info.requires（conan 2.29 检查报错）
            "libxext::libxext",
            "libxrender::libxrender",
        ]
        self.cpp_info.set_property("cmake_file_name", "cairo-gobject")
        self.cpp_info.set_property("cmake_target_name", "cairo-gobject::cairo-gobject")
        self.cpp_info.set_property("pkg_config_name", "cairo-gobject")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _inject_meson_binaries(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not ar:
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        entries = []
        if ar and "\nar =" not in content:
            entries.append(f"ar = '{ar}'")
        if ranlib and "\nranlib =" not in content:
            entries.append(f"ranlib = '{ranlib}'")
        if pkg_config and "\npkg-config =" not in content:
            entries.append(f"pkg-config = '{pkg_config}'")
        if not entries:
            return
        insert = "[binaries]\n" + "\n".join(entries) + "\n"
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insert, 1))

    def _ensure_library_aliases(self, libdir, stem, soversion):
        if not os.path.isdir(libdir):
            return
        candidates = [
            path for path in glob.glob(os.path.join(libdir, f"{stem}.so.{soversion}.*"))
            if os.path.isfile(path) and not os.path.islink(path)
        ]
        if not candidates:
            return
        source = sorted(candidates, key=len, reverse=True)[0]
        for alias in (f"{stem}.so.{soversion}", f"{stem}.so"):
            destination = os.path.join(libdir, alias)
            if os.path.exists(destination):
                continue
            try:
                os.symlink(os.path.basename(source), destination)
            except (OSError, NotImplementedError):
                shutil.copy2(source, destination)

    def _remove_libtool_archives(self):
        for archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(archive)

    def _patch_meson_helpers(self):
        meson_build = os.path.join(self.source_folder, "meson.build")
        replace_in_file(
            self,
            meson_build,
            "version: run_command(find_program('version.py'), check: true).stdout().strip(),",
            "version: run_command(find_program('python3'), 'version.py', check: true).stdout().strip(),",
        )

    def _prepare_build_environment(self):
        if self.settings.os != "OHOS":
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # CI #26198：meson sanity check（configure 阶段编译并运行探测程序）在
        # 运行时找不到依赖库 → "Executables created by c compiler ... are not
        # runnable"。把全部 host 依赖的 lib 目录 prepend 进 LD_LIBRARY_PATH，
        # 使 sanity 探测程序能加载 glib/cairo 依赖（gtk+ 子任务同款修复）。
        dep_lib_dirs = []
        for _ref, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                absolute = os.path.join(dep.package_folder, libdir) if not os.path.isabs(libdir) else libdir
                if os.path.isdir(absolute) and absolute not in dep_lib_dirs:
                    dep_lib_dirs.append(absolute)
        if dep_lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(dep_lib_dirs + ([existing] if existing else []))

    def _sign_shared_libs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{target}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{target}" -outFile "{target}" -selfSign 1')
