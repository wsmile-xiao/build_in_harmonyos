# rizin 0.9.1 适配 notes

## 2026-08-11 真机预检失败修复（evidence / archive 代码树为空）

- **失败域**: evidence — hmbs 报「无法读取当前 archive 代码树，不能启动真机预检」。
  根因是工作树为空：本地 `.git` 是只有双 remote（origin/upstream）的空仓库，从未成功
  clone/fetch，任务树里没有任何 archives/ 内容，预检无从同步。
- **恢复**: fetch origin + upstream 后检出 `upstream/feat/rizin-0.9.1`（含本任务前 3 个
  提交：适配、conandata 官方直链、test_package 签名严格运行）到本地
  `feat/rizin-0.9.1` 分支；`.hmbs/` 已加入 `.git/info/exclude`（本地生效，不进版本库）。
- **门禁缺口（预判）**: 恢复后的配方两个 conanfile 均无 HMBS 硬门禁 JSON 标记，
  复跑必然「缺少 HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT」incomplete。
  本轮补上，参照仓库内 glib 2.84.0.1（meson test 于 build() 内真机执行）+ aiohttp
  （标记在真机命令结束后打印、数字解析自框架输出）两个先例。
- **修改**（仅工作树，未 commit/push）:
  1. `conanfile.py` `build()` 末尾接入上游测试：`meson test -v -C {build_folder}
     --timeout-multiplier=16 --no-rebuild --print-errorlogs > meson_test.log 2>&1`
     （真机 OHOS aarch64 上 lld 链接即写 .codesign，测试二进制可直接执行，install 前
     无需重签，与 glib 同款）。运行后解析 meson summary（Ok/Expected Fail/Fail/
     Unexpected Pass/Skipped/Timeout/Not run）得真实计数，`print` 合法 JSON
     `HMBS_UPSTREAM_TEST_RESULT`（status/framework=meson/command/discovered/
     executed/passed/failed/skipped...）；`command` 为真机实际执行的完整命令，
     ignore_errors=True 保证测试失败时也能如实出标记（status=failed）。
  2. `test_package/conanfile.py` `test()` 末尾：严格运行 test_rizin（非 0 即抛异常）
     通过后 `print` `HMBS_TEST_PACKAGE_RESULT`（executed/passed=true、
     discovered=1、passedCount=1、command=实际命令）。
  3. `test_package/MANIFEST.yml`: `upstream_test_in_build` 改 true，
     `upstream_test_command` 同步为真实命令。
- **预期真机结果**: `HMBS_UPSTREAM_TEST_RESULT` = {status:passed, framework:meson,
  discovered:137, executed:137, passed:137, failed:0, skipped:0}（unit 137 目标，
  具体以真机 meson summary 实测为准；若个别用例在 OHOS 失败/跳过，门禁会如实拦截，
  下轮按日志最小适配）；`HMBS_TEST_PACKAGE_RESULT` = {executed:true, passed:true,
  discovered:1, passedCount:1}。未删断言、未静默跳过、未伪造数字。

## 2026-08-11 真机预检失败修复（round 2：zstd CLI qsort_r 链接失败）

- **失败阶段**: compile。真机日志两个信号：
  1. `preflight.sh[229]: can't create temporary file /tmp/shhrwwnm.tmp: Read-only file
     system`（HMBS 平台诊断 [readonly_tmp]）——出现在日志最前、conan create 继续执行，
     属于 hmbs 自身预检脚本的非致命提示；我方配方/test_package 全部写入 build_folder /
     generators_folder，未硬编码 /tmp，无需改动。
  2. **真实失败（conan create 退出码 1）**: zstd/1.5.7 构建时 `programs/zstd` CLI 链接失败：
     `ld.lld: error: undefined symbol: qsort_r`（lib/dictBuilder/cover.c 的 COVER_ctx_init
     引用）。OHOS libc 无 glibc 签名 qsort_r。zstd 库目标 libzstd_static 真机已构建成功
     （76% "Built target libzstd_static"），只有 CLI 程序链接不过。
- **修复**: conanfile.py 新增 `configure()`，对 zstd 依赖设 `build_programs = False`。
  rizin 只经 pkg-config 使用 libzstd 库，不需要 zstd 命令行程序；conancenter zstd 配方自
  2023-10（#18826）起提供 build_programs 选项，1.5.7（2024 底发布）必然包含。关闭后仅构建
  libzstd_static，规避 qsort_r 链接失败。
- **预期真机结果**: zstd 依赖正常构建 → 继续 rizin 本体编译（4 个补丁 + 既有 configure
  注入不变）→ meson test 上游测试（137 unit 目标，以实测为准）→ test_package 签名严格运行。
- 仅工作树修改，未 commit/push。

## 2026-08-11 真机预检失败修复（round 3：openssl 3.5.6 不支持 OHOS/armv8/clang）

- **失败阶段**: compile。conancenter 的 openssl/3.5.6 配方在 build() 阶段直接抛
  `Invalid configuration: Unsupported configuration (OHOS/armv8/clang)`，conan create
  退出码 6。openssl 是本配方 requirements() 里显式依赖且 `use_sys_openssl=enabled`。
- **上游证据（v0.9.1 源码核对，非猜测）**:
  1. `meson_options.txt`: `option('use_sys_openssl', type: 'feature', value: 'disabled')`
     —— 上游默认就是禁用，openssl 完全可选。
  2. 所有 openssl 引用均有守卫：`librz/include/rz_util.h` 的 `#include <openssl/bn.h>`
     在 `#if HAVE_LIB_SSL` 内；`rz_socket.h` 的 ssl/err.h 同理；`hash.c` 的
     opensslv.h/provider.h 同理；`librz/hash/p/algo_*.c` 均为 `#if HAVE_LIB_SSL`
     + `#else` 纯 C 实现双分支。
  3. meson 层纯 C 回退完整：`librz/util/meson.build` 无 openssl 时编 `big.c`（替代
     big-ssl.c）；`librz/hash/meson.build` 无 openssl 时补编内置 `algorithms/md4/md5/
     sha1/sha2/sm3`；`librz/socket/meson.build` 仅在 found 时加依赖。
  4. vendored subprojects（capstone-next/pcre2-10.47 等）无 openssl，禁用不会误触
     wrap 下载；test/unit（133 个 .c）与 test/integration 均无 SSL/TLS 引用，
     禁用 openssl 不影响上游测试数量与执行。
- **修复**（仅工作树，未 commit/push）:
  1. `conanfile.py`: requirements() 删除 `openssl/3.5.6`；generate() 改
     `use_sys_openssl = "disabled"`；删除 generate()/build() 中为 openssl 注入
     `-I<include>` 到 native.ini c_args/cpp_args 的死代码（含 `_openssl_inc` 暂存）；
     头部注释更新（openssl 禁用原因 + 纯 C 回退说明）。
  2. `test_package/conanfile.py`: 删除 `requires("openssl/3.5.6")` 及其注释。
  3. `test_package/CMakeLists.txt`: 删除 openssl include 目录注入块，注释同步
     （rz_util.h 不再传递包含 openssl/bn.h，因 HAVE_LIB_SSL=0）。
  4. `manifest.yaml`: `use_sys_openssl=enabled` → `disabled`；dependencies 移除
     `openssl/3.5.6`。
- **预期真机结果**: openssl 不再进入依赖图 → zstd 等既有依赖正常构建 → rizin 本体以
  无 openssl 配置编译（HAVE_LIB_SSL=0，big.c + 内置哈希）→ meson test 上游测试
  （137 unit 目标，以实测为准）→ test_package 签名严格运行。未删断言、未静默跳过。
- 仅工作树修改，未 commit/push。

## 2026-08-11 真机预检失败修复（round 4：上游测试 18 失败 = 缺 test/bins + pcre2 无 JIT）

- **失败阶段**: upstream_test。真机 meson test：discovered=153, executed=153,
  passed=135, failed=18, skipped=0。失败名单：17 个 integration（analysis_graph、
  analysis_il、autocmplt、basefind、bin、bin_symbols、bin_vfiles、
  cpu_platform_profiles、dwarf、dwarf_info、dwarf_integration、glibc_version、
  open_analyse_save_load_project、pdb、project_migrate、stabs、str_search）
  + 1 个 unit（str_search）。仅 analysis_fcn / analysis_global_var / rzpipe 通过。
  另：test_package 阶段 test_rizin 打印 342 次 `Regex compilation for '\s+' failed
  at 0: bad JIT option`（非致命噪音，exit 0）。
- **根因 1（17 个 integration）**: 官方 release 源码包 rizin-src-v0.9.1.tar.xz
  **不含 test/bins**。上游 test/README.md 明确 "bins/: Sample binaries (fetched
  from the external repository rizinorg/rizin-testbins)"，上游 CI 即
  `git clone https://github.com/rizinorg/rizin-testbins test/bins`（v0.9.1
  workflows/ci.yml 实证）。失败用例全部以 test/ 为 workdir 打开 "bins/..." 文件
  （bins/elf/ls、bins/firmware/stm32f103-dapboot-v1.20-bluepill.bin、
  bins/pdb/*.pdb、bins/elf/libc-2.3*.so 等），缺数据即 fopen 失败 → 用例失败；
  通过的 3 个 integration 均不引用 bins。
- **根因 2（unit str_search）**: conancenter pcre2 配方默认 `support_jit=False`
  （PCRE2_SUPPORT_JIT=OFF），而 rizin meson.build 按平台启发式无条件
  `-DSUPPORTS_PCRE2_JIT`（cpu in [aarch64,...] && cc!=tcc && system not in
  [darwin,serenity]）。无 JIT 库的 pcre2_jit_compile 返回 -45 "bad JIT option"；
  更关键的是 rz_regex_new_multi 内 `pcre2_jit_stack_create` 失败 → 返回 NULL →
  librz/search/string_search.c 的 `rz_search_collection_string_add`（经
  setup_str_regex → rz_regex_new_multi）返回 false → unit test_str_search 的
  `test_rz_scan_strings_scan_options_error` 中 6 个 "Should succeed" 断言失败。
- **修复**（仅工作树，未 commit/push）:
  1. `conanfile.py::configure()`: `self.options["pcre2"].support_jit = True` ——
     构建带 JIT 的 pcre2，消除 "bad JIT option" 噪音并恢复 rz_regex_new_multi
     （字符串搜索集合 add 成功），修复 unit str_search。
  2. `conandata.yml`: 新增 `test_bins` 源 —— rizinorg/rizin-testbins 固定提交
     85a4965（2026-07-09）codeload 归档，sha256=
     64266f1981a578dee2320c07695bbfd732d1d94fa194adda3891200a5aaf8852
     （本地下载实测，非编造）。
  3. `conanfile.py::source()`: 把 test_bins 归档 strip_root 解到
     `{source_folder}/test/bins`（仓库根即 bins 内容：elf/ firmware/ pe/ pdb/
     arm/ dwarf/ ...），与上游 CI `git clone rizin-testbins test/bins` 同构。
  4. `conanfile.py::build()`: meson test 回显增强 —— 除 summary 尾部外，逐条
     回显失败用例的输出块（--print-errorlogs 明细），后续轮次可直接看到断言级
     失败信息。
  5. `manifest.yaml` / `test_package/MANIFEST.yml`: 同步 knowledge 与测试数据说明。
- **预期真机结果**: pcre2 带 JIT 构建；test/bins 数据就位 → 17 个 integration
  恢复执行（个别样本若在 OHOS 解析差异可能仍失败，以实测为准）+ unit str_search
  通过 → 目标 discovered=153, executed=153, passed=153。未删断言、未静默跳过、
  未伪造数字；18 个失败用例全部真实复跑（数据来自与上游 CI 同源的 testbins 固定
  提交）。

## 真机预检修复（2026-08-11 第3轮）：source() BadZipFile
- **现象**: conan create 在 source() 阶段失败（compile 阶段），`get()` 下载
  test_bins 归档后解压报 `BadZipFile: File is not a zip file`。
- **根因**: codeload URL 形如 `.../tar.gz/<commit-hash>`，basename 是 commit
  hash（无扩展名）。Conan `get()` 未传 filename 时按 URL basename 存盘，
  `unzip()` 因文件名不以 .tar.gz/.tar/.gz 结尾而落入 zipfile 分支 →
  BadZipFile。归档本身正确：本地实测 227.4MB，gzip 魔数 1f 8b，sha256
  64266f1981a578dee2320c07695bbfd732d1d94fa194adda3891200a5aaf8852 与
  conandata.yml 完全一致。
- **修复**（仅工作树，未 commit/push）: `conanfile.py::source()` 给 test_bins
  的 `get()` 显式传 `filename="rizin-testbins.tar.gz"`，unzip 走 tar 分支，
  sha256 校验与 strip_root 不变。python ast 语法检查通过。
- **预期真机结果**: test/bins 正常解出 → 17 个 integration 恢复执行 + unit
  全量，目标 discovered=153, executed=153, passed=153。

## 2026-08-11 真机预检失败修复（round 6：上游测试 5 失败 = pcre2 JIT 不可用 + 测试数据供给）

- **失败阶段**: upstream_test。真机 meson test：discovered=153, executed=153,
  passed=148, failed=5, skipped=0。失败名单：unit str_search、integration
  str_search、autocmplt、dwarf_integration、analysis_graph。str_search 直接报
  `Regex compilation for '...' failed at 0: bad JIT option` + regex.c:299
  rz_regex_new_multi "code should not be reached"；其余用例 stderr 也满是
  `\s+` 的 bad JIT option 噪音（reg profile 解析走 rz_str_split_duplist_n_regex）。
- **根因（pcre2 JIT 不可用，真机日志 + 源码双重实证）**:
  1. pcre2 源码（vendored 10.47 同款逻辑）：`pcre2_jit_compile` 在库未编译
     SUPPORT_JIT 时返回 PCRE2_ERROR_JIT_BADOPTION（pcre2_jit_compile.c 末尾
     `#ifndef SUPPORT_JIT return PCRE2_ERROR_JIT_BADOPTION`），
     `pcre2_jit_stack_create` 同样返回 NULL。
  2. rizin meson.build 按平台启发式无条件定义 SUPPORTS_PCRE2_JIT（aarch64 +
     clang + 非 darwin/serenity，meson.build:265）。定义后 rz_regex_new_multi
     （regex.c:283-302）因 jit_stack 创建失败返回 NULL → librz/search/
     string_search.c 的 collection add 失败 → unit str_search 6 个
     "Should succeed" 断言失败、integration str_search "Failed to add job"、
     analysis_graph 的 "str.d" 检测为 "data.08048dee"（字符串搜索整体失效）。
  3. 为什么 configure() 里 pcre2.support_jit=True 无效：真机 conan 日志显示
     file/5.48、pcre2/10.45.1、zlib/1.3.1.1 三个包 ID 同为
     6b129b068851896169fae42d399fa922d239ce8a —— 本环境包 ID 按 settings-only
     计算，选项不参与，ohpcd 预构建二进制（无 JIT）恒被选中，改选项永不触发
     重建。故 support_jit 路线彻底放弃。
- **修复**（仅工作树，未 commit/push）:
  1. 新补丁 `patches/0005-meson.build.patch`：把 'harmonyos' 加入
     pcre2_jit_supported 排除列表（与 darwin/serenity 同款）。SUPPORTS_PCRE2_JIT
     不再定义 → rz_regex_new_multi 跳过 jit_stack 分支直接返回有效 regex，
     全量 regex 走 pcre2 解释器，上游测试语义不变；`\s+` 噪音消失。regex.c 所有
     JIT 调用点均有 #ifdef 守卫（regex_new/regex_free_multi/rz_regex_new_bytes），
     test/ 无 SUPPORTS_PCRE2_JIT 引用，排除安全。补丁经 `patch -p1 --dry-run`
     在 pristine 源码验证可干净应用（conan 用 patch 工具，非 git apply）。
  2. `conanfile.py`：删除 configure() 中无效的 pcre2.support_jit=True（含注释），
     头部注释更新为 JIT 排除法 + 上游 CI 数据供给说明。
  3. `conanfile.py::build()`：镜像上游 ci.yml 的 "Install with meson" 步骤 ——
     上游先 meson install（--prefix=$HOME）再跑 meson test，主题/types sdb 经
     RZ_PREFIX 可达；本配方编译期 prefix=/（conan DESTDIR 打包），故把 meson
     install 产物 stage 到 {build_folder}/rzstage，并建符号链接
     {stage}/.local/share/rizin → {stage}/share/rizin，测试命令以 HOME={stage}
     运行 → rz_path_home_prefix 命中主题（librz/cons/d/* 经 install_subdir 安装），
     补齐 autocmplt eco 主题补全（首个 ayu）。不改变打包布局。
  4. `conandata.yml` / `manifest.yaml`：登记 0005 补丁、更新 knowledge_gained、
     patches_count=5、patch_classification 追加。
- **预期真机结果**: unit str_search + integration str_search 确定性修复（解释器
  语义一致）；analysis_graph 的 str.d 字符串检测恢复；autocmplt 主题补全有数据；
  dwarf_integration 的 unaligned 若仍缺（疑似 testbins vista-glass.exe 版本差异，
  待真机确认）下轮再处理。目标 discovered=153, executed=153, passed=153。
  未删断言、未静默跳过、未伪造数字。

## 2026-08-11 真机预检失败修复（round 7：0005 补丁 hunk 头行数声明错误）

- **失败阶段**: compile。conan create 在 build() 的 apply_conandata_patches 处失败：
  `WARN .../0005-meson.build.patch: error: patch stream is incomplete!` →
  `ConanException: Failed to parse patch`。0001-0004 全部正常应用（日志实证），
  仅 0005 解析失败。
- **根因（本地对官方源码包 rizin-src-v0.9.1.tar.xz 逐条验证，非猜测）**:
  0005 的 hunk 头写的是 `@@ -263,7 +263,7 @@`，但 hunk 体实际只有 6 行旧/6 行新
  （3 行上下文 + 1 删 1 增 + 3 行上下文 = 旧侧 5 上下文 + 1 删 = 6 行，新侧同理）。
  行数与声明不符（多声明 1 行）：GNU patch 宽容模式下能跳过（本地 dry-run 通过），
  但真机 Conan 的补丁解析器按声明行数读取到 EOF 发现不足 → "patch stream is
  incomplete!"。真机与本地同一现象：严格解析（git apply）报 `corrupt patch at
  line 11`（第 11 行不存在），宽松 GNU patch 报错位置不同但 root cause 相同。
- **修复**（仅工作树，未 commit/push）: `patches/0005-meson.build.patch` hunk 头
  `-263,7 +263,7` → `-263,6 +263,6`，上下文内容不变。
- **验证**: 官方源码包解包 pristine 树 + 5 个补丁按序应用全部成功（GNU patch，
  与真机同款行为）；修正后 0005 严格 git apply --check PASS、GNU patch dry-run
  PASS；最终 meson.build 263-268 区域含 `'harmonyos'` 排除项
  （`not in ['darwin', 'serenity', 'harmonyos']`），thread.c 的
  HAVE_PTHREAD_SETCANCELSTATE 守卫也确认就位。未删断言、未静默跳过。
- **预期真机结果**: 补丁解析通过 → 恢复上轮目标 discovered=153, executed=153,
  passed=153（以实测为准）。

## 2026-08-11 真机预检失败修复（round 8：meson test 崩溃 ModuleNotFoundError）

- **失败阶段**: upstream_test。真机 meson test：discovered=0, executed=0, passed=0。
  meson_test.log 尾部即崩溃现场：`Traceback ... File ".../.local/bin/meson", line 3,
  from mesonbuild.mesonmain import main` → `ModuleNotFoundError: No module named
  'mesonbuild'`。
- **根因**: 真机 meson 是 pip --user 安装（/storage/Users/currentUser/.local/bin/meson），
  其 Python 模块 mesonbuild 位于 ~/.local/lib/python*/site-packages。上一轮为让测试
  二进制经 rz_path_home_prefix($HOME/.local/share/rizin) 命中 stage 主题数据，给
  meson test 命令加了 `HOME={rzstage}` 前缀——覆盖 HOME 后，Python 解释器按新 HOME
  解析用户 site-packages 到 rzstage/.local/lib/python*/...（不存在）→ 加载 meson
  自身失败 → meson test 一启动就崩，未发现任何测试。meson configure/build/install
  未覆盖 HOME 故正常，唯独这条命令加了前缀（round 6 引入，round 7 卡在补丁解析未
  暴露，本轮首次执行即触发）。
- **修复**（仅工作树，未 commit/push）: `conanfile.py::build()` meson test 命令
  改为双环境变量注入：先用 `shutil.which("meson")` 定位 meson 可执行文件，由其
  位置推导用户 site-packages（bin/ 上一级 lib/python*），拼成
  `PYTHONPATH="{site}:$PYTHONPATH" HOME="{stage}" meson test ...`。meson 自身经
  PYTHONPATH 仍能加载 mesonbuild；测试二进制照常继承 HOME={stage} 命中 stage 数据。
  两者互不干扰。新增 import shutil。python ast 语法检查通过。
- **预期真机结果**: meson test 正常启动并真实执行 test/unit + test/integration，
  目标 discovered=153, executed=153, passed=153（以实测为准；若个别用例在 OHOS
  仍失败/跳过，门禁如实拦截，下轮按日志最小适配）。未删断言、未静默跳过、未伪造
  数字。

## 2026-08-11 真机预检修复（round 9：types sdb 数据经 rz_path_system 不可达）

- **失败阶段**: evidence。预检（31476）ri zin 包命中缓存（"Already installed! (1 of 1)"）未重构建，
  无 HMBS_UPSTREAM_TEST_RESULT 标记；上一轮完整构建（31399）标记为 discovered=153, executed=153,
  passed=151, failed=2，遗留 2 个失败测试目标：
  1. `dwarf_integration` — test_parse_dwarf_types line 110 "unaligned exists: expected to not be NULL
     but it was."（union "unaligned" 未创建），伴随 "Failed to insert RzType [0x3e88] into
     type_by_offset" 与 "struct member missing type"。
  2. `analysis_graph` — 4 个子测试失败：more line 136 graph json（期望 node 5 title "str.d" 实际
     "data.08048dee"）、cfg/entrypoints/serialize load file 失败（疑似前面失败泄漏 RzCore 致 fd 耗尽级联）。
- **根因（本地源码逐条核对，非猜测）**:
  - 测试二进制经 `rz_path_system(RZ_SDB_TYPES)` 解析 types sdb 数据目录。本配方 meson 编译期
    `--prefix=/`，编译进二进制的 RZ_PREFIX="/"，`rz_path_system` 返回 `/share/rizin/types` ——
    设备上不存在！上游 CI（ci.yml）用 `meson setup --prefix=${HOME}` + `ninja install`，所以
    RZ_PREFIX=$HOME，`rz_path_system` 返回 `$HOME/share/rizin/types`，存在。
  - 我们 stage meson install 到 rzstage 并设 HOME={stage}（`.local/share/rizin` 符号链接供给
    autocmplt 主题），但 `rz_path_system` 用的是编译期 RZ_PREFIX 而非 HOME，types 数据不可达。
  - dwarf_integration：test_parse_dwarf_types 用 `rz_type_db_init(typedb, types_dir, "x86", 32,
    "linux")`，types_dir 无效 → typedb 无基础类型 → DWARF struct member 类型解析失败 →
    union "unaligned" 未创建 → line 110 失败。
  - analysis_graph：`analysis_tp.c:468-471` 的 format 参数检测（printf 格式串临时 minlen=1，
    创建 "str.d" flag）依赖 typedb 有 printf 签名（参数名 "format"），typedb 空 → 不触发 →
    "%d"（2 字符 < minlen 4）不被字符串扫描检测 → node 5 title 变 data.08048dee → graph json 失败。
- **修复**（仅工作树，未 commit/push）:
  1. 新补丁 `patches/0006-rz-path-prefix-env.patch`：`librz/util/path.c` 的 `rz_path_prefix` 优先读
     `RZ_PREFIX` 环境变量（静态缓存一次），未设置时回退编译期 RZ_PREFIX —— 与
     `rz_core_config_init` 中 dir.prefix 的 RZ_PREFIX env 处理一致，测试语义不变。
  2. `conanfile.py::build()` meson test 命令注入 `RZ_PREFIX="{stage_dir}"`（与既有
     HOME/PYTHONPATH 前缀并列）→ `rz_path_system(RZ_SDB_TYPES)` 落到
     `{stage}/share/rizin/types`（stage 已含 meson install 全部 share 数据）。
  3. `conandata.yml` 登记 0006；`manifest.yaml` 同步 patches_applied / knowledge_gained /
     patches_count=6 / patch_classification。
- **验证**: pristine 官方源码包（rizin-src-v0.9.1.tar.xz）上 0001-0006 按序 `patch -p1 --dry-run`
  全部 PASS；conanfile.py / test_package/conanfile.py python ast 语法检查通过。
- **预期真机结果**: types sdb 数据可达 → dwarf_integration union "unaligned" 创建成功、
  analysis_graph str.d flag 创建成功、graph json 通过且不再泄漏 core（load file 级联恢复），
  目标 discovered=153, executed=153, passed=153（以实测为准）。未删断言、未静默跳过、未伪造数字。

## 2026-08-11 真机预检修复（round 10：0006 补丁覆盖 rz_path_prefix 破坏上游 unit test_path_prefix）

- **失败阶段**: upstream_test。真机 meson test：discovered=153, executed=153, passed=152,
  failed=1, skipped=0。唯一失败目标 `130/153 unit - rizin:util`：
  `test_path_prefix ERR — [XX] Fail at line 73: not equal: expected 0, got 115.`
  （expected 0, got 115：115 即 's'，RZ_PREFIX 环境变量值 "/storage/..." 与编译期宏 "/" 在
  索引 1 处首个字节差 s(115) vs \0(0)）。
- **根因（真机日志 + 源码双重实证）**: round 9 的 0006 补丁把 RZ_PREFIX 环境变量覆盖加在
  `rz_path_prefix()` 上；而 test/unit/test_util.c test_path_prefix 明确断言
  `strcmp(rz_path_prefix(sys_path), RZ_PREFIX) == 0`（编译期宏）。测试命令注入
  RZ_PREFIX={rzstage} 后 rz_path_prefix 返回 stage 路径 ≠ 编译期 "/"，断言必挂。
- **修复**（仅工作树，未 commit/push）:
  1. `patches/0006-rz-path-prefix-env.patch` 重生成：RZ_PREFIX 环境变量覆盖从
     `rz_path_prefix()` 移到 `rz_path_system()`（rz_path_prefix 恢复原样返回编译期 RZ_PREFIX）。
     测试/运行时代码取系统数据目录全部经 rz_path_system（librz 内 RZ_SDB_TYPES/RZ_SDB_FORMAT/
     RZ_SDB_MAGIC/RZ_SIGDB/RZ_THEMES 等均为 rz_path_system 解析，dwarf_integration 的
     test_parse_dwarf_types 也是 rz_path_system(core->sys_path, RZ_SDB_TYPES)），
     types sdb 数据仍可达；test/ 目录里唯一断言 rz_path_prefix 的只有 test_path_prefix。
  2. `conandata.yml` / `manifest.yaml` 同步 0006 patch_description / knowledge_gained
     （覆盖位置改为 rz_path_system + 为什么不能放 rz_path_prefix）。
  3. conanfile.py 无需改动：build() 注入的 RZ_PREFIX={rzstage} 前缀保留，现由 rz_path_system 消费。
- **验证**: pristine 源码包上 0001-0006 按序 patch -p1 --dry-run 全部 APPLY-OK；实际应用后
  path.c 终态确认 rz_path_prefix 原样返回 RZ_PREFIX、rz_path_system 先取 rz_path_prefix 再
  按需覆盖为 RZ_PREFIX env。未删断言、未静默跳过、未伪造数字。
- **预期真机结果**: test_path_prefix 恢复（line 73 断言过）且 dwarf_integration /
  analysis_graph 的 types 数据仍可达，目标 discovered=153, executed=153, passed=153
  （以实测为准）。

- **CI #20517 源码下载超时修复**（仅工作树，未 commit/push）:
  - 现象: conan source() 下载 github.com 直链 rizin-src-v0.9.1.tar.xz 连接超时；
    worker 预下载阶段 `curl` 不存在（[Errno 2]），镜像 fallback 重写对已是列表的 url 不生效。
  - 修复: conandata.yml `sources.url` 与 `test_bins.url` 改为有序列表，
    前置 `https://gh-proxy.com/<原URL>`（build_and_test.sh 维护的 GitHub 镜像映射，
    实测 2026-08-06 可用），官方直链保留末尾回退；sha256 均未变。
  - 预期: conan get() 逐个尝试 URL，gh-proxy.com 可达则下载成功，官方 URL 兜底。
