import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)


class Libical3Conan(ConanFile):
    name = "libical3"
    version = "3.0.20"
    description = "libical 3.0 line: iCalendar (RFC 5545) protocol library with GLib bindings"
    license = "LGPL-2.1-only OR MPL-2.0"
    homepage = "https://github.com/libical/libical"
    url = "https://github.com/libical/libical"
    topics = ("icalendar", "vcal", "calendar", "rfc5545")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")
        self.requires("libxml2/2.15.3.1")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        self._generate_pkg_config_fix()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            with open(rules, "w") as f:
                f.write("\n".join((
                    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,./")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                    'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                    'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                )) + "\n")
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        tc.variables["WITH_CXX_BINDINGS"] = "OFF"
        tc.variables["GOBJECT_INTROSPECTION"] = "OFF"
        tc.variables["ICAL_GLIB"] = "ON"
        tc.variables["ICAL_GLIB_VAPI"] = "OFF"
        tc.variables["ICAL_BUILD_DOCS"] = "OFF"
        tc.variables["LIBICAL_BUILD_EXAMPLES"] = "OFF"
        tc.variables["LIBICAL_BUILD_TESTING"] = "ON"
        tc.variables["LIBICAL_BUILD_TESTING_BIGFUZZ"] = "OFF"
        tc.variables["USE_BUILTIN_TZDATA"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_BerkeleyDB"] = "ON"
        perl = next(
            (d for d in self.dependencies.build.values()
             if d.ref and d.ref.name == "perl"),
            None,
        )
        if perl and perl.package_folder:
            tc.variables["PERL_EXECUTABLE"] = os.path.join(
                perl.package_folder, "bin", "perl")
        # presets env：基于 VirtualBuildEnv 环境叠加 PKG_CONFIG_PATH
        #（上游 FindGLib/FindLibXML 走 pkg_check_modules，需要修正后的
        # .pc 路径；presets_build_environment 是注入 cmake presets
        # environment 的通道，配方自身 buildenv_info 不进 presets）
        env = vbe.environment()
        env.prepend_path("PKG_CONFIG_PATH", self._pkg_config_paths())
        tc.presets_build_environment = env
        tc.generate()

    def _dep_package_folder(self, name):
        for dep in self.dependencies.values():
            if dep.ref and dep.ref.name == name and dep.package_folder:
                return dep.package_folder
        return None

    def _generate_pkg_config_fix(self):
        """上游 FindGLib/FindLibXML 走 pkg_check_modules。

        conan glib/libxml2 包里安装的 .pc 文件 prefix=/ （broken），且
        glib-2.0.pc 的 Requires 引用 proxy-libintl——该包没有安装 .pc，
        pkg-config 解析直接失败。这里复制直接依赖的 .pc 到 pc-fix 目录，
        修正 prefix 并剥掉 proxy-libintl 引用；传递依赖
        （pcre2/zlib/libffi）的 pkgconfig 目录直接加入 PKG_CONFIG_PATH。
        """
        fix_dir = os.path.join(self.generators_folder, "pc-fix")
        os.makedirs(fix_dir, exist_ok=True)

        def _strip_proxy_libintl(text):
            # Requires 行按逗号拆分，剔除 proxy-libintl 词条后重组
            #（该包未安装 .pc，pkg-config 解析失败；链接期由 conan
            # 依赖图自动带上 libintl.a）。
            # Requires.private 整行置空：其传递依赖（libpcre2-8/libffi/
            # zlib/gmodule-no-export）仅静态链接场景需要，FindGLib 的
            # pkg_check_modules 只取非 static 的 CFLAGS/LDFLAGS；
            # pkg-config 对 private 行做存在性校验，缺失即整体失败。
            out_lines = []
            for line in text.splitlines():
                m = re.match(r"^(Requires(\.private)?):\s*(.*)$", line)
                if m and m.group(2):  # Requires.private 整行置空
                    line = "{}:".format(m.group(1))
                elif m and "proxy-libintl" in m.group(3):
                    items = [i.strip() for i in m.group(3).split(",")]
                    kept = [i for i in items if i and not
                            i.startswith("proxy-libintl")]
                    line = "{}: {}".format(
                        m.group(1), ", ".join(kept))
                out_lines.append(line)
            return "\n".join(out_lines) + "\n"

        def fix_pc(pkg_name, pc_names):
            folder = self._dep_package_folder(pkg_name)
            if not folder:
                return
            pcdir = os.path.join(folder, "lib", "pkgconfig")
            if not os.path.isdir(pcdir):
                return
            for pc_name in pc_names:
                src = os.path.join(pcdir, pc_name)
                if not os.path.isfile(src):
                    continue
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={folder}",
                              text, count=1, flags=re.M)
                text = _strip_proxy_libintl(text)
                with open(os.path.join(fix_dir, pc_name), "w",
                          encoding="utf-8") as fh:
                    fh.write(text)

        fix_pc("glib", (
            "glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
            "gmodule-2.0.pc", "gthread-2.0.pc",
            "gmodule-no-export-2.0.pc", "gmodule-export-2.0.pc",
        ))
        fix_pc("libxml2", ("libxml-2.0.pc",))

    def _pkg_config_paths(self):
        fix_dir = os.path.join(self.generators_folder, "pc-fix")
        pc_paths = [fix_dir]
        for pkg in ("pcre2", "zlib", "libffi", "proxy-libintl"):
            folder = self._dep_package_folder(pkg)
            if folder:
                pcdir = os.path.join(folder, "lib", "pkgconfig")
                if os.path.isdir(pcdir):
                    pc_paths.append(pcdir)
                    continue
            self.output.info(f"libical3: no pc dir for {pkg} "
                             f"(folder={folder})")
        return os.pathsep.join(pc_paths)

    def build(self):
        apply_conandata_patches(self)
        # OHOS-on-OHOS：构建机与目标机同为 OHOS aarch64。上游的
        # CMAKE_CROSSCOMPILING 分支要求导入 native 构建 exported 的
        # ical-glib-src-generator target；这里构建期工具可直接就地
        # 构建运行（glib/libxml2 共享库通过 BUILD RPATH 解析），
        # 砍掉交叉导入分支走普通路径。
        src = os.path.join(self.source_folder, "src", "libical-glib",
                           "CMakeLists.txt")
        replace_in_file(self, src,
            """if(CMAKE_CROSSCOMPILING)
  # import native ical-glib-src-generator when cross-compiling
  set(IMPORT_ICAL_GLIB_SRC_GENERATOR "ICAL_GLIB_SRC_GENERATOR-NOTFOUND"
    CACHE FILEPATH
    "Path to exported ical-glib-src-generator target from native build"
  )
  include(${IMPORT_ICAL_GLIB_SRC_GENERATOR})
  set(ical-glib-src-generator_EXE native-ical-glib-src-generator)
else()
  set(ical-glib-src-generator_EXE ical-glib-src-generator)
endif()
""",
            "set(ical-glib-src-generator_EXE ical-glib-src-generator)\n")
        # OHOS 相对 soname：去掉 VERSION/SOVERSION 属性
        #（HMDFS 上绝对 soname/$ORIGIN rpath 不稳定，与其他 OHOS 库一致）
        for target, rel in (
            ("ical", os.path.join("src", "libical", "CMakeLists.txt")),
            ("icalss", os.path.join("src", "libicalss", "CMakeLists.txt")),
            ("icalvcal", os.path.join("src", "libicalvcal", "CMakeLists.txt")),
            ("ical-glib", os.path.join("src", "libical-glib", "CMakeLists.txt")),
        ):
            path = os.path.join(self.source_folder, rel)
            replace_in_file(self, path,
                """if(NOT ANDROID)
  set_target_properties({target} PROPERTIES
    VERSION ${{LIBICAL_LIB_VERSION_STRING}}
    SOVERSION ${{LIBICAL_LIB_MAJOR_VERSION}}
  )
endif()
""".format(target=target),
                "")
        cmake = CMake(self)
        # PKG_CONFIG_PATH 需在 cmake 进程内生效（FindGLib/FindLibXML 走
        # pkg_check_modules；pc-fix 目录含 prefix 修正+剥 proxy-libintl
        # 后的 glib/libxml .pc 副本）。
        # LIBRARY_PATH：上游 FindLibXML 把 pkg-config 的 --libs-only-l
        # 结果（仅 -lxml2，无 -L）传给 target_link_libraries，链接期
        # 靠该环境变量解析依赖库目录（clang/lld 认可，等效 -L）。
        # LD_LIBRARY_PATH：构建期就地运行的 ical-glib-src-generator
        # 需要加载 glib/libxml2 共享库。
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self._pkg_config_paths())
        for pkg in ("glib", "libxml2"):
            folder = self._dep_package_folder(pkg)
            if folder:
                env.prepend_path("LIBRARY_PATH",
                                 os.path.join(folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(folder, "lib"))
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游 CTest 全量（N=48 注册）。

        测试二进制 NEEDED 相对 soname（./libical.so 等，OHOS 规则），
        运行目录为 build/bin，需把构建产物的 lib*.so* 复制到
        CTestTestfile.cmake 所在各目录（含 bin 及其上溯路径），
        同 4.0.1 线的处理。环境变量带上 glib/libxml2 共享库路径。
        """
        import glob
        import shutil
        lib_sources = glob.glob(os.path.join(self.build_folder, "lib",
                                             "lib*.so*"))
        base_dirs = {self.build_folder}
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                base_dirs.add(root)
        for base in sorted(base_dirs):
            for rel in (".", "lib", os.path.join("..", "lib"),
                        os.path.join("..", "..", "lib"),
                        os.path.join("..", "..", "..", "lib")):
                target_dir = os.path.abspath(os.path.normpath(
                    os.path.join(base, rel)))
                if not target_dir.startswith(self.build_folder):
                    continue
                os.makedirs(target_dir, exist_ok=True)
                for src in lib_sources:
                    dst = os.path.join(target_dir,
                                       os.path.basename(src))
                    if os.path.abspath(src) == os.path.abspath(dst):
                        continue
                    shutil.copy2(src, dst)
        # zoneinfo：USE_BUILTIN_TZDATA=ON 时 builtin_timezones 测试
        # 从 build/../zoneinfo 读取
        src_zone = os.path.join(self.source_folder, "zoneinfo")
        if os.path.isdir(src_zone):
            for dst_zone in (
                os.path.join(self.build_folder, "zoneinfo"),
                os.path.normpath(os.path.join(self.build_folder, "..",
                                              "zoneinfo")),
            ):
                shutil.copytree(src_zone, dst_zone, dirs_exist_ok=True)
        env = Environment()
        for pkg in ("glib", "libxml2"):
            folder = self._dep_package_folder(pkg)
            if folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(folder, "lib"))
        ctest = os.environ.get("CTEST_EXECUTABLE") or shutil.which("ctest") or "ctest"
        with env.vars(self).apply():
            self.run(f'"{ctest}" --test-dir "{self.build_folder}" '
                     f'--output-on-failure --no-tests=error')

    def package(self):
        CMake(self).install()
        if self.settings.os == "OHOS":
            self._sign_ohos_elf_tree(self.package_folder)

    def _sign_ohos_elf_tree(self, root_folder):
        """OHOS 上未签名 ELF 无法被 dlopen/执行——安装后统一签名。"""
        import shutil
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            import sys
            print("WARNING: llvm-objcopy/binary-sign-tool not found; "
                  "skipping ELF signing", file=sys.stderr)
            return
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path) \
                        or not self._is_elf(path):
                    continue
                self.run(
                    f'"{objcopy}" --remove-section .codesign '
                    f'"{path}" 2>/dev/null || true')
                self.run(
                    f'"{signer}" sign -inFile "{path}" '
                    f'-outFile "{path}" -selfSign 1')

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"

    def package_info(self):
        self.cpp_info.libs = ["ical-glib", "icalvcal", "icalss", "ical"]
        self.cpp_info.requires = ["glib::glib", "glib::gobject",
                                  "libxml2::libxml2"]
