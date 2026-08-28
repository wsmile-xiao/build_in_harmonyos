# E327: restinio 0.6.19 header-only 适配 — 官方 tarball 未打包 bundled 依赖 + sendfile 部分读 Broken pipe → SIGSEGV + http-parser 依赖闭环

> **⚠️ DRAFT（草稿）**: 未提升为正式条目，禁止 promote。
> **结构化数据**: [drafts/E327-draft-D4B1.kv](../drafts/E327-draft-D4B1.kv)
> **严重度**: 🔴 blocking | **分类**: header-only|testing|dependency|platform | **自动修复**: ❌ manual
> **来源**: restinio 0.6.19 HarmonyOS PC 知识库拓展（路径 B）probe，2026-08-15

---

## 错误特征

```
CMake: add_subdirectory given source "dev/fmt" which does not contain a CMakeLists.txt
CMake: Compatibility with CMake < 3.5 has been removed from CMake (http_parser 子项目 cmake_minimum_required 3.4)
测试: unable to openfile 'test/sendfile/f1.dat': No such file or directory
测试: read_until: End of file
测试: send file data error: 32 (Broken pipe)
测试: Signal 11 (core dumped) / SIGSEGV
```

## 触发条件

- 构建系统: cmake
- 阶段: configuration / testing
- 适用: 以官方 release tarball 直接构建 restinio 0.6.19（或同类 header-only HTTP 库）时；
  以及在其上游测试中执行 sendfile 相关用例时

## 根因

restinio 0.6.19 官方 release tarball 存在三个相互独立、但叠加影响适配的问题：

1. **官方 tarball 不含 bundled 依赖源码**：`dev/asio`、`dev/fmt`、`dev/nodejs/http_parser/` 下只有
   `CMakeLists.txt` 骨架，`http_parser.c/.h` 等源码均未打包。依赖获取在官方流程中由
   `externals.rb`（MxxRu Ruby 脚本）完成：asio 1.28.1、fmt 10.1.0、nodejs/http-parser v2.9.4、
   Catch2 v2.13.9、Clara v1.1.5。CMake 默认路径（`RESTINIO_FIND_DEPS=OFF`）执行
   `add_subdirectory(fmt)` / `add_subdirectory(nodejs/http_parser)` 必然失败。
2. **CMake 4.x 兼容性**：`dev/nodejs/http_parser/CMakeLists.txt` 声明 `cmake_minimum_required(3.4)`，
   CMake 4.1.2 移除了 `< 3.5` 兼容 → 需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（已有 E103/E187 覆盖）。
3. **依赖闭环**：http-parser 是 restinio 的必需依赖（无关闭开关；默认 add_subdirectory bundled，
   或 `RESTINIO_USE_EXTERNAL_HTTP_PARSER=ON` 时 `find_package(http-parser REQUIRED)`），
   但 ohpcd 制品仓中 `http-parser`、`http_parser`、`nodejs-http-parser`、`unofficial-http-parser`
   均无任何 recipe（fmt/8.1.1、catch2/2.13.10-r0、boost/1.84.0 存在）→ R36 依赖闭环。

4. **sendfile 测试崩溃（真实症状，待确认平台特有性）**：从正确 CWD 运行
   `_unit.test.sendfile` 时 10 个 test case 中 9 通过、1 失败（"sendfile with partially-read
   response"，main.cpp:644），断言 1822/1823 通过，随后 Signal 11 (SIGSEGV) 崩溃，
   3/3 可复现（EXIT=139）。日志显示客户端中途断开（Broken pipe, errno 32）后崩溃。

## 探针证据（probe_only_no_upload）

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 配置 | `cmake ../src/dev -DCMAKE_BUILD_TYPE=Release -DRESTINIO_SAMPLE=OFF -DRESTINIO_BENCH=OFF -DRESTINIO_ALLOW_SOBJECTIZER=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（依赖按 externals.rb 装配） | 0 | 配置成功 |
| 构建 | `cmake --build . -j4` | 0 | 100% 完成 |
| ctest | `ctest --output-on-failure` | 8 | **53/54 通过**，sendfile 失败 |
| sendfile 直跑（错误 CWD=build 根） | `./test/sendfile/_unit.test.sendfile` | 7 | 10 cases 3 passed 7 failed（数据文件相对路径问题） |
| sendfile 直跑（正确 CWD） | `cd test/sendfile && ./_unit.test.sendfile` | 139 | 10 cases 9 passed 1 failed，Signal 11 (SIGSEGV)，3/3 可复现 |

> 数据路径假象：ctest 从 build 根目录运行时，`configure_file` 把 f1.dat 复制到
> `${CMAKE_CURRENT_BINARY_DIR}/test/sendfile/f1.dat`（即 build/test/sendfile/test/sendfile/），
> 而测试代码按相对路径 `test/sendfile/f1.dat` 读取 → 从 build 根找不到数据文件导致
> 7 个 case 失败（unable to openfile → read_until EOF）。从正确 CWD（build/test/sendfile）
> 运行时数据文件可找到，剩余 1 个 case 崩溃是真实症状。

## 解决方案

### 推荐方案：probe-only-then-publish-deps

1. header-only 库先以官方 tarball + externals.rb 装配依赖做 probe_only_no_upload 最小构建
   与上游测试，确认真实症状与数据路径；
2. required 依赖（http-parser）未发布时**停止正式适配**，按 R36 先发布 http-parser 到 ohpcd
   制品仓，再继续 conanfile 归档；
3. **不得把依赖源码混入 restinio PR**（conanfile 中不得内嵌 http-parser 源码或 patch）。

### 回退方案：fix-test-data-cwd

sendfile 类测试从 build 根目录跑会因测试数据相对路径与 configure_file 复制位置不一致而失败；
应从正确 CWD（build/test/sendfile）运行，或把数据文件放到测试期望的相对路径，
再区分"数据路径问题"与"真实崩溃"。

## 禁止做法

- ❌ 修改上游测试断言、skip 条件、测试数据或预期结果（掩盖真实症状）
- ❌ required 依赖未发布时把 http-parser 源码/patch 混入 restinio PR（R36 依赖闭环被绕过）
- ❌ 用空壳 self.run / echo / mock / 仅检查文件存在代替真实测试运行（R34）
- ❌ 把"构建成功"写成"上游测试全部通过"（真实统计：53/54，sendfile 崩溃）
- ❌ promote 本草稿

## 适用条件

- header-only C++14 HTTP 服务库（restinio 及同类）在 HarmonyOS PC 上的适配
- 官方 release tarball 依赖 externals.rb / 外部下载获取 bundled 依赖的库
- required 依赖未发布到 ohpcd 制品仓时的适配决策

## 不适用条件

- 官方 tarball 完整打包依赖源码的 header-only 库（无需装配 externals）
- 已有 http-parser 等依赖发布在 ohpcd 的场景（可直接走 R36 正常适配）

## 风险与待确认

- sendfile SIGSEGV 是否平台特有（OHOS）仍需对照上游 issue 与 Linux x86_64 验证；
  未确认前不作为 restinio 平台缺陷的最终结论
- http-parser 发布到 ohpcd 后，需重新 probe 确认依赖闭环解除

## 2026-08-18 后续验证（依赖闭环已解除 + 正式适配成立）

http-parser/2.9.4 已发布到 ohpcd 制品仓（本轮 `conan list http-parser/2.9.4 -r=ohpcd`
返回 1 recipe + 可用 binary package，SHA256 与官方 v2.9.4 一致）。R36 依赖闭环已解除。

### sendfile 证据收敛（2026-08-18 重跑）

**已证实事实（本机 aarch64 原生执行，非 qemu）**：
- 命令：`cd restinio-src/probe/build/test/sendfile && ./_unit.test.sendfile`（正确 CWD，数据文件
  `test/sendfile/f1.dat` 在位）
- 退出码：139（SIGSEGV）
- 统计：test cases 10 | 9 passed | 1 failed；assertions 1823 | 1822 passed | 1 failed
- 失败位置：`probe/src/dev/test/sendfile/main.cpp:644`，TEST_CASE "sendfile with partially-read
  response"（Catch v2.13.9）
- stderr 关键行：`ERROR: [connection:1] send file data error: 32 (Broken pipe) bytes` →
  `ERROR: [connection:1] unable to write: Broken pipe` → `close` → Catch2 `SIGSEGV -
  Segmentation violation signal`

**Linux 基线状态**：
- 本环境为 aarch64 宿主，无 x86_64 环境可执行同版本 0.6.19 基线 → **Linux x86_64 同版本实测未验证**。
- 上游历史证据：Issue #72（2020-02-07，restinio 0.6.3，Ubuntu 18.04 gcc 8.3.0）——
  sendfile 期间客户端关闭 socket → SIGPIPE → SIGSEGV，官方在 v0.6.4 修复
  （"fixed for me when sending a file to the client"）。注意：这是 0.6.3→0.6.4 的历史修复，
  **不是 0.6.19 的 Linux 基线**；0.6.19 测试仍复现 SIGSEGV。
- **待验证假设**：0.6.19 在 Linux x86_64 上是否同样 SIGSEGV → 未验证，**不得称为平台特有**。
  仅可表述为"本机 aarch64(OHOS) 环境可复现，Linux x86_64 基线未验证，平台特有性待定"。
- **2026-08-26 web 检索补充**：restinio 上游文档（0.7 sendfile 文档，
  stiffstream.com/en/docs/restinio/0.7/sendfile.html）明确记载"Linux 上向客户端已关闭的
  socket 写 sendfile 会触发 SIGPIPE（需自行忽略或安装 handler）"——即"客户端断开→
  SIGPIPE"机制至少在上游文档层面是**通用平台行为**，与 OHOS 无关；上游 Issue #172
  （0.6.15，Guix 隔离容器）亦出现 `_unit.test.sendfile` 失败，但根因是
  `resolve: Host not found`（容器 DNS），属另一类环境问题，非本 SIGSEGV 边界。
  因此：机制层面有上游文档佐证为通用行为，但 0.6.19 Linux x86_64 实测基线仍为
  **未验证**，平台特有性结论保持"待定"，不升级为平台缺陷。

**可复用范围**：header-only 库装配（externals.rb bundled 依赖 → Conan requires）模式适用于
同类 Stiffstream 库；sendfile 部分读 Broken pipe 边界适用于所有 sendfile 类 HTTP 响应场景。
**失败边界**：仅 "sendfile with partially-read response" 1 个 case；其余 9 个 sendfile case 通过。
本轮适配不编译 sendfile 示例（header-only 配方），该边界属上游测试在目标环境的运行时边界，
记录为知识边界，不弱化处理。

**本轮未改** sendfile 测试断言/skip/数据/预期；E327 草稿保持 draft，禁止 promote。

### 正式适配证据（2026-08-18）

本轮完成 restinio 0.6.19 正式 Conan 配方适配（archives/r/restinio/0.6.19/），真实证据：

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| conan create | `conan create archives/r/restinio/0.6.19/conanfile.py --name=restinio --version=0.6.19 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd` | 0 | fmt/8.1.1 + http-parser/2.9.4 从 ohpcd 解析下载，restinio 包构建成功，test_package 编译链接运行通过 |
| test_package | （conan create 内部触发） | 0 | `assertions_passed=3 request_handler=wired fmt_link=ok http_parser_link=ok`（fmt::format 链接、http_parser_settings_init �号链接、express_router GET 路由安装） |
| conan-verify | `ohc-run.py conan-verify restinio 0.6.19 --profile ohos-aarch64 --project-dir <worktree>` | 0 | G1/G2/G3/G4/L2/L4/L5 全 PASS，verdict PASS |
| finish | `ohc-run.py finish restinio 0.6.19 built --project-dir <worktree>` | 外层 1 / 内部 0 | EXIT_REASON=finish_success，EXIT_CODE=0（知识整理完成）；外层非零因 Step6 gen_summary 报 `'str' object has no attribute 'append'`（ohc-run.py 内部 bug）+ Step8 submit 就绪预检缺 test-report.md/packaging/.staging-verified（W4 门禁，本轮禁 commit 故未补） |
| pre_pr_audit check | `pre_pr_audit.py check --repo-dir <worktree>` | 1 | 缺 `.ci-result.json`（W3 本地 CI 模拟结果文件，本轮禁 commit/PR 故未生成） |

配方设计要点：
- package_type=header-library，不编译任何二进制；打包 129 restinio 公共头 + .ipp 实现文件到 include/restinio/，bundled standalone-asio 1.28.1 snapshot 到 include/（asio.hpp + asio/*）。
- Conan requires fmt/8.1.1 + http-parser/2.9.4（真实 ohpcd 平台包，不内置依赖源码）。
- cpp_info.defines=[ASIO_STANDALONE, ASIO_HAS_STD_CHRONO, ASIO_DISABLE_STD_STRING_VIEW]（与上游 CMakeLists.txt 默认 standalone 一致）。
- bundled asio snapshot 由 conanfile.source() 显式下载 codelload asio-1-28-1.tar.gz（SHA256 5ff6111ec8cbe73a168d997c547f562713aa7bd004c5c02326f0e9d579a5f2ce），layout 到 dev/asio/（codelload 顶层 asio-asio-1-28-1/ 始 strip_root，余 asio/include/asio.hpp）。

本轮未改 sendfile 测试断言/skip/数据/预期；sendfile 平台边界（main.cpp:644 Broken pipe 后 SIGSEGV EXIT=139，3/3 可复现）仍为待确认平台特有性，本草稿记录不变。本轮适配不编译 sendfile 示例（header-only 配方），该边界属上游示例在 OHOS 运行时边界。

知识库查重（2026-08-18）：关键词 restinio/header-only/asio/http-parser/sendfile/Broken pipe/SIGSEGV/externals.rb/RESTINIO_FIND_DEPS 命中知识库——restinio 仅本草稿；header-only 命中 E035/E099/E191（通用 header-only 适配，不覆盖 restinio 特有 externals.rb 装配 + bundled asio + Conan requires 组合）；SIGSEGV 命中 E040/E222/E249（不覆盖 sendfile Broken pipe 特有路径）。结论：E327 形成新的"header-only + 外部依赖选择 + externals.rb bundled 装配 + 鸿蒙"问题组合，无正式条目完整覆盖，本草稿保持 draft。

本草稿仍为 draft，禁止 promote。本轮未 commit/push/PR//ai review//rebuild/任务平台提审。
