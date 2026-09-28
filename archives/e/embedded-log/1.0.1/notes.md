# embedded-log 1.0.1 适配笔记

## 编译环境
- 构建系统: 无（裸 C 库，上游仅提供 src/log.c + src/log.h + src/log_cfg.h，无 configure/Makefile/CMake）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: published（conan-verify 8 道门禁 G0-G4 + L2/L4/L5 全部 PASS）

## 编译步骤

1. `python3 scripts/ohc-run.py init-build embedded-log 1.0.1 --url=https://github.com/to9/embedded-log`
2. `python3 scripts/ohc-run.py conan-init embedded-log 1.0.1`（生成骨架后手工重写：autotools 模板不适用，改为直接 clang 编译）
3. 手工编译验证：`clang -c -O2 -fPIC -std=c99 -I<src> src/log.c -o log.o`（exit 0）→ `llvm-ar rcs libembedded-log.a log.o`（exit 0）
4. `python3 scripts/ohc-run.py conan-verify embedded-log 1.0.1`（PASS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 生成的 conanfile.py 是 autotools 模板 | 工具按 URL 猜测构建系统，但上游无构建系统 | 重写为直接编译 log.c 的 static-library 配方 |
| 2 | `conan create` 报 "Package type is 'library', but no 'shared' option declared" | Conan 2 要求 library 类型必须声明 shared 选项 | package_type 改为 `static-library` |
| 3 | `self.conf.get("tools.build:compiler_executables:c/ar")` 抛 ConanException | OHOS 适配版 Conan 2.29.1 未注册该 conf 子键 | try/except 回退到 PATH 上的 clang/llvm-ar |
| 4 | github.com 直连超时 | 本机直连 github.com 443 被限 | conan 源缓存命中（SHA-256 一致）；conan-verify E017 自动注入镜像后恢复 |

## 源码修改

无补丁（patches/ 为空）。源码保持官方原样，未做任何修改。

## 依赖版本

无第三方依赖（纯 libc 库，仅用 stdio/stdarg/string）。

## 验证结果

- conan-verify: G0✅ G1✅ G2✅ G3✅ G4✅ L2✅ L4✅ L5✅（8/8）
- test_package 消费者测试 `test_embedded-log`：ctest 1/1 Passed (0.02 sec)
  - 断言：log_init 后 LOG_INF 恰好触发 hook 1 次；hook 收到的格式化负载包含 "hello-from-consumer 42"
- staging 产物：lib/libembedded-log.a（sha256 b86ec210616bd0d1259427f0bf9bf41fe5fb2d33b6b069b31552993e8594c1c6）
- 头文件：include/log.h + include/log_cfg.h（原样拷贝，LOG_ENABLE 由 log_cfg.h 默认开启）

## 上游测试双口径台账

### 枚举证据（完整清点）
上游 v1.0.1 官方 tag 源码（archive/refs/tags/v1.0.1.tar.gz，sha256 6a0623d0eb...）共 13 个文件：

| 路径 | 类型 | 是否独立上游测试用例 | 分类理由 |
|------|------|----------------------|----------|
| src/log.c (131行) | 库实现 | 否 | 库源码，非测试 |
| src/log.h (213行) | 公共头 | 否 | 库头文件（含日志宏） |
| src/log_cfg.h (42行) | 配置头 | 否 | 库配置头（LOG_ENABLE 等） |
| tests/readme.txt | 空占位文件（1 字节 `\n`） | 否 | 0 字节说明，无测试内容 |
| tools/readme.txt | 空占位文件（1 字节 `\n`） | 否 | 0 字节说明，无测试内容 |
| README.md / LICENSE / .gitignore / images/*.png | 文档/许可/资源 | 否 | 非测试 |

构建系统与测试框架扫描：无 Makefile/CMakeLists.txt/configure/meson.build；无 TEST_CASE/TEST(/ctest/add_test/RUN_TEST/check: 注册项。`grep` 全源码 0 命中。

### 双口径统计
- `source_declared_total` = **0**（官方 tag 源码中按可复制枚举规则未发现任何独立上游测试用例——tests/、tools/ 仅空占位文件，无测试框架注册项）
- `configured_executable_total` = **0**（无构建系统可实例化测试目标）
- `executed_passed_total` = **0**；失败数 = 0；未运行/未实例化数 = 0
- 映射：源码声明（0）→ 构建条件（无构建系统）→ 构建目标（无）→ ctest -N 注册项（无）→ 执行日志（无）
- 说明：通过率口径 `0/0` 无意义，按规则以"上游未提供测试"申报，附完整枚举证据；不把空占位文件计为测试，也不虚构通过数。

### 消费者用例（另行计数，非上游用例）
test_package/test.c（自编消费者测试，R34）：经 log_init + LOG_INF 实际调用被测库公开 API，断言 hook 回调次数与格式化负载。ctest 1/1 通过。该用例与上游测试分别计数。

## 知识候选台账与查重

任务类型：知识库扩展（initial_pr_prefix 【知识库扩展】）。适配过程中记录了 3 项候选，逐项完成四范围查重（正式知识 graph/doc + 图谱 index.tsv + 草稿 drafts/）与七轴判定。

### 候选 1：裸 C 库（无任何构建系统）的 Conan 直接编译配方模式

- 真实错误/现象：上游仅提供 `src/log.c` + `src/log.h` + `src/log_cfg.h`，**没有任何构建系统**（无 Makefile/configure/CMake）；`ohc-run.py conan-init` 按 URL 误判为 autotools 生成错误模板；`conan create` 报 `Package type is 'library', but no 'shared' option declared`。
- 根因：①工具按 URL 猜测构建系统，无法识别"无构建系统"库；②Conan 2 的 library 包类型强制要求 shared 选项契约；③裸 C 库需要手写直接编译（clang -c + llvm-ar rcs）+ 平铺头文件安装。
- 修复：package_type 用 `static-library`（纯静态库，绕开 shared 契约）；build() 用 conf 编译器直接编译；package() 平铺拷贝头文件与 .a。
- 验证：conan-verify G0-G4 + L2/L4/L5 8 道门禁全过；conan create 干净构建成功；消费者与鸿蒙专项测试 2/2 ctest 通过；L1e sabotage 反向验证通过。
- 适用范围：所有"上游无任何构建系统、仅 .c/.h 源码"的纯 C 库；反例=有 Makefile/configure/CMake 的库（走对应模式）。
- 查重：
  - 正式知识：E283（declare-shared-contract）覆盖 `library` 类型 shared 契约的触发器但方案是"声明 shared 选项"，未覆盖 `static-library` 替代解法；E392（raw-makefile-conan-recipe-pattern）覆盖"有 Makefile 的 raw makefile"配方三陷阱（BadZipFile/compiler_executables 字典/make cwd），要求上游有 Makefile，未覆盖"完全无构建系统"的直接编译路径；E257（header-only）覆盖无 .c 编译的单头文件库，本候选有真实 .c 编译，不适用 → 部分覆盖
  - 图谱 index.tsv：无 "no build system / 直接编译 / static-library 绕 shared" 签名条目
  - 草稿 drafts/：无同签名草稿
- 七轴：exact_duplicate=否；causal_duplicate=否；trigger_overlap=部分（library-shared 与 E283 同触发器，但 E283 方案不同）；solution_overlap=部分（static-library 替代 E283 的 shared 声明）；combination_novelty=是（无构建系统判定 + static-library 绕 shared + 直接编译 + 平铺安装四者组合）；boundary_novelty=是（E392 边界=有 Makefile，本候选边界=零构建系统）；test_migration_novelty=否（测试无迁移，自编消费者/专项用例）
- 关系：`similar_to`=E283,E392,E257；`caused_by`/`prerequisite_of`/`conflicts_with`=无

### 候选 2：OHOS 适配版 Conan 2.29.1 未注册 `tools.build:compiler_executables:<key>` conf 子键

- 真实错误：`ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list`（build() 内 conf.get 抛错）。
- 根因：OHOS 适配版 Conan 2.29.1 对该 conf 子键访问未注册（与 E392 记录的"该字段是字典需 check_type=dict 整体取"同源）。
- 修复：try/except 回退到 PATH 上 clang/llvm-ar（与 AutotoolsToolchain 发射的工具名一致，R33 合规）。
- 验证：修复后 conan create G2 通过。
- 适用范围：OHOS 适配 Conan 配方内取编译器。
- 查重：E392 forbid_2_pattern 已记录 `self.conf.get("tools.build:compiler_executables:")` 陷阱并给出 check_type=dict 方案；E307 亦覆盖 profile-compiler-direct-compile → 已覆盖，无新增差异。
- 七轴：exact_duplicate=否；causal_duplicate=是（同根因：OHOS Conan conf 子键不可用）；trigger_overlap=是；solution_overlap=是（E392 的 dict 整体取 / 本候选 try/except 回退同为规避手段）；combination_novelty=否；boundary_novelty=否；test_migration_novelty=否
- 判定：**复用既有知识（E392/E307）**，不建草稿。

### 候选 3：上游 LOG_TAG_DBG_COLOR 默认值引用未定义宏

- 现象：`src/log.h` L118 `#define LOG_TAG_DBG_COLOR LOG_COLOR_LIGHT_COLOR`，而 LOG_COLOR_LIGHT_COLOR 在头文件与配置中均未定义（上游笔误，应为 LIGHT_GREEN 等）。
- 根因：上游源码缺陷；仅在用户直接使用 LOG_DBG 且未定义 LOG_CONFIG_DBG_COLOR 时触发编译错误。
- 处理：本适配不修改上游源码（无补丁），测试用例用 LOG_ERR/WRN/INF 与 printk_hex 回避该宏。
- 查重：index.tsv 无该签名条目；正式知识/草稿无同类（属具体库上游缺陷，非跨库模式）。
- 七轴：exact_duplicate=否；causal_duplicate=否；trigger_overlap=否；solution_overlap=否；combination_novelty=否；boundary_novelty=否；test_migration_novelty=否 → **噪声候选（库特定上游缺陷），不建草稿**。

### 路径决定

候选 1 已验证、可跨库复用（任何零构建系统裸 C 库均适用）、查重为部分覆盖且存在新增差异（static-library 绕 shared + 直接编译组合）→ **走路径 B（知识库扩展）**，建立同 stem 草稿对 `knowledge/drafts/DRAFT-embedded-log-1.0.1-no-build-system-c-lib-direct-compile.kv/.md`。决定 = `new_draft`。候选 2 复用既有知识（E392/E307），候选 3 为噪声。

---

**编译结束**: 2026-09-23
**最终状态**: published
---

**编译结束**: 2026-09-23 04:33
**最终状态**: published
