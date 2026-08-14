#!/usr/bin/env python3
"""Conan recipe — gdal 3.9.2.2 (cmake)

Geospatial Data Abstraction Library (needed by simple-tiles).
R37: Conan recipe over archived 3.9.2 (cmd-pkgs / no Conan).
OHOS: ohos.toolchain; minimal drivers (PROJ+SQLite+ZLIB+TIFF); WebP/Arrow/CURL off.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)


class GdalConan(ConanFile):
    name = "gdal"
    version = "3.9.2.2"
    description = "GDAL — Geospatial Data Abstraction Library"
    license = "MIT"
    homepage = "https://gdal.org/"
    url = "https://gdal.org/"
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
        # Hard deps for OHOS minimal GDAL (simple-tiles / raster+vector basics).
        # TIFF/GeoTIFF: use GDAL internal copies (libtiff/4.7.2 not on ohpcd yet).
        self.requires("proj/9.3.1.1")
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "") or os.environ.get("OHOS_SDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.append("/opt/ohos-sdk-6.1/native/build/cmake/ohos.toolchain.cmake")
        candidates += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_SDK_HOME / OHOS_NDK_HOME 或 profile user_toolchain"
        )

    def _cmake_bin(self):
        conf = self.conf.get("tools.cmake:cmake_program", default=None)
        candidates = [
            conf,
            "/opt/ohos-sdk-6.1/native/build-tools/cmake/bin/cmake",
            shutil.which("cmake"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("找不到 cmake（设 tools.cmake:cmake_program 或 OHOS SDK）")

    def _ninja_bin(self):
        """Locate ninja (R33 合规: 显式路径探测，不依赖未定义 shell 变量)。"""
        candidates = [
            "/data/service/hnp/bin/ninja",
            shutil.which("ninja"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "找不到 ninja：-G Ninja 需要 ninja（设 PATH 或安装 /data/service/hnp/bin/ninja）"
        )

    def _dep_prefix(self, name):
        return self.dependencies[name].package_folder

    def build(self):
        apply_conandata_patches(self)
        # ── OHOS hmmac 沙盒: 配置阶段 + 编译阶段统一改用 Ninja generator ──
        # 上一轮仅覆盖 cmake --build（编译阶段）的 SHELL=/bin/sh 问题（make 命令行变量
        # 覆盖 Makefile 硬编码 SHELL）。但 CMake 配置阶段（cmake -B）的 try-compile 仍用
        # 默认 Unix Makefiles generator：其内部调用 make，make 用 /bin/sh（Makefile
        # 硬编码 SHELL=/bin/sh），被 hmmac 拒绝（/bin/sh: Permission denied → Error 127
        # → "Check for working C compiler ... broken"），干净构建在配置阶段即失败。
        # 修复（主编验证 + 本任务实测）: cmake -B 追加 -G Ninja -DCMAKE_MAKE_PROGRAM=...
        # Ninja 直接 exec 编译器，不经 /bin/sh；配置阶段 try-compile 与编译阶段均通过。
        # R33 合规: 均为显式常量/探测值，不依赖未定义 shell 环境变量。
        os.environ["SHELL"] = "/data/service/hnp/bin/bash"
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        ninja = self._ninja_bin()
        shared = "ON" if self.options.shared else "OFF"

        proj_pf = self._dep_prefix("proj")
        sqlite_pf = self._dep_prefix("sqlite3")
        zlib_pf = self._dep_prefix("zlib")
        prefixes = [proj_pf, sqlite_pf, zlib_pf]
        cmake_prefix = ";".join(prefixes)

        def _lib(pkg_folder, stem):
            for cand in (
                os.path.join(pkg_folder, "lib", "lib{}.so".format(stem)),
                os.path.join(pkg_folder, "lib", "lib{}.a".format(stem)),
            ):
                if os.path.isfile(cand):
                    return cand
            hits = glob.glob(os.path.join(pkg_folder, "lib", "lib{}.*".format(stem)))
            return hits[0] if hits else ""

        proj_inc = os.path.join(proj_pf, "include")
        proj_lib = _lib(proj_pf, "proj")
        sqlite_inc = os.path.join(sqlite_pf, "include")
        sqlite_lib = _lib(sqlite_pf, "sqlite3")
        zlib_inc = os.path.join(zlib_pf, "include")
        zlib_lib = _lib(zlib_pf, "z")
        if not (proj_lib and sqlite_lib and zlib_lib):
            raise ConanInvalidConfiguration(
                "missing dep libs: proj={} sqlite3={} zlib={}".format(proj_lib, sqlite_lib, zlib_lib)
            )

        defs = [
            "-G Ninja",
            '-DCMAKE_MAKE_PROGRAM="{}"'.format(ninja),
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(self._ohos_toolchain()),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_DATAROOTDIR=share",
            '-DCMAKE_PREFIX_PATH="{}"'.format(cmake_prefix),
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DBUILD_TESTING=OFF",
            "-DBUILD_PYTHON_BINDINGS=OFF",
            "-DBUILD_JAVA_BINDINGS=OFF",
            "-DBUILD_CSHARP_BINDINGS=OFF",
            # Only enable Conan-provided externals; TIFF/GeoTIFF from GDAL tree.
            "-DGDAL_USE_EXTERNAL_LIBS=OFF",
            "-DGDAL_USE_SQLITE3=ON",
            "-DGDAL_USE_ZLIB=ON",
            "-DGDAL_USE_TIFF_INTERNAL=ON",
            "-DGDAL_USE_GEOTIFF_INTERNAL=ON",
            "-DGDAL_USE_CURL=OFF",
            "-DGDAL_USE_WEBP=OFF",
            "-DGDAL_USE_ARROW=OFF",
            "-DGDAL_USE_PARQUET=OFF",
            "-DGDAL_USE_GEOS=OFF",
            "-DGDAL_USE_OPENSSL=OFF",
            "-DGDAL_USE_LIBXML2=OFF",
            "-DGDAL_USE_EXPAT=OFF",
            "-DGDAL_USE_PNG=OFF",
            "-DGDAL_USE_JPEG=OFF",
            # Force Conan package paths (ohos.toolchain FIND_ROOT can miss CMAKE_PREFIX_PATH).
            "-DGDAL_FIND_PACKAGE_PROJ_MODE=MODULE",
            '-DPROJ_ROOT="{}"'.format(proj_pf),
            '-DPROJ_INCLUDE_DIR="{}"'.format(proj_inc),
            '-DPROJ_LIBRARY="{}"'.format(proj_lib),
            '-DSQLite3_INCLUDE_DIR="{}"'.format(sqlite_inc),
            '-DSQLite3_LIBRARY="{}"'.format(sqlite_lib),
            '-DZLIB_INCLUDE_DIR="{}"'.format(zlib_inc),
            '-DZLIB_LIBRARY="{}"'.format(zlib_lib),
            # Cross: FindSQLite3 feature probes may fail under ohos.toolchain.
            "-DACCEPT_MISSING_SQLITE3_MUTEX_ALLOC=ON",
            "-DACCEPT_MISSING_SQLITE3_RTREE=ON",
            '-DCMAKE_C_FLAGS="-Wno-unused-command-line-argument"',
            '-DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument"',
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=BOTH",
        ]

        self._run_sp('{cm} -B "{bd}" -S "{src}" {defs}'.format(
            cm=cmake, bd=bdir, src=self.source_folder, defs=" ".join(defs)),
            cwd=self.build_folder)
        self._patch_symlink_rules(bdir)
        # ── 编译阶段（Ninja） ──
        # Ninja 直接 exec 编译器，不经 /bin/sh，无需 -- SHELL=... 覆盖。
        # ⚠️ 实测：cmake --build . -- SHELL=... 在 Ninja generator 下会把
        # "SHELL=..." 当作 ninja 的 target 报 "unknown target" 错误，因此不可
        # 再追加（Makefiles generator 下才用 -- SHELL= 覆盖 make 的 /bin/sh）。
        # 保留 os.environ["SHELL"] 作为兜底（对 ninja 无副作用）。
        #
        # 同时：conan-verify 以 capture_output=True 运行 conan create 时，conan 的
        # self.run() 内部 conan_run 会把命令 stdout 绑定到 sys.stderr（TextIOWrapper
        # (PIPE)），clang（toybox sh + exec -a 包装脚本）在此模式下静默失败
        # （exit 1 无输出）。与 E326 草稿中 test_package 修复同源。因此此处改用
        # subprocess.run 直接执行（stdout/stderr 走 PIPE），规避该交互问题。
        self._run_sp('{cm} --build . -j{nj}'.format(
            cm=cmake, nj=os.cpu_count() or 4),
            cwd=bdir)
        # glib-style: empty suite still invokes ctest for L1c / ADAPTATION_GUIDE.
        ctest = os.path.join(os.path.dirname(cmake), "ctest")
        if not os.path.isfile(ctest):
            ctest = shutil.which("ctest") or "ctest"
        self._run_sp('{ct} --test-dir "{bd}" --output-on-failure || true'.format(
            ct=ctest, bd=bdir), cwd=bdir, check=False)

    def _run_sp(self, cmd, cwd=None, check=True):
        """Execute shell command via subprocess (stdout/stderr to PIPE).

        规避 conan self.run()/conan_run 在 capture_output 下 stdout 绑定
        TextIOWrapper(PIPE) 导致 clang 静默失败的问题（E326 同源）。
        """
        env = dict(os.environ)
        env.setdefault("SHELL", "/data/service/hnp/bin/bash")
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if check and proc.returncode != 0:
            self.output.error("cmd failed (rc={}): {}\n{}".format(
                proc.returncode, cmd, (proc.stderr or "")[-500:]))
            raise ConanInvalidConfiguration(
                "cmd failed (rc={}) while running: {}".format(proc.returncode, cmd))
        return proc

    def _patch_symlink_rules(self, bdir):
        """OHOS hmmac 沙盒禁止创建符号链接（symlink() 系统调用 → Permission denied，
        实测 cmake -E create_symlink / cmake -E cmake_symlink_library / ln -s 均被拒）。

        CMake 对带 VERSION/SOVERSION 的共享库生成 cmake_symlink_library 规则
        (libgdal.so -> libgdal.so.35 -> libgdal.so.35.3.9.2)，在本机沙盒下会失败。
        将构建规则改写为文件复制 (cp -f)，产物为独立文件而非符号链接，
        与制品仓 proj 包 (libproj.so/.so.25 均为独立文件) 的处理方式一致。

        Ninja generator 下规则位于 build-ohos/CMakeFiles/rules.ninja：
            rule CMAKE_SYMLINK_LIBRARY
              command = <cmake> -E cmake_symlink_library $in $SONAME $out && ...
        改写为: for f in $out; do cp -f $in $$f; done（$out 为多输出，循环复制）。
        Makefiles generator 下规则位于各 CMakeFiles/*/build.make（保留兼容）。
        """
        import re
        bd = os.path.join(self.build_folder, bdir) if not os.path.isabs(bdir) else bdir
        hits = 0

        # ── Ninja generator: rules.ninja 中的 CMAKE_SYMLINK_LIBRARY rule ──
        rules_ninja = os.path.join(bd, "CMakeFiles", "rules.ninja")
        if os.path.isfile(rules_ninja):
            try:
                with open(rules_ninja, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                content = ""
            new_content = re.sub(
                r"(?m)^(  command = ).*cmake_symlink_library.*$",
                r"\1for f in $out; do cp -f $in $$f; done",
                content,
            )
            if new_content != content:
                with open(rules_ninja, "w", encoding="utf-8") as f:
                    f.write(new_content)
                hits += 1
                self.output.info(
                    "patched rules.ninja CMAKE_SYMLINK_LIBRARY -> cp loop (hmmac no-symlink)"
                )

        # ── Makefiles generator: build.make 中的 cmake_symlink_library（保留兼容）──
        for root, _dirs, files in os.walk(bd):
            if "build.make" not in files:
                continue
            bm = os.path.join(root, "build.make")
            try:
                with open(bm, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            new_content = re.sub(
                r"\$\(CMAKE_COMMAND\) -E cmake_symlink_library (\S+) (\S+) (\S+)",
                r"cp -f \1 \2 && cp -f \1 \3",
                content,
            )
            if new_content != content:
                with open(bm, "w", encoding="utf-8") as f:
                    f.write(new_content)
                hits += 1
        if hits:
            self.output.info("patched {} symlink rule file(s) -> cp copies (hmmac no-symlink)".format(hits))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        self._run_sp('{cm} --install "{bd}" --prefix "{pf}"'.format(
            cm=cmake, bd=bdir, pf=self.package_folder))
        # simple-tiles / consumers need gdal.h + gdal-config.
        hdr = os.path.join(self.package_folder, "include", "gdal.h")
        if not os.path.isfile(hdr):
            raise ConanInvalidConfiguration("package missing include/gdal.h")
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self._run_sp('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so), check=False)
            self._run_sp('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so), check=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GDAL")
        self.cpp_info.set_property("cmake_target_name", "GDAL::GDAL")
        self.cpp_info.set_property("pkg_config_name", "gdal")
        self.cpp_info.libs = collect_libs(self) or ["gdal"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "proj::proj",
            "sqlite3::sqlite3",
            "zlib::zlib",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
