#!/usr/bin/env python3
"""Conan recipe — libcifpp 10.0.4 (CMake, C++20).

CIF (Crystallographic Information File) C++ library (PDB-REDO).
v10.0.4 供 cif-tools 2.0.0 使用（其 find_package(cifpp 10) 要求主版本 10）。

OHOS adaptation notes（相对 v9 配方的增量）：
- **C++23 → C++20**：上游 `target_compile_features(cifpp PUBLIC cxx_std_23)`，
  但 OHOS clang15 无 `-std=c++23`（仅到 c++2b），且实测 v10 源码**未使用任何
  C++23 独有特性**（std::expected/print/to_underlying/byteswap/mdspan/flat_map/
  stacktrace 全 0 处）——ranges/format/concepts/`<=>` 均为 C++20 特性。
- **std::ranges 需打开实验开关**：OHOS libc++15 的 `__config` 默认定义
  `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，导致 `std::ranges::sort/find_if` 等**算法**
  不存在（v10 共 80 处）。加 `-D_LIBCPP_ENABLE_EXPERIMENTAL` 即恢复（实测编译+
  链接+运行通过；ranges 为 header-only 模板，不依赖库符号）。
- **std::format → fmt**：`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 且 libc++.so 内**无**
  format_error 等符号（`llvm-nm -D` 计数 0），打开实验开关也仅能编译、**链接失败**。
  v10 共 94 处 std::format（12 文件，0 处自定义 formatter）→ 机械替换为 fmt::format。
- key_element_type 聚合 → 补构造函数（C++20 P0960 聚合括号初始化，libc++15 的
  construct_at 不支持）。
- FindAtomic.cmake 的 check_cxx_source_runs 交叉编译下误判 → OHOS 强制
  _CXX_ATOMIC_BUILTIN=1。
- 依赖：pcre2（libpcre2-8 via pkg-config）+ FastFloat 8.0 + fmt + zlib + eigen3
  + sqlite3（v10 新增，BUILD_SQLITE_INTERFACE 默认 ON）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class LibcifppConan(ConanFile):
    name = "libcifpp"
    version = "10.0.4"
    description = "C++ library for manipulating CIF (Crystallographic Information File) files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/PDB-REDO/libcifpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 默认静态：ohpcd 的 zlib/1.3.1 仅提供静态 libz.a（非 PIC），libcifpp 若编成
    # 共享库链接它会报 relocation R_AARCH64_* against 'z_errmsg'（需 -fPIC）
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 上游声明 cxx_std_23，但 OHOS clang15 不支持 -std=c++23（且源码未用 C++23
        # 特性），统一按 C++20 编译
        if self.settings.get_safe("compiler.cppstd"):
            self.settings.compiler.cppstd = "20"

    def requirements(self):
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        self.requires("fast_float/8.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/7.1.3", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/3.4.0", transitive_headers=True, transitive_libs=True)
        # v10 新增：BUILD_SQLITE_INTERFACE 默认 ON，不用系统 sqlite3 会走
        # FetchContent 下载 sqlite amalgamation（CI 禁网）
        self.requires("sqlite3/3.53.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_cxx20()
        self._patch_format_to_fmt()
        self._patch_key_element_type()
        self._patch_aggregate_ctors()
        self._patch_cxx23_features()
        self._patch_atomic()

    def _patch_cxx20(self):
        """cxx_std_23 → cxx_std_20（OHOS clang15 不支持 c++23）。"""
        p = os.path.join(self.source_folder, "CMakeLists.txt")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        if "cxx_std_23" in t:
            t = t.replace("cxx_std_23", "cxx_std_20")
            open(p, "w", encoding="utf-8").write(t)
            self.output.info("patched CMakeLists.txt: cxx_std_23 -> cxx_std_20")

    def _patch_format_to_fmt(self):
        """std::format -> fmt::format（OHOS libc++15 无 std::format 实现）。

        v10 的 format.hpp 已无 fmt 回退分支（上游直接 `using std::format`），
        libc++.so 内亦无 format_error 等符号（llvm-nm -D 计数 0）——因此按站点
        机械替换：`#include <format>` → `<fmt/format.h>`，`std::format(` →
        `fmt::format(`。已核实 0 处自定义 std::formatter、0 处 std::vformat。
        """
        subs = ("include/cif++/condition.hpp", "include/cif++/point.hpp",
                "include/cif++/format.hpp", "include/cif++/utilities.hpp",
                "src/cql.cpp", "src/dictionary_parser.cpp", "src/model.cpp",
                "src/parser.cpp", "src/point.cpp", "src/utilities.cpp",
                "src/validate.cpp", "src/pdb/cif2pdb.cpp", "src/pdb/pdb2cif.cpp")
        touched = 0
        for rel in subs:
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                continue
            t = open(path, encoding="utf-8", errors="ignore").read()
            orig = t
            if "#include <format>" in t:
                t = t.replace("#include <format>", "#include <fmt/format.h>")
            if "std::format" in t:
                t = t.replace("std::format", "fmt::format")
            if t != orig:
                open(path, "w", encoding="utf-8").write(t)
                touched += 1
        # 兜底：全树扫描（上游文件列表可能变动）
        for root, _dirs, files in os.walk(os.path.join(self.source_folder, "src")):
            for fn in files:
                if not fn.endswith((".cpp", ".hpp", ".h")):
                    continue
                path = os.path.join(root, fn)
                t = open(path, encoding="utf-8", errors="ignore").read()
                orig = t
                if "#include <format>" in t:
                    t = t.replace("#include <format>", "#include <fmt/format.h>")
                if "std::format" in t:
                    t = t.replace("std::format", "fmt::format")
                if t != orig:
                    open(path, "w", encoding="utf-8").write(t)
                    touched += 1
        self.output.info(f"patched std::format -> fmt::format ({touched} files)")

    def _patch_key_element_type(self):
        """key_element_type 的 C++20 聚合问题（与 v9 处理方式不同，切勿照搬 v9）。

        v10 里 `key_element_type` 同时被两种写法使用：
          (a) 指定初始化器：`m_cat[{ { .name = "id", .value = m_id } }]`
              （model.hpp 4 处）—— **要求它保持聚合**；
          (b) 多参 emplace_back（3 处）：
              category.cpp:373 `k2.emplace_back(std::string{ fld }, "")`
              condition.cpp:238/248 `lookup.emplace_back(s->m_item_name, s->m_value[, true])`
              —— 触发 C++20 聚合括号初始化（P0960），libc++15 的 construct_at
              不支持，报 'no matching function for call to construct_at'。
        v9 的解法（给 key_element_type 加构造函数）会把聚合打破，反而让 (a) 全数
        编译失败（实测 34 处 'no viable overloaded operator[]'）。因此 v10 采用
        **相反策略：保持聚合不变，把 (b) 的 3 处调用改为显式聚合构造**。
        """
        site = [
            ("src/category.cpp",
             'k2.emplace_back(std::string{ fld }, "");',
             'k2.emplace_back(category::key_type::value_type{ std::string{ fld }, "", false });'),
            ("src/condition.cpp",
             "lookup.emplace_back(s->m_item_name, s->m_value);",
             "lookup.emplace_back(category::key_type::value_type{ s->m_item_name, s->m_value, false });"),
            ("src/condition.cpp",
             "lookup.emplace_back(s->m_item_name, s->m_value, true);",
             "lookup.emplace_back(category::key_type::value_type{ s->m_item_name, s->m_value, true });"),
        ]
        hits = 0
        for rel, old, new in site:
            p = os.path.join(self.source_folder, rel)
            if not os.path.isfile(p):
                continue
            t = open(p, encoding="utf-8", errors="ignore").read()
            if old in t:
                t = t.replace(old, new)
                open(p, "w", encoding="utf-8").write(t)
                hits += 1
        if hits:
            self.output.info(
                f"patched {hits} 处 emplace_back -> 显式聚合构造（保持 key_element_type "
                "为聚合，避开 libc++15 construct_at 的 P0960 缺口）")

    def _patch_aggregate_ctors(self):
        """clang15 未实现 C++20 P0960（聚合括号初始化，Clang 16 起才支持）——
        实测 `Agg x(1, 2.0);` 与 `std::construct_at(p, 1, 2.0)` 均报
        'no matching constructor for initialization of Agg'。

        libcifpp v10 用 `std::make_unique<T>(args...)` 构造**聚合**，故需为这些
        聚合补显式构造函数。已确认 virtual_table / virtual_cursor 无指定初始化器
        用法（grep `.<member> =` 为空），因此补 ctor 安全（与 key_element_type 不同，
        后者的调用点改写而非补 ctor）。
        """
        p = os.path.join(self.source_folder, "src", "cql.cpp")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        hits = 0

        # ① virtual_table
        old_vt = """	std::stack<category> m_rollback_buffer;
	std::vector<std::string> m_items;
};"""
        new_vt = """	std::stack<category> m_rollback_buffer;
	std::vector<std::string> m_items;

	virtual_table(sqlite3_vtab b, connection_impl &c, category &cat, datablock &db)
		: base(b)
		, m_connection_impl(c)
		, m_cat(cat)
		, m_db(db)
	{
	}
};"""
        if old_vt in t and "virtual_table(sqlite3_vtab b" not in t:
            t = t.replace(old_vt, new_vt, 1)
            hits += 1

        # ② virtual_cursor
        old_vc = """struct virtual_cursor
{
	sqlite3_vtab_cursor base;

	std::unique_ptr<conditional_iterator_proxy<>> m_result;
	conditional_iterator_proxy<>::iterator m_cur;
};"""
        new_vc = """struct virtual_cursor
{
	sqlite3_vtab_cursor base;

	std::unique_ptr<conditional_iterator_proxy<>> m_result;
	conditional_iterator_proxy<>::iterator m_cur;

	explicit virtual_cursor(sqlite3_vtab_cursor b)
		: base(b)
	{
	}
};"""
        if old_vc in t:
            t = t.replace(old_vc, new_vc, 1)
            hits += 1

        if hits:
            open(p, "w", encoding="utf-8").write(t)
            self.output.info(f"patched cql.cpp: {hits} 个聚合补构造函数"
                             "（clang15 无 P0960）")

    def _patch_cxx23_features(self):
        """v10 用到两处 OHOS clang15/libc++15 不具备的 C++20/23 能力：

        ① `std::unreachable()`（src/item.cpp:199）—— C++23 起才有。实测
           `-std=c++2b` 下可用，但 c++20 下报 'no member named unreachable'。
           因本配方按 C++20 编译，改用编译器内建 `__builtin_unreachable()`。
        ② `std::string_view <=> std::string_view`（include/cif++/item.hpp:442）
           —— libc++15 的 basic_string_view **未提供** operator<=>（实测 c++20 与
           c++2b 下均报 invalid operands），改为按 compare() 显式映射到
           std::partial_ordering。
        """
        # ① std::unreachable -> __builtin_unreachable()
        p = os.path.join(self.source_folder, "src", "item.cpp")
        if os.path.isfile(p):
            t = open(p, encoding="utf-8", errors="ignore").read()
            if "std::unreachable()" in t:
                t = t.replace("std::unreachable()", "__builtin_unreachable()")
                open(p, "w", encoding="utf-8").write(t)
                self.output.info("patched item.cpp: std::unreachable -> "
                                 "__builtin_unreachable (C++23)")
        # ② string_view 三路比较 -> compare() + partial_ordering
        p = os.path.join(self.source_folder, "include", "cif++", "item.hpp")
        if os.path.isfile(p):
            t = open(p, encoding="utf-8", errors="ignore").read()
            old = "case TEXT: result = m_data.sv() <=> rhs.m_data.sv();"
            new = ("case TEXT: {\n"
                   "\t\t\t\t\t// libc++15 的 basic_string_view 未提供 operator<=>\n"
                   "\t\t\t\t\tconst int c = m_data.sv().compare(rhs.m_data.sv());\n"
                   "\t\t\t\t\tresult = c < 0 ? std::partial_ordering::less\n"
                   "\t\t\t\t\t       : c > 0 ? std::partial_ordering::greater\n"
                   "\t\t\t\t\t               : std::partial_ordering::equivalent;\n"
                   "\t\t\t\t\tbreak;\n"
                   "\t\t\t\t}")
            if old in t:
                t = t.replace(old, new)
                open(p, "w", encoding="utf-8").write(t)
                self.output.info("patched item.hpp: string_view <=> 改为 compare()"
                                 "（libc++15 无 string_view operator<=>）")

    def _patch_atomic(self):
        """FindAtomic.cmake 用 check_cxx_source_runs（交叉编译无法运行测试程序）
        → 误判需 -latomic。OHOS 强制 _CXX_ATOMIC_BUILTIN=1 跳过。"""
        p = os.path.join(self.source_folder, "cmake", "FindAtomic.cmake")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        if "set(_CXX_ATOMIC_BUILTIN 1)" in t:
            return
        if 'set(code [[\n#include <atomic>' in t:
            t = t.replace(
                'set(code [[\n#include <atomic>',
                'if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")\n'
                '  set(_CXX_ATOMIC_BUILTIN 1)\n'
                'endif()\nset(code [[\n#include <atomic>',
                1)
            t = t.replace(
                'check_cxx_source_runs("${code}" _CXX_ATOMIC_BUILTIN)',
                'check_cxx_source_runs("${code}" _CXX_ATOMIC_BUILTIN)',
            )
            open(p, "w", encoding="utf-8").write(t)
            self.output.info("patched FindAtomic.cmake: OHOS 强制 _CXX_ATOMIC_BUILTIN=1")

    def generate(self):
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # libcifpp 用 pkg_check_modules(PCRE2 libpcre2-8)，PkgConfigDeps 生成的是
        # pcre2.pc → 复制别名（同 girepository-2.0.pc / libudev.pc 先例）
        src_pc = os.path.join(self.generators_folder, "pcre2.pc")
        dst_pc = os.path.join(self.generators_folder, "libpcre2-8.pc")
        if os.path.isfile(src_pc) and not os.path.isfile(dst_pc):
            shutil.copy2(src_pc, dst_pc)
            self.output.info("copied pcre2.pc -> libpcre2-8.pc (pkg_check_modules alias)")

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CCD 下载（默认 ON，configure 时 file(DOWNLOAD) 拉 components.cif）→ 关闭
        tc.variables["CIFPP_DOWNLOAD_CCD"] = "OFF"
        # 上游测试用 FetchContent 拉 catch2（CI 禁网）→ 关闭
        tc.variables["BUILD_TESTING"] = "OFF"
        # examples 默认 ON：其 CMakeLists 只 `target_link_libraries(example
        # cifpp::cifpp)`，而 cifpp 对 fmt 是 PRIVATE 链接 —— 本配方把
        # std::format 换成 fmt::format 后，libcifpp.a 会引用 fmt 符号，
        # examples 因缺 -lfmt 而链接失败（实测 undefined symbol:
        # fmt::v7::detail::vformat）。examples 不被 install，直接关闭。
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # 【OHOS 关键】恢复 std::ranges 算法（libc++15 默认标为 incomplete 而关闭）
        for flag_list in (tc.extra_cxxflags, tc.extra_cflags):
            if "-D_LIBCPP_ENABLE_EXPERIMENTAL" not in flag_list:
                flag_list.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")
        # 依赖 include/lib 路径注入
        for _n, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                f = "-I" + p
                if f not in tc.extra_cxxflags:
                    tc.extra_cxxflags.append(f)
            for p in dep.cpp_info.libdirs:
                f = "-L" + p
                if f not in tc.extra_sharedlinkflags:
                    tc.extra_sharedlinkflags.append(f)
                if f not in tc.extra_exelinkflags:
                    tc.extra_exelinkflags.append(f)
        # FastFloat_DIR / Eigen3_DIR / SQLite3_DIR：遍历依赖 package_folder 探测
        # config 文件（不依赖 ref.name 字符串匹配）
        for _n, dep in self.dependencies.items():
            pf = dep.package_folder
            if not pf:
                continue
            if "FastFloat_DIR" not in tc.variables:
                for cand in (os.path.join(pf, "share", "cmake", "FastFloat"),
                             os.path.join(pf, "lib", "cmake", "FastFloat"),
                             os.path.join(pf, "lib", "cmake"),
                             os.path.join(pf, "share", "cmake")):
                    if os.path.isfile(os.path.join(cand, "FastFloatConfig.cmake")):
                        tc.variables["FastFloat_DIR"] = os.path.abspath(cand)
                        break
            if "Eigen3_DIR" not in tc.variables:
                for cand in (os.path.join(pf, "share", "eigen3", "cmake"),
                             os.path.join(pf, "share", "cmake"),
                             os.path.join(pf, "lib", "cmake", "eigen3")):
                    if os.path.isfile(os.path.join(cand, "Eigen3Config.cmake")):
                        tc.variables["Eigen3_DIR"] = os.path.abspath(cand)
                        break
            if "SQLite3_DIR" not in tc.variables:
                for cand in (os.path.join(pf, "lib", "cmake", "SQLite3"),
                             os.path.join(pf, "share", "cmake", "SQLite3"),
                             os.path.join(pf, "lib", "cmake")):
                    if os.path.isfile(os.path.join(cand, "SQLite3Config.cmake")):
                        tc.variables["SQLite3_DIR"] = os.path.abspath(cand)
                        break
            # sqlite3 无 config 时退回 FindSQLite3 的 include/lib 提示
            if "SQLite3_DIR" not in tc.variables and os.path.isdir(
                    os.path.join(pf, "include")):
                inc = os.path.join(pf, "include")
                if os.path.isfile(os.path.join(inc, "sqlite3.h")):
                    tc.variables["SQLite3_INCLUDE_DIR"] = os.path.abspath(inc)
                    tc.variables["SQLite3_LIBRARY"] = os.path.abspath(
                        os.path.join(pf, "lib", "libsqlite3.a"))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cifpp")
        self.cpp_info.libs = ["cifpp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["pcre2::pcre2", "fmt::fmt", "zlib::zlib",
                                  "fast_float::fast_float", "eigen::eigen",
                                  "sqlite3::sqlite3"]
