# ohcount 4.0.0 适配笔记

## 编译环境
- 构建系统: custom（沿用上游 bash build 脚本的编译/链接方式；无 autotools/cmake/meson）
- 编译日期: 2026-09-24（初版 2026-09-22，09-24 修复上游测试运行阻塞并集成实跑）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
  - 路径由 recipe 从 conan profile `ohos-aarch64` 的
    `tools.build:compiler_executables={"c": "/data/service/hnp/bin/clang", ...}`
    读取（R33：不使用裸 $CC/$CFLAGS）
- 依赖: pcre/8.45（静态 libpcre.a）、libmagic/5.48（静态 libmagic.a），均已发布在 ohpcd
- 状态: built

## 关键背景：为什么配方携带 generated/ 预生成源码
官方 GitHub tarball（sha256 d71f69fd…，与 conandata 一致，实测一致）不包含
bin/ohcount，也不包含 Ragel/gperf 生成产物：
- `src/hash`：`cd src/hash && sh ./generate_headers`（gperf → language_hash.c + 6 个 *_hash.h）
- `src/parsers`：`cd src/parsers && bash ./compile`（ragel，107 个 .rl → 107 个 .h）

制品仓无 ragel/gperf 包，CI 无法在构建期生成。故在设备端用 ragel 6.10 + gperf 3.1
**预生成纯文本源码**随配方提交（`generated/`，合计 114 个文件，全部为 .h/.c 文本，
无任何二进制）：
- `generated/hash/`：7 个（language_hash.c + extension/filename/disambiguatefunc/
  cppheader/parser/option 共 6 个 *_hash.h）
- `generated/parsers/`：107 个（每个 .rl 对应一个 .h）

`build()` 将两组产物覆盖到源码树 `src/hash`、`src/parsers` 后再真编译，不使用任何
预构建二进制（R19/R33）。

生成命令（与提交内容一致的可复现步骤）：
```
tar -xzf 4ff78ce2_4.0.0.tar.gz      # sha256 实测 = d71f69fd…（与 conandata 一致）
cd ohcount-4.0.0/src/hash && sh ./generate_headers     # GNU gperf 3.1
cd ../parsers && bash ./compile                        # Ragel 6.10，107 个 .rl
cp …/src/hash/language_hash.c …/src/hash/*_hash.h  generated/hash/
cp …/src/parsers/*.h                               generated/parsers/
```
（核对：生成的 7 个 hash 文件与用于先行验证的同版本构建产物逐字节相同。）

## 构建流程（conanfile.py build()）
1. `source()`：官方 tarball strip_root 解压
2. `apply_conandata_patches()`：应用 `patches/` 下 5 个补丁（见下节；由
   `ohc-run.py refresh-patch --auto` 生成并经 dry-run 校验）
3. 将 `generated/hash/*`、`generated/parsers/*` 覆盖进源码树
4. clang 编译 `src/parser.c` → `src/parser.o`
   （`src/hash/parser_hash.h` 统一 `#include` 全部 107 个解析器头，故单文件含全部解析器）
5. clang 链接 `src/ohcount.c` + sourcefile/detector/licenses/loc/log/diff/parsed_language
   + `src/hash/language_hash.c` + `src/parser.o` → `bin/ohcount`
   （-I/-L 取自 pcre、libmagic 依赖的 cpp_info；`-lpcre -lmagic` 静态链接）
6. **上游 C 测试套件实编译 + 实跑**：clang 编译 `test/unit/all_tests.c` + 上述源文件
   → `test/unit/run_tests`，注入 `TMPDIR`（可写构建目录 `tmp-upstream-tests/`）、
   `MAGIC`（libmagic 包内 `share/misc/magic.mgc`）与 PATH（GNU diff，供 >100kB
   的 diff 用例 popen 调用），在 `test/unit/` 下运行；任一断言失败即构建失败。
   成功时输出 `UPSTREAM TEST SUMMARY: total=529 passed=529 failed=0`
7. `package()`：安装 `bin/ohcount` + `licenses/COPYING`；`package_info()` 声明 bindirs

## 补丁清单（patches/，全部 R3：refresh-patch --auto 生成）
1. `0001-src-diff.c.patch`（portability）：`tmp_file_from_buf()` 的临时文件模板由
   硬编码 `/tmp/ohcount_diff_XXXXXXX` 改为 `$TMPDIR`（未设置回退 /tmp），并对
   mkstemp 失败显式报错；POSIX 语义，无 `#ifdef __OHOS__`（R8）
2. `0005-test-unit-sourcefile_test.h.patch`（portability）：`test_tmp_dir` 同步改为
   扫描 `$TMPDIR`（回退 /tmp）
3. `0002-test-unit-parser_test.h.patch`（test）：上游 `all_parser_tests()` 漏挂 5 个
   聚合器（cmake/golang/puppet/qml/typescript）且漏 include `test_cmake.h`；补挂后
   新增 13 个孤儿用例
4. `0004-test-unit-parsers-test_jsp.h.patch`（test）：`all_jsp_tests()` 漏调
   `test_jsp_comment()`；补调后新增 1 个孤儿用例
5. `0003-test-unit-parsers-test_golang.h.patch`（test）：golang 用例使用的语言名
   `"go"` 未注册（实际注册名 `"golang"`，见 `src/hash/language_hash.c`），原用例在
   任何平台都会因解析结果为空而崩溃（上游笔误）；修正后 4 个用例可执行
说明：以上补丁不修改任何断言与期望值；全部修改点均为可移植性（TMPDIR）或上游
测试清单漏挂/笔误。

## 上游测试清点与实跑证据（R51 三步法，2026-09-24 更新）

### 清点（tarball 全量实测）
- C 核心套件（`test/unit/all_tests.c` → `test/unit/run_tests`，上游 build 脚本 `sh build tests`）：
  - 命名用例 280：sourcefile_test.h 10 + detector_test.h 25（函数体内 123 条
    ASSERT_DETECT/ASSERT_NODETECT 数据断言，覆盖 test/detect_files/ 样本）
    + loc_test.h 25 + license_test.h 2（src_vs_expected_tests + very_long_file_test）
    + unit/parsers/*.h 218（96 个头文件中的命名用例）
  - 数据驱动 249 组（按实际执行口径，即循环实际访问且配对成功的样本）：
    test/src_dir ↔ test/expected_dir 154 组（src_dir 158 个样本中 4 个无同名
    expected 文件：classic_basic1.classic_basic、html.cgi、mysql-stale-table-sniper、
    postscript.ps；expected_dir 中有 2 个无同名 src：perl.cgi、postscipt.ps
    （上游拼写错误），不会被循环访问）；
    test/src_licenses ↔ test/expected_licenses 95 组
  - C 套件合计 529 个入口
- Ruby 绑定测试：test/unit/ruby/ 14 个 *_test.rb，85 个 test 方法
- Python 绑定测试：test/unit/python/python_test.py，5 个 test 方法
- 上游 N 合计 = 529 + 85 + 5 = 619

### 实跑（N′，真机实测；build() 集成）
```
$ (conan create 日志；实际命令 ./run_tests，cwd=test/unit，TMPDIR=<构建目录>/tmp-upstream-tests)
Running sourcefile tests
Running detector tests
Running license tests
Running parser tests
Running loc tests
ALL TESTS PASSED.
ohcount/4.0.0: UPSTREAM TEST SUMMARY: total=529 passed=529 failed=0 (bindings skipped: 0/90, swig/ruby headers missing)
```
- C 套件 N′ = 529/529 通过（0 失败、0 跳过），完整日志见
  `reports/w3-local-ci.log`（W3），CI 构建日志同样打印该 SUMMARY 行。
- 绑定 0/90 未执行，具体技术原因：上游 build 脚本 ruby 目标需 `swig`（本环境
  PATH 与 /data/service/hnp/bin 均无 swig）与 ruby 开发头文件（未安装），
  `ruby/ohcount_wrap.c` 无法生成 → ruby 绑定无法构建；python 绑定模块同样依赖
  swig 生成，未构建。属工具链缺失，非代码失败。
- 09-22 版曾申报 N′=0（/tmp 只读导致 run_tests 首个 sourcefile 用例即中止）；
  本版已通过补丁 1/2 修复并用 build() 注入 TMPDIR 实跑，N′ 提升为 529/529。

## 本包验证（W3 本地 conan create，全绿，2026-09-24）
```
$ conan create archives/o/ohcount/4.0.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
      --build=missing -cc core.sources:download_cache=<tarball 校验过的下载缓存>
  # 设备直连 github 超时；通过 core.sources:download_cache 提供
  # sha256=d71f69fd… 的官方 tarball（实测 sha256 一致），仅影响取源
ohcount/4.0.0: Apply patch (portability): ...
ohcount/4.0.0: RUN: /data/service/hnp/bin/clang ... -c src/parser.c -o src/parser.o
ohcount/4.0.0: RUN: /data/service/hnp/bin/clang ... -o bin/ohcount ... -lpcre -lmagic
ohcount/4.0.0: RUN: /data/service/hnp/bin/clang ... test/unit/all_tests.c ... -o test/unit/run_tests ...
ohcount/4.0.0: RUN: ./run_tests
Running sourcefile tests / detector / license / parser / loc
ALL TESTS PASSED.
ohcount/4.0.0: UPSTREAM TEST SUMMARY: total=529 passed=529 failed=0 (bindings skipped: 0/90, swig/ruby headers missing)
ohcount/4.0.0: Package '236e8b71f9bde58890ce8c37df118cf89231857f' built
...
PASS 01: bin/ohcount installed in the package
PASS 02: bin/ohcount parses as an ELF file
PASS 03: ELF64 little-endian
PASS 04: e_machine == EM_AARCH64 (183)
PASS 05: PT_INTERP == OHOS musl loader (ld-musl-aarch64.so.1)
PASS 06: OpenHarmony .codesign section present
PASS 07: no DT_RPATH / DT_RUNPATH leakage
PASS 08: pcre/libmagic statically linked (DT_NEEDED clean)
PASS 09: functional: fixture.c -> c 1/4/5/1/10
PASS 10: functional: fixture.py -> python 1/4/2/1/7
OHOS SPECIFIC TESTS: 10/10 PASSED
```
- 完整日志：`reports/w3-local-ci.log`（设备 `~/tmp/ohcount-w3-upstream.log` 副本）
- 包内 bin/ohcount 1,251,776 B，`bin/ohcount <fixture.c>` 输出与参考二进制逐字段一致

## 已知限制
- Ruby/Python 绑定测试（90 例）未执行：缺 swig 与 ruby 开发头文件（见上节逐项原因）
- 上游 C 套件中 14 个孤儿用例（cmake/golang/puppet/qml/typescript/jsp）原未被
  上游 `all_parser_tests()` 挂载；本包已用补丁补挂并跑通，全部计入 529
- 上游 test/unit 的 4 个 src_dir 样本无对应 expected 文件、2 个 expected 文件名
  拼写错误（postscipt.ps），属上游测试数据问题，不影响 529 口径（这些样本本就不
  会被上游循环执行）
