#!/usr/bin/env python3
"""Conan recipe for cld2 0.0.0-git20150806 — manual shell-script build.

Compact Language Detector 2 (Google): Naïve Bayesian classifier detecting
80+ languages in UTF-8 text. Upstream ships no configure/CMake/Meson; the
official build is internal/compile_libs.sh (single g++ -shared -fPIC link).
This recipe mirrors that script with per-file compilation (lower peak RAM
for the ~27MB generated quadgram tables) using the Conan toolchain
compiler (R33), then builds and runs the upstream unittests
(internal/cld2_unittest.cc, internal/cld2_unittest_full.cc).
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout

# Shared core (mirrors compile_libs.sh/compile.sh/compile_full.sh): the 19 files
# common to both variants. The CJK delta_bi table is variant-specific and
# intentionally excluded here — chrome_2 uses delta_bi_4 while full uses
# delta_bi_32; both define CLD2::kCjkDeltaBi_obj so they must never link
# together (ld.lld duplicate-symbol otherwise).
_CLD2_BASE_COMMON_SRCS = [
    "cldutil.cc",
    "cldutil_shared.cc",
    "compact_lang_det.cc",
    "compact_lang_det_hint_code.cc",
    "compact_lang_det_impl.cc",
    "debug.cc",
    "fixunicodevalue.cc",
    "generated_entities.cc",
    "generated_language.cc",
    "generated_ulscript.cc",
    "getonescriptspan.cc",
    "lang_script.cc",
    "offsetmap.cc",
    "scoreonescriptspan.cc",
    "tote.cc",
    "utf8statetable.cc",
    "cld_generated_cjk_uni_prop_80.cc",
    "cld2_generated_cjk_compatible.cc",
    "generated_distinct_bi_0.cc",
]

# Variant-specific CJK delta_bi tables (mutually exclusive, same symbol).
_CLD2_DELTA_SMALL_SRC = "cld_generated_cjk_delta_bi_4.cc"
_CLD2_DELTA_FULL_SRC = "cld_generated_cjk_delta_bi_32.cc"

# Small-table (chrome_2) objects -> libcld2.so
_CLD2_SMALL_SRCS = [
    "cld2_generated_quadchrome_2.cc",
    "cld2_generated_deltaoctachrome.cc",
    "cld2_generated_distinctoctachrome.cc",
    "cld_generated_score_quad_octa_2.cc",
]

# Full-table objects (full 160-language set, mirrors compile_libs.sh second
# block + compile_full.sh): the 4 large quad/octa tables. The delta_bi_32
# table lives in _CLD2_DELTA_FULL_SRC above, not here.
_CLD2_FULL_TABLE_SRCS = [
    "cld2_generated_quad0122.cc",
    "cld2_generated_deltaocta0122.cc",
    "cld2_generated_distinctocta0122.cc",
    "cld_generated_score_quad_octa_0122.cc",
]


class Cld2Conan(ConanFile):
    name = "cld2"
    version = "0.0.0-git20150806"
    description = "Compact Language Detector 2: language detection in UTF-8 text."
    license = "Apache-2.0"
    homepage = "https://github.com/CLD2Owners/cld2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        # get_safe: profile校验先于配方执行，缺settings时直接比较会抛异常；
        # 用get_safe保持稳健（此前从未动过该位置，与source/generate/build/
        # conandata各轮补丁不重叠）。Windows才去fPIC，OHOS/Linux保留。
        if self.settings.get_safe("os") == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # E002/readonly_tmp: conan `get()` downloads + extracts the 72MB
        # upstream tarball. Python tempfile/conan helpers fall back to /tmp
        # when TMPDIR is unset — fatal on HarmonyOS (read-only /tmp). Prefer
        # the HMBS-injected writable dir; if the harness env propagation
        # broke (cf. preflight.sh mktemp failure), fall back to a writable
        # dir under base_source_folder instead of leaving TMPDIR unset.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.base_source_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HMBS readonly_tmp: /tmp is read-only on HarmonyOS. Forward the
        # HMBS-injected writable TMPDIR/TMP/TEMP into the build env so any
        # compiler temp files or test children never fall back to /tmp.
        # No /tmp hardcoding exists in this recipe (all objs under build_folder).
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)

    def _resolve_tool(self, *candidates):
        # True-machine stale profile path guard: profile pins
        # /data/service/hnp/bin/clang(++), but that file may not exist
        # on the current worker (FileNotFoundError in build()). Prefer
        # conf value only when the file exists; otherwise fall back to
        # PATH lookup (hmbs prepends real tool dirs to buildenv PATH).
        # R33 compliant: no bare $CC/$CXX shell vars, only conf + PATH.
        import shutil
        for _c in candidates:
            if not _c:
                continue
            if os.path.isabs(_c):
                if os.path.isfile(_c):
                    return _c
                _w = shutil.which(os.path.basename(_c))
                if _w:
                    return _w
            else:
                _w = shutil.which(_c)
                if _w:
                    return _w
                if os.path.isfile(_c):
                    return _c
        for _c in candidates:
            if _c:
                return _c
        return "clang++"

    def _toolchain(self):
        # R33: compiler/flags come from Conan conf, never from shell env.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        _conf_cxx = compilers.get("cpp")
        _conf_c = compilers.get("c")
        cxx = self._resolve_tool(
            _conf_cxx, "clang++",
            "aarch64-linux-ohos-clang++", "c++", "g++", _conf_c)
        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = "-std=c++%s" % cppstd if cppstd else "-std=c++17"
        cxxflags = [std_flag, "-O2", "-fPIC",
                    "-Wno-narrowing", "-Wno-c++11-narrowing"]
        if self.settings.get_safe("build_type") == "Debug":
            cxxflags.append("-g")
        else:
            cxxflags.append("-DNDEBUG")
        return cxx, cxxflags

    def _run_noshell(self, args, cwd=None):
        # readonly_tmp 新路线：shell-free 执行，彻底绕开 /bin/sh。
        # 前三轮 TMPDIR 转发复跑指纹逐字节一致，证明 sh 自身的
        # /tmp/sh*.tmp（dash 为 $()/`` 命令替换硬编码 /tmp，不读
        # TMPDIR）无法靠 export TMPDIR 修复。本方法用
        # subprocess list 形式（shell=False）直接 exec，不经过
        # sh -c，因此不产生任何 sh 临时文件；仅透传已确保可写的
        # TMPDIR/TMP/TEMP + 最小 PATH/LD_LIBRARY_PATH。
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        self.output.info("noshell: %s" % " ".join(args))
        subprocess.run(args, check=True, cwd=cwd or self.build_folder,
                       env=_env)

    def _compile_objects(self, src_dir, obj_dir, sources, cxx, cxxflags):
        # shell-free 逐文件编译：前轮仅转换了链接/测试环节，本轮补齐
        # 剩余的 self.run(shell) 路径；list 直调不经 sh -c，不产生
        # /tmp/sh*.tmp，语义与原单命令逐文件编译一致。
        for src in sources:
            obj = os.path.join(obj_dir, src.replace(".cc", ".o"))
            self._run_noshell(
                [cxx] + cxxflags + ["-c", os.path.join(src_dir, src),
                                   "-o", obj])

    def build(self):
        # E002/readonly_tmp: never use hardcoded /tmp; prefer HMBS TMPDIR,
        # fallback to a writable dir under build_folder.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        src_dir = os.path.join(self.source_folder, "internal")
        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)
        cxx, cxxflags = self._toolchain()

        # Library objects: common core + variant delta_bi + variant tables,
        # exactly mirroring compile_libs.sh / compile_full.sh. The two
        # delta_bi tables are mutually exclusive (same symbol) and must
        # never appear in one link.
        self._compile_objects(src_dir, obj_dir, _CLD2_BASE_COMMON_SRCS,
                              cxx, cxxflags)
        self._compile_objects(src_dir, obj_dir, [_CLD2_DELTA_SMALL_SRC],
                              cxx, cxxflags)
        small_dir = os.path.join(self.build_folder, "obj_small")
        full_dir = os.path.join(self.build_folder, "obj_full")
        os.makedirs(small_dir, exist_ok=True)
        os.makedirs(full_dir, exist_ok=True)
        self._compile_objects(src_dir, small_dir, _CLD2_SMALL_SRCS, cxx, cxxflags)
        self._compile_objects(src_dir, full_dir, [_CLD2_DELTA_FULL_SRC],
                              cxx, cxxflags)
        self._compile_objects(src_dir, full_dir, _CLD2_FULL_TABLE_SRCS,
                              cxx, cxxflags)

        if self.options.shared:
            lib_ext = ".so"
        else:
            lib_ext = ".a"
        lib_cld2 = os.path.join(self.build_folder, "libcld2" + lib_ext)
        lib_full = os.path.join(self.build_folder, "libcld2_full" + lib_ext)
        common_objs = [os.path.join(obj_dir, s.replace(".cc", ".o"))
                       for s in _CLD2_BASE_COMMON_SRCS]
        delta_small_obj = os.path.join(
            obj_dir, _CLD2_DELTA_SMALL_SRC.replace(".cc", ".o"))
        delta_full_obj = os.path.join(
            full_dir, _CLD2_DELTA_FULL_SRC.replace(".cc", ".o"))
        small_objs = [os.path.join(small_dir, s.replace(".cc", ".o"))
                      for s in _CLD2_SMALL_SRCS]
        full_table_objs = [os.path.join(full_dir, s.replace(".cc", ".o"))
                           for s in _CLD2_FULL_TABLE_SRCS]
        chrome2_objs = common_objs + [delta_small_obj] + small_objs
        full_objs = common_objs + [delta_full_obj] + full_table_objs
        if self.options.shared:
            # noshell 链接：list 形式直接 exec（不经 sh -c），长目标
            # 列表不再触发 sh 为参数处理建 /tmp 临时文件；同时把
            # 完整参数另存一份 .rsp（build_folder 下可写目录）便于
            # 失败时复现，不经 shell 展开。
            for _rsp_name, _objs, _lib, _soname in (
                    ("link_cld2.rsp", chrome2_objs,
                     lib_cld2, "libcld2.so"),
                    ("link_full.rsp", full_objs,
                     lib_full, "libcld2_full.so")):
                _rsp = os.path.join(self.build_folder, _rsp_name)
                with open(_rsp, "w", encoding="utf-8") as _f:
                    _f.write("\n".join(
                        ["-shared", "-fPIC"] + _objs +
                        ["-o", _lib, "-Wl,-soname,%s" % _soname]))
                self._run_noshell(
                    [cxx, "-shared", "-fPIC"] + _objs +
                    ["-o", _lib, "-Wl,-soname,%s" % _soname])
        else:
            _conf_ar = self.conf.get("tools.build:compiler_executables:ar",
                                     default="llvm-ar", check_type=str)
            ar = self._resolve_tool(_conf_ar, "llvm-ar", "ar")
            self._run_noshell(
                [ar, "rcs", lib_cld2] + chrome2_objs)
            self._run_noshell(
                [ar, "rcs", lib_full] + full_objs)

        # ---- Upstream official tests (must run, blocking) ----
        # internal/cld2_unittest.cc covers ~85 script/letter/quadgram cases,
        # internal/cld2_unittest_full.cc covers the full 160-language tables.
        ut_small = os.path.join(self.build_folder, "cld2_unittest_chrome_2")
        ut_full = os.path.join(self.build_folder, "cld2_unittest_full")
        self._run_noshell(
            [cxx] + cxxflags + [os.path.join(src_dir, "cld2_unittest.cc")] +
            chrome2_objs + ["-o", ut_small])
        self._run_noshell(
            [cxx] + cxxflags + [os.path.join(src_dir, "cld2_unittest_full.cc")] +
            full_objs + ["-o", ut_full])
        # shell-free 运行上游二进制（不经 sh -c，无 /tmp 临时文件）：
        # 任一非零退出即抛异常，标记仅在双二进制 exit 0 后可达。
        self._run_noshell([ut_small])
        self._run_noshell([ut_full])
        _upstream_marker = {
            "status": "passed",
            "framework": "custom",
            "command": "./cld2_unittest_chrome_2 && ./cld2_unittest_full",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(_upstream_marker, ensure_ascii=False))
        # Dual channel: conan may route output.info to stderr while the
        # harness scans stdout tail, so also print() the identical line.
        print("HMBS_UPSTREAM_TEST_RESULT="
              + json.dumps(_upstream_marker, ensure_ascii=False),
              flush=True)
        # Persist the marker so test_package can re-emit it on Conan
        # cache hits (build() is skipped then, marker would vanish).
        with open(os.path.join(
                self.build_folder, "hmbs_upstream_result.json"),
                "w", encoding="utf-8") as _f:
            json.dump(_upstream_marker, _f, ensure_ascii=False)

    def package(self):
        copy(self, "hmbs_upstream_result.json",
             src=self.build_folder, dst=self.package_folder)
        if self.options.shared:
            copy(self, "libcld2*.so*",
                 src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libcld2*.a",
                 src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Preserve public/<->internal relative include layout
        # (public/compact_lang_det.h includes ../internal/*.h).
        copy(self, "*.h", src=os.path.join(self.source_folder, "public"),
             dst=os.path.join(self.package_folder, "include", "cld2", "public"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "internal"),
             dst=os.path.join(self.package_folder, "include", "cld2", "internal"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cld2", "cld2_full"]
        self.cpp_info.includedirs = ["include/cld2/public"]
        self.cpp_info.set_property("cmake_file_name", "cld2")
        self.cpp_info.set_property("cmake_target_name", "cld2::cld2")
