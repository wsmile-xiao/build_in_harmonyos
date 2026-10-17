# libecoli 0.11.7 适配笔记

## 编译环境

- 构建系统: meson
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (HarmonyOS PC 真机 clang 15，由 hmbs 预检提供)
- 状态: built（首轮工作树，真机预检待 hmbs 后台执行）
- 申请人: waylong，队伍: 龙骑士

## 上游信息

- 上游仓库: https://github.com/rjarry/libecoli
- 上游版本: 0.11.7（Git tag v0.11.7，meson.build 中 project version 0.11.7）
- 源码包: https://github.com/rjarry/libecoli/archive/refs/tags/v0.11.7.tar.gz
- sha256: 5facc940909359b832f22902aca991787a083d0721469dbc16a1318e0bdba612
- 许可证: BSD-3-Clause
- 构建系统: meson（C99，warning_level=2，werror=true）
- 可选特性: yaml（libyaml）、editline（libedit）、doc（doxygen）、examples、tests

## 编译步骤

1. 下载并解压上游 tag 包。
2. meson 配置（OHOS）：
   `meson setup build -Ddefault_library=static -Dyaml=disabled -Deditline=disabled -Ddoc=disabled -Dexamples=disabled -Dtests=enabled -Dwerror=false`
3. 编译：`meson compile -C build`
4. 上游测试：`meson test -v --print-errorlogs --no-rebuild -C build`（32 个 unit 套件二进制）
5. 安装：`meson install -C build`（产出 libecoli 静态库、头文件、libecoli.pc）
6. test_package：以消费者视角编译运行 test_package.c（8 项断言），meson 方式查找已安装的 ecoli 库。

配方把上述步骤固化在 conanfile.py（MesonToolchain + Meson helper），与仓库内 libseat 0.9.1 的 meson 写法对齐（含 OHOS 下 werror=false 与 archiver 注入）。

## 上游测试清点（来源：test/meson.build）

共 32 个必跑测试（suite unit，测试名 = 文件 stem + `_test`）：
complete、config、dict、htable、log、node、node_any、node_bypass、node_cmd、
node_cond、node_dynamic、node_dynlist、node_empty、node_expr、node_file、
node_int、node_many、node_none、node_once、node_option、node_or、node_re、
node_re_lex、node_seq、node_sh_lex、node_space、node_str、node_subset、
parse、string、strvec、vec。
另有 1 个条件测试 yaml，仅当 yaml 特性启用时才构建；本配方显式禁用 yaml，
故不构建、不执行。测试均为自包含 C 可执行文件（EC_TEST_MAIN），无需 gtest/cmocka。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 werror=true，在 OHOS SDK 头文件警告下可能误伤构建 | 上游对 GCC/Clang 开 -Werror，OHOS SDK 头文件警告不可控 | 仅 OHOS 时传 -Dwerror=false（参照 libseat 0.9.1 同类处理） |
| 2 | 可选依赖导致测试集不确定（yaml 启用时多 1 个测试） | yaml/editline 为 feature auto，随环境变化 | 路径 A 显式全部禁用，保证 32 个测试集固定、零依赖 |
| 4 | OHOS musl libc 缺 qsort_r，链接 libecoli.so 失败 undefined symbol: qsort_r（真机预检 compile 阶段，strvec.c ec_strvec_sort 引用） | 上游 src/strvec.c 用 GNU 扩展 qsort_r 传 comparator 上下文；OHOS musl 未提供该符号（与 glibc 不同） | 新增 patches/0001-ohos-portable.patch：ec_strvec_sort 改为可移植插入排序（直接调 str_cmp，无全局量、线程安全），删 GNU cmp_vec_elt/qsort_r 调用 |
| 5 | 上游顶层 meson.build 硬编码 shared_library，无视 -Ddefault_library=static（OHOS 要求静态） | shared_library 不响应 default_library，OHOS 仍产出 .so | 同一补丁把 shared_library 改为 library()，默认行为不变，OHOS 静态生效 |
| 3 | OHOS profile 只声明 clang，meson 原生文件缺 ar/ranlib | MesonToolchain 生成的 native file 无归档工具 | 复用 libseat 的 _inject_ohos_archiver 逻辑补 ar/ranlib |
| 6 | 真机 32 项上游测试大面积失败：`type=empty/none/any/space does not exist`、`cannot create node`（node.c:57/62、complete.c、parse.c 等 dump/parse 断言连带失败） | 补丁把顶层 `shared_library` 改为 `library()` 后 OHOS 下产出静态归档，而 test/meson.build 用 `link_with` 只拉取被引用目标文件；按名称查找的节点类型（empty/none/any/space 等）目标文件无人引用，构造器不执行、类型未注册 | 同一补丁追加 test/meson.build：`link_with: libecoli` 改为 `link_whole: libecoli`，测试二进制拉取归档全部目标文件（与上游 subproject 下 static_library + link_whole 做法一致；shared 构建下语义不变） |
| 7 | 同上：静态链接时测试 `__init` 构造器先于库构造器执行，`ec_init()` 在 init_list 为空时空转，node_cmd/node_cond 预构建解析器与 htable 初始化回调永不执行 | 可执行文件目标文件排在归档成员之前，.init_array 按链接顺序执行；shared 库则先加载库构造器故无此问题 | 同一补丁调整 test/test.h 的 EC_TEST_MAIN：构造器只保留 `ec_htable_force_seed(42)`，`ec_init()` 推迟到 `main()` 首行（此时全部构造器已执行）；失败返回 1，不改变任何断言与用例数 |
| 8 | 真机诊断 `[readonly_tmp]`：`/tmp` 只读，`preflight.sh` mktemp 与测试临时文件可能受影响 | 真机 /tmp 只读挂载；hmbs 注入按任务隔离的可写 TMPDIR | conanfile.py build() 新增 `_ensure_writable_tmp()`：优先复用可写的 TMPDIR/TMP/TEMP，否则回退到 build 文件夹下 `hmbs-tmp`；仅重定向临时根目录，不跳过、不删除任何测试（yaml.c 硬编码 /tmp 的测试因 yaml=disabled 未构建） |
| 9 | 第二轮预检（上一轮补丁已生效：按名查找的类型缺失消失，仅剩预期的 `type=deznuindez does not exist` 否定断言）仍失败：complete.c:52/63/64、node.c:57/62、parse.c:37/78、strvec.c:142/164 的 `strstr(buf, ...)` 全灭，dict/htable 从 SIGTRAP 变为 SIGSEGV | 100% 相关性：所有失败断言都读取 `open_memstream` 的 `buf`，而同一测试中不经过内存流的断言（节点计数、补全计数/条目、解析匹配标志）全部通过；dict/htable 也在 open_memstream+dump 序列后崩溃。open_memstream 在此 OHOS libc 环境不可用（dump 内容回空、堆破坏导致崩溃，且与静态/动态链接方式无关，属不同失败域） | 与上一轮不同策略：不再动链接/初始化，新增 test/test.h 可移植 helper `ec_test_memstream_open/close`（TMPDIR/TMP/TEMP 下 mkstemp 无名临时文件 + 读回，fclose 语义由 close helper 承担），6 个测试文件 11 处调用点机械替换；fail 路径保留 plain fclose；断言一字未改 |
| 10 | 补丁文件经 difflib 追加时因行尾处理丢失换行导致 hunk 体粘连（本地验出，非真机问题） | 生成脚本混用 lineterm/尾空行，`"".join(d)` 产出单行巨块 | 重写生成器：全程显式行表 + `chr(10)` 连接，round-1 与新增 test.h 改动合并为单一连贯 diff；本地逐文件模拟 `patch` 应用全绿后才结束本轮 |

## 源码修改

补丁 patches/0001-ohos-portable.patch（含 4 个 hunk）：src/strvec.c 可移植插入排序替代 qsort_r；meson.build `shared_library` 改 `library()`（OHOS 下静态生效）；test/meson.build 测试改 `link_whole` 拉取归档全部目标文件；test/test.h 新增 TMPDIR 临时文件的内存流替代 helper，6 个测试文件 11 处 `open_memstream` 调用点替换（断言不变）；test/test.h EC_TEST_MAIN 把 `ec_init()` 推迟到 `main()` 首行。未引入 `__OHOS__` 平台宏，未删除/跳过任何断言。

## 依赖版本

无外部依赖（libyaml/libedit 均未启用，doc/examples 已禁用）。

## 验证结果

- 本轮为未提交工作树，按任务要求不提前写真机结论。
- 待 hmbs 后台真机预检：conan create（含 32 项上游 meson test + test_package 8 项断言）。
- 预检通过前不 commit、不 push、不创建 PR。

```bash
# 后台预检成功后，回填以下两行标记数字到 PR 正文：
# HMBS_TEST_PACKAGE_RESULT（discovered/passedCount = test_package 真实计数）
# HMBS_UPSTREAM_TEST_RESULT（discovered = 32，executed/passed/skipped 据实回填）
```

## 注意事项

- 本机为 Windows，大仓含大小写冲突路径（如 archives/l/libXext 与 libxext、gama 补丁 `??` 文件），本地采用稀疏检出 + core.protectNTFS=false 绕过；远端 Linux 不受影响，PR 仅含 archives/l/libecoli/0.11.7 与 .hmbs/pr-body.md 相关新增。
- 真机环境与官方 CI 同源，正文统一表述为「在 HarmonyOS aarch64 环境实测」，不写入真机 IP 等内部基建信息。
