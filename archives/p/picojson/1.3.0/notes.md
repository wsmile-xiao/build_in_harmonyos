# picojson 1.3.0 适配笔记

## 编译环境
- 构建系统: header-only（无构建族；上游仅 Makefile 构建测试）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built（conan-verify 全门禁通过，待 CI upload 后转 published）

## 编译步骤

1. 官方源下载：`curl -L https://codeload.github.com/kazuho/picojson/tar.gz/refs/tags/v1.3.0`
   SHA-256: `056805ca2691798f5545935a14bb477f2e1d827c9fb862e6e449dbea22801c7d`
   （github.com archive URL 在本环境连接超时；codeload.github.com 为 GitHub 官方归档 CDN，仓库内 163 个配方同型 URL）
2. 上游测试（OHOS 工具链直接编译运行，双配置）：
   - `clang++ -Wall test.cc picotest/picotest.c -o test-core && ./test-core` → TAP 1..99 全过
   - `clang++ -Wall -DPICOJSON_USE_INT64 test.cc picotest/picotest.c -o test-core-int64 && ./test-core-int64` → TAP 1..125 全过
3. header-only 安装语义验证：`make install DESTDIR=$TEST_PREFIX prefix=/usr/local`（需 PATH 含 /bin，本环境 install 在 /bin）
   消费者程序 `#include <picojson.h>` 编译运行成功（parse/inspect/serialize）
4. `ohc-run.py conan-verify picojson 1.3.0` → G1-G4 + L2/L4/L5 全部 PASS（可标记 published）
   - test_package：test_picojson（消费者）+ test_ohos（OHOS 专项，5 项平台敏感断言）均编译运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create: "Package type is 'library', but no 'shared' option declared" | header-only 包声明 package_type=library 但无 shared option | 改用 Conan 2 原生 `package_type = "header-library"`（仓库 7bitdi/ableton-link 同型） |
| 2 | conan create source(): `BadZipFile: File is not a zip file` | codeload URL 末段是 tag 名 "v1.3.0" 无扩展名，get() 按末段推导文件名后默认按 zip 解压 | conandata.yml sources 显式声明 `filename: "picojson-1.3.0.tar.gz"`（与 E276/E483 方案等效） |
| 3 | CMake: "Cannot determine link language for target test_picojson" | conan-init 生成 test.c + project(... C)，改为 CXX 后 .c 源导致无 C 链接语言；C++ 代码须用 .cc 后缀 | test.c → test.cc，CMakeLists/MANIFEST 同步引用 |
| 4 | package(): WARN "No files in this package!" | conan copy() 的 dst 相对路径按进程 CWD 解析，package() 时 CWD 非 package_folder | dst 全部改为绝对路径 `os.path.join(self.package_folder, "include")` |
| 5 | 上游测试 test_picojson 首次 CTest 失败（静默 exit 4） | test.cc 断言 tags 数组 3 元素但 JSON 只给 2 个（自身断言 bug） | 测试数据补第 3 个 tag，断言自洽 |
| 6 | make install 报 "install: No such file or directory" | install 二进制在 /bin 但不在默认 PATH | PATH 补 /bin 后重跑 |

## 依赖版本
- 无第三方依赖（header-only）
- 工具链：OHOS SDK 26.0.0.18 clang 15.0.4 / libc++17

## 验证结果

```bash
# 上游测试（OHOS 工具链直接运行）
./test-core        # 1..99 全过, exit 0
./test-core-int64  # 1..125 全过, exit 0
# 消费者 + OHOS 专项
./test_picojson    # exit 0
./test_ohos        # "ohos-picojson-test: ALL PASS", exit 0
# 配方门禁
conan-verify picojson 1.3.0  # G1 PASS G2 PASS G3 PASS G4 PASS + L2/L4/L5
```

## 上游测试台账（双口径）

| 入口 | 类型 | 是否独立上游用例 | 结果 |
|------|------|------------------|------|
| test.cc + picotest/picotest.c,h（默认配置）→ test-core | 用户测试源（picotest 断言框架） | 是（1 个测试源文件的默认配置实例，运行时 99 项断言） | 运行通过 99/99 |
| test.cc（-DPICOJSON_USE_INT64 配置）→ test-core-int64 | 用户测试源（int64 编译变体） | 是（同一测试源的第 2 个配置实例，运行时 125 项断言） | 运行通过 125/125 |
| picotest/picotest.h,c | 框架源码（ok/is/_ok 宏与输出） | 否（框架内部宏，不计入上游用例） | 已运行（随 test-core 链接执行） |
| examples/github-issues.cc, iostream.cc, streaming.cc | 样例 | 否（样例非独立用例，按规则不计入） | 未运行（非测试声明） |
| Makefile test/check 目标 | 构建目标（聚合 test-core+test-core-int64） | 否（聚合目标非独立用例） | make check 语义=两二进制运行，均已过 |
| README.mkdn | 文档 | 否 | — |

- 源码声明总数口径：test.cc 静态 ok() 断言 58 处；含循环展开运行时实例化 99（默认）/125（int64）。
- configured_executable_total：2 个独立可执行（test-core、test-core-int64）。
- executed_passed_total：2/2 配置实例全部运行通过。
- 全量通过率：2/2 配置实例（100%）；运行时断言 224/224（99+125）。
- 映射：test.cc 宏/断言 → 无预处理互斥（仅 PICOJSON_USE_INT64 切换 int64 行为，两个配置都编译）→ Makefile test 目标 → test-core/test-core-int64 → TAP 计划行 1..99 / 1..125 实际日志。

## 知识候选台账 + 四范围查重（task 要求）

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 正式知识查重 | 图谱查重 | 草稿查重 | 结论 |
|------|----------|------|------|------|--------------|----------|----------|------|
| A. codeload 无扩展名 URL → BadZipFile | `BadZipFile: File is not a zip file` (source()) | get() 按 URL 末段推导文件名，无扩展名默认 zip 解压 | conandata sources 显式 filename= | conan-verify G2 PASS | E276/E483/E392 已覆盖（同根因同方案） | 命中 E483 (2244) | E276.md/E483.md 存在 | exact_duplicate → reuse_existing（本轮复现验证既有方案） |
| B. package_type=library 无 shared option | `Package type is 'library', but no 'shared' option declared` | header-only 包误用 library 类型缺 shared 契约 | 改用 package_type=header-library | conan-verify G2 PASS | E283（declare-shared-contract）+ E321/E322（header-library 模式已入库） | 命中 E283 (6) | E321.md/E322.md 存在 | solution_overlap → reuse_existing |
| C. CMake Cannot determine link language（test.c 于 CXX-only 项目） | `Cannot determine link language for target test_picojson` | C++ 消费者写成 .c 源，CXX-only 项目无 C 链接语言 | 改 .cc 后缀 | conan-verify G2 PASS | 未命中（E053 为 cc1plus 误命中，不相关） | 无匹配条目 | 无 | 未命中 → 新增草稿 DRAFT-picojson-1.3.0-test-package-source-language.kv |
| D. copy() 相对 dst → 空包 | `package(): WARN: No files in this package!` | copy() dst 相对路径按进程 CWD 解析，package() 时 CWD ≠ package_folder | dst 用 package_folder 绝对路径 | conan-verify G2 PASS（Packaged 1 '.h' file） | 未命中（E292 为 Arrow 类测试环境误命中，不相关） | 无匹配条目 | 无 | 未命中 → 新增草稿 DRAFT-picojson-1.3.0-conan-copy-absolute-dst.kv |
| E. 引擎噪声：E540 shadow-ci / E325 resource-data-package | conan-verify 时引擎提示（非实际错误） | 关键词模糊命中；本包无 configure/make 失败、非资源数据包 | 不适用（噪声，忽略） | — | — | — | — | 噪声，不建草稿 |

### 七轴查重（相对候选 C 与 D 的新增知识）

- exact_duplicate: 否（无同根因同方案条目）
- causal_duplicate: 否（C 与 D 根因不同，互不因果）
- trigger_overlap: C 与 D 均属 header-only Conan 配方 test_package/package 阶段，触发上下文有交集（同配方同一构建流程），但错误签名、阶段与修复动作不同
- solution_overlap: 与 E321/E322/E283 无方案重叠（E321/E322 是 cmake install 路线，不涉及 copy() dst 语义；E283 是 library 类型 shared 契约，与本两个候选无关）
- combination_novelty: C+D 组合覆盖"header-only 配方从 test_package 源语言到 package() 拷贝的完整陷阱面"，既有条目无此组合
- boundary_novelty: C 的边界=任何把 C++ 消费者写成 .c 的 test_package；D 的边界=任何手写 package() 用相对 dst 的配方（尤其 header-only 无 install 流程时）
- test_migration_novelty: 无（非测试迁移场景）

### 路径判定

- 候选 A、B：完整重复/方案重叠 → reuse_existing（路径 A 成分，复用 E276/E483/E283/E321）
- 候选 C、D：已验证、可跨库复用、查重未命中且存在新增差异 → new_draft → **路径 B（知识库扩展）**
- PR 前缀：【知识库扩展】（new_draft 且 .md/.kv 配对通过）
- 知识草稿与 picojson 归档文件进入同一 PR（task 要求），不另建知识库 PR

## 注意事项

- 官方源 URL 保持 codeload.github.com（PF7 黑名单外官方域；init-build 提示的 gitcode 镜像属黑名单搬运源，不可使用）
- /tmp 只读（E002），下载与构建全部使用 $TMPDIR=/storage/Users/currentUser/tmp
- 本 worktree 存在 libxext/libXext 大小写碰撞噪声（main 树两目录并存 + 本机文件系统大小写不敏感），属既有环境条件，任何提交只 add 本任务路径避免污染
---

**编译结束**: 2026-09-06 21:55
**最终状态**: built
