#!/usr/bin/env python3
"""Conan recipe for ctemplate 2.4 (OlafvdSpek/ctemplate).

ctemplate 是 Google 的 C++ 模板引擎（TemplateDictionary/Template 展开）。
零第三方依赖（W0 预检通过），仅用 pthread。

OHOS 适配要点（本包核心难点）：
- git tag 与 Debian orig tarball 内容相同（sha256 已核实一致），**均无预生成
  configure**：autogen.sh 依赖 autoconf/automake/libtool，沙箱不具备
  → 不走 autotools，conanfile 内直接完成 configure 的三件事：
  (1) 手工合成 config.h（本目录 config.h，OHOS 特性集已逐项核实，不确定的
      一律不定义走 fallback）；
  (2) .h.in → .h 替换 7 个 @var@（hash_map→<unordered_map>/std、attribute→1、
      dllexport→空，与 m4/stl_hash.m4 在现代 clang 上的探测结果一致）；
  (3) 用 sys.executable 跑上游 generate_fsm.py 生成 3 个 fsm 头（BUILT_SOURCES）。
- 上游测试体系完整：20 个二进制（9 对 threads/nothreads + statemachine_test
  + generate_fsm_c_test）+ 3 个 shell 脚本，自带 mini harness（非 gtest）。
  build() 内全部 23 个实跑：库编 4 变体（threads/nothreads × release/debug）
  与上游 Makefile.am 的四套 lib 一一对应。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os
import shutil
import subprocess
import sys


LIB_SOURCES = [
    "src/base/arena.cc",
    "src/per_expand_data.cc",
    "src/template.cc",
    "src/template_annotator.cc",
    "src/template_cache.cc",
    "src/template_dictionary.cc",
    "src/template_modifiers.cc",
    "src/template_namelist.cc",
    "src/template_pathops.cc",
    "src/template_string.cc",
    "src/htmlparser/htmlparser.cc",
    "src/htmlparser/jsparser.cc",
    "src/htmlparser/statemachine.cc",
]

HEADER_SUBSTS = {
    "@ac_cv_cxx_hash_map@": "<unordered_map>",
    "@ac_cv_cxx_hash_set@": "<unordered_set>",
    "@ac_cv_cxx_hash_namespace@": "std",
    "@ac_google_attribute@": "1",
    "@ac_have_attribute_weak@": "1",
    "@ac_windows_dllexport@": "",
    "@ac_windows_dllexport_defines@": "",
}

# (名字, 测试源, 额外编译进二进制的源)
BIN_TESTS = [
    ("compile_test", "src/tests/compile_test.cc", []),
    ("template_test_util_test", "src/tests/template_test_util_test.cc",
     ["src/template_dictionary.cc", "src/tests/template_test_util.cc"]),
    ("template_dictionary_unittest", "src/tests/template_dictionary_unittest.cc",
     ["src/tests/template_test_util.cc"]),
    ("template_modifiers_unittest", "src/tests/template_modifiers_unittest.cc",
     ["src/tests/template_test_util.cc"]),
    ("template_setglobals_unittest", "src/tests/template_setglobals_unittest.cc",
     ["src/tests/template_test_util.cc"]),
    ("template_cache_test", "src/tests/template_cache_test.cc",
     ["src/tests/template_test_util.cc"]),
    ("template_unittest", "src/tests/template_unittest.cc",
     ["src/tests/template_test_util.cc"]),
    ("template_regtest", "src/tests/template_regtest.cc", []),
    ("htmlparser_test", "src/tests/htmlparser_cpp_test.cc", []),
]


class CtemplateConan(ConanFile):
    name = "ctemplate"
    version = "2.4"
    description = "Google ctemplate - C++ template expansion engine"
    license = "BSD-3-Clause"
    homepage = "https://github.com/OlafvdSpek/ctemplate"
    url = ""  # CI fills this
    topics = ("template", "html", "string-formatting")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        copy(self, "config.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # HMFS 设备 /tmp 不可写：TmpFile 硬编码 "/tmp/" 会让所有写临时文件的
        # 测试（template_cache_test 的 TestTemplateSearchPath 等）fopen 失败
        # SIGABRT（CI #43922 实测）。改走 TMPDIR，缺省回落 ./（build() 以
        # 可写构建目录为 cwd 运行测试）。
        util = os.path.join(self.source_folder, "src", "tests", "template_test_util.cc")
        with open(util, encoding="utf-8") as f:
            content = f.read()
        old = ('static string TmpFile(const char* basename) {\n'
               '  return string("/tmp/") + basename;\n'
               '}')
        assert old in content, "TmpFile 实现已变更，需同步本替换"
        new = ('static string TmpFile(const char* basename) {\n'
               '  const char* td = getenv("TMPDIR");\n'
               '  if (td && td[0]) return string(td) + "/" + basename;\n'
               '  return string("./") + basename;\n'
               '}')
        with open(util, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(old, new))
        # HMFS 不支持硬链接：template_unittest 的 TemplateNamelist 用
        # link() 建 f1_copy/f2_copy/f3_copy，EPERM → ASSERT SIGABRT
        # （CI #43954 实测）。改为读内容复制 + utime 回填 src 的 mtime——
        # 硬链接语义是共享 inode mtime；StringToFile 会赋"新"mock 时间
        # （mock_time++），使 modtime > after_time 违反
        # GetLastmodTime 断言（CI #43966 实测），故必须回填。
        uni = os.path.join(self.source_folder, "src", "tests", "template_unittest.cc")
        with open(uni, encoding="utf-8") as f:
            ucontent = f.read()
        old_test = ("// Tests all the static methods in TemplateNamelist\n"
                    "TEST(Template, TemplateNamelist) {")
        assert old_test in ucontent, "TemplateNamelist 测试入口已变更，需同步替换"
        helper = (
            "// HarmonyOS: HMFS 无硬链接，link() 替代品（共享 mtime 语义靠 utime 回填）\n"
            "#include <sys/stat.h>\n"
            "#include <utime.h>\n"
            "static void CopyTemplateFile(const string& src, const string& dst) {\n"
            "  FILE* fp = fopen(src.c_str(), \"rb\");\n"
            "  ASSERT(fp);\n"
            "  string content;\n"
            "  char buf[4096];\n"
            "  size_t n;\n"
            "  while ((n = fread(buf, 1, sizeof buf, fp)) > 0) content.append(buf, n);\n"
            "  fclose(fp);\n"
            "  fp = fopen(dst.c_str(), \"wb\");\n"
            "  ASSERT(fp);\n"
            "  ASSERT(fwrite(content.data(), 1, content.size(), fp) == content.size());\n"
            "  fclose(fp);\n"
            "  struct stat st;\n"
            "  ASSERT(stat(src.c_str(), &st) == 0);\n"
            "  struct utimbuf tb;\n"
            "  tb.actime = st.st_atime;\n"
            "  tb.modtime = st.st_mtime;\n"
            "  ASSERT(utime(dst.c_str(), &tb) == 0);\n"
            "}\n\n"
            + old_test
        )
        ucontent = ucontent.replace(old_test, helper)
        old_links = ("  ASSERT(link(f1.c_str(), f1_copy.c_str()) == 0);\n"
                     "  ASSERT(link(f2.c_str(), f2_copy.c_str()) == 0);\n"
                     "  ASSERT(link(f3.c_str(), f3_copy.c_str()) == 0);")
        assert old_links in ucontent, "link() 断言块已变更，需同步替换"
        ucontent = ucontent.replace(
            old_links,
            "  CopyTemplateFile(f1, f1_copy);\n"
            "  CopyTemplateFile(f2, f2_copy);\n"
            "  CopyTemplateFile(f3, f3_copy);")
        with open(uni, "w", encoding="utf-8", newline="\n") as f:
            f.write(ucontent)

    def _gen_headers(self, work):
        """.h.in → .h 替换 + generate_fsm.py 生成 3 个 fsm 头"""
        ctpl_inc = os.path.join(work, "src", "ctemplate")
        for fn in os.listdir(ctpl_inc):
            if not fn.endswith(".h.in"):
                continue
            path = os.path.join(ctpl_inc, fn)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            for k, v in HEADER_SUBSTS.items():
                content = content.replace(k, v)
            with open(path[:-3], "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        gen = os.path.join(work, "src", "htmlparser", "generate_fsm.py")
        for cfg, out in [
            ("src/htmlparser/htmlparser_fsm.config", "src/htmlparser/htmlparser_fsm.h"),
            ("src/htmlparser/jsparser_fsm.config", "src/htmlparser/jsparser_fsm.h"),
            ("src/tests/statemachine_test_fsm.config", "src/tests/statemachine_test_fsm.h"),
        ]:
            out_path = os.path.join(work, out)
            with open(out_path, "w") as f:
                subprocess.run(
                    [sys.executable, gen, os.path.join(work, cfg)],
                    stdout=f, check=True, cwd=work,
                )

    def _build_lib(self, work, cxx, extra_flags, out_name):
        """编一个库变体（13 个 .cc → .a）"""
        objs = []
        inc = f"-I{work} -I{os.path.join(work, 'src')}"
        for i, s in enumerate(LIB_SOURCES):
            obj = os.path.join(self.build_folder, f"{out_name}_{i}.o")
            # -DHAVE_CONFIG_H 必带：template.cc 等库源文件的条件包含
            # `#ifdef HAVE_CONFIG_H / #include "config.h"`，缺了它
            # HASH_MAP_H/HASH_NAMESPACE 等宏全空 → 编译失败（CI #43779 实测）。
            self.run(f"{cxx} -std=c++11 -O2 -fPIC -DHAVE_CONFIG_H {extra_flags} {inc} -c "
                     f"{os.path.join(work, s)} -o {obj}")
            objs.append(obj)
        ar = os.path.join(self.build_folder, out_name)
        self.run(f"ar rcs {ar} " + " ".join(objs))
        return ar

    def build(self):
        src = self.source_folder
        bf = self.build_folder
        work = os.path.join(bf, "work")
        shutil.copytree(src, work)
        copy(self, "config.h", src=self.export_sources_folder, dst=work)
        self._gen_headers(work)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # 上游 4 套库变体一一对应（Makefile.am 的 libctemplate{,_nothreads}{,_debug}）
        lib_rel = self._build_lib(work, cxx, "-DNDEBUG -pthread", "libctemplate.a")
        lib_rel_nt = self._build_lib(work, cxx, "-DNDEBUG -DNO_THREADS", "libctemplate_nothreads.a")
        lib_dbg = self._build_lib(work, cxx, "-pthread", "libctemplate_dbg.a")
        lib_dbg_nt = self._build_lib(work, cxx, "-DNO_THREADS", "libctemplate_nothreads_dbg.a")

        # 层1：上游测试全量实跑（20 二进制 + 3 脚本 = 23）
        inc = (f"-I{work} -I{os.path.join(work, 'src')} "
               f"-I{os.path.join(work, 'src', 'tests')}")
        # TMPDIR 指向可写构建目录：diff_tpl_auto_escape_unittest.sh 的
        # ${TMPDIR-"/tmp"} 在 HMFS 设备上同样会落到不可写的 /tmp。
        env = f"TEMPLATE_ROOTDIR={work} TMPDIR={bf}"
        for name, test_src, extra in BIN_TESTS:
            for nt, lib in (("", lib_dbg), ("_nothreads", lib_dbg_nt)):
                flags = "-DNO_THREADS" if nt else "-pthread"
                exe = os.path.join(bf, f"{name}{nt}")
                srcs = " ".join([os.path.join(work, test_src)] +
                                [os.path.join(work, s) for s in extra])
                self.run(f"{cxx} -std=c++11 -O1 {flags} {inc} {srcs} {lib} "
                         f"-o {exe} -pthread")
                self.run(f"{env} {exe}", cwd=bf)
        # statemachine_test：statemachine.cc 以 C 模式再编一遍（上游 cp 成 .c）
        sm_c = os.path.join(bf, "statemachine.c")
        shutil.copy(os.path.join(work, "src", "htmlparser", "statemachine.cc"), sm_c)
        # statemachine.h 直接 #include <config.h>（无条件，非 HAVE_CONFIG_H
        # 守护），config.h 在 work 根目录，必须补 -I{work}（CI #44003 实测
        # 'config.h' file not found；上游 automake 恒带 -I$(top_builddir)）。
        self.run(f"{cc} -O1 -I{work} -I{os.path.join(work, 'src')} "
                 f"-I{os.path.join(work, 'src', 'htmlparser')} -c {sm_c} "
                 f"-o {os.path.join(bf, 'statemachine_c.o')}")
        self.run(f"{cc} -O1 -I{work} -I{os.path.join(work, 'src')} "
                 f"{os.path.join(work, 'src', 'tests', 'statemachine_test.c')} "
                 f"{os.path.join(bf, 'statemachine_c.o')} "
                 f"-o {os.path.join(bf, 'statemachine_test')}")
        self.run("./statemachine_test", cwd=bf)
        # generate_fsm_c_test：验证 sample_fsm.c 可作为 C 编译
        # generate_fsm_c_test.c 同样经 htmlparser/statemachine.h 引入 <config.h>
        self.run(f"{cc} -O1 -I{work} -I{os.path.join(work, 'src')} "
                 f"{os.path.join(work, 'src', 'tests', 'generate_fsm_c_test.c')} "
                 f"-o {os.path.join(bf, 'generate_fsm_c_test')}")
        self.run("./generate_fsm_c_test", cwd=bf)
        # 2 个辅助二进制（上游链 nothreads 库）+ 3 个脚本
        for tool in ("make_tpl_varnames_h", "diff_tpl_auto_escape"):
            # 这两个工具源同样 #ifdef HAVE_CONFIG_H 包含 config.h
            self.run(f"{cxx} -std=c++11 -O1 -DNO_THREADS -DHAVE_CONFIG_H {inc} "
                     f"{os.path.join(work, 'src', tool + '.cc')} {lib_dbg_nt} "
                     f"-o {os.path.join(bf, tool)}")
        os.makedirs(os.path.join(bf, "tmp"), exist_ok=True)
        self.run(f"sh {os.path.join(src, 'src', 'tests', 'generate_fsm_test.sh')} {src}")
        # make_tpl_varnames_h_unittest.sh 的 expected_okN=`cat <<EOF` here-doc
        # 由 shell 建临时文件：HMFS 的 sh 无视 TMPDIR 硬落 /tmp（只读）→
        # "can't create temporary file"（CI #44037/#44049 实测，TMPDIR= 前缀
        # 对 sh 无效）；bash 的 here-doc 临时文件遵循 TMPDIR，故改用
        # /data/service/hnp/bin/bash 运行（R33 既有约定）+ TMPDIR={bf}。
        bash = "/data/service/hnp/bin/bash"
        self.run(f"TMPDIR={bf} "
                 f"{bash} {os.path.join(src, 'src', 'tests', 'make_tpl_varnames_h_unittest.sh')} "
                 f"{os.path.join(bf, 'make_tpl_varnames_h')} "
                 f"{os.path.join(bf, 'tmp', 'mkv')}")
        self.run(f"TMPDIR={bf} "
                 f"{bash} {os.path.join(src, 'src', 'tests', 'diff_tpl_auto_escape_unittest.sh')} "
                 f"{os.path.join(bf, 'diff_tpl_auto_escape')} "
                 f"{os.path.join(bf, 'tmp', 'difftpl')}")

    def package(self):
        work = os.path.join(self.build_folder, "work")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(work, "src", "ctemplate"),
             dst=os.path.join(self.package_folder, "include", "ctemplate"))
        copy(self, "libctemplate.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libctemplate_nothreads.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ctemplate"]
        self.cpp_info.system_libs = ["pthread"]
