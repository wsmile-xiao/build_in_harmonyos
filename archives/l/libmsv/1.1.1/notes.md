# libmsv 1.1.1 适配笔记

## 编译环境

- 构建系统：Autotools（上游标签源码需执行 `autoreconf -fi`）
- 编译日期：2026-09-20
- 编译器：HarmonyOS Clang 15，aarch64
- 状态：built

## 编译步骤

1. 从上游作者维护的 Salsa 仓库获取标签 `1.1.1` 对应的不可变提交归档。
2. 使用 `automake/1.18` 与 `libtool/2.5.4` 执行 `autoreconf -fi`。
3. 由 `AutotoolsToolchain` 注入 HarmonyOS 编译器和交叉编译参数。
4. 使用 `AutotoolsDeps` 注入 curl 与 jansson 的头文件、库及链接参数。
5. 执行单线程构建与安装；构建期运行上游 `make check`，随后通过 Conan `test_package` 运行消费者与 HarmonyOS 专项测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方历史主页与 tarball 地址不可达 | 上游旧站已停止响应 | 使用上游作者维护的 Salsa 仓库中标签 `1.1.1` 对应的不可变提交归档 |
| 2 | 标签归档不包含生成后的 `configure` | 上游 Git 标签只保存 Autotools 源文件 | 通过已发布的 Automake/Libtool 工具依赖执行 `autoreconf -fi` |
| 3 | 上游 `checkmsva` 依赖外部 MSVA | 测试假设本机已有兼容验证代理 | 测试时启动确定性的回环 MSVA，覆盖代理探测、JSON 请求与响应解析 |
| 4 | HNP Bash 在 HMDFS 构建树中无法稳定执行 `getcwd(2)` | HarmonyOS PC 的 Conan 缓存位于 HMDFS，子 shell 无法重建深层工作目录 | 在 Autoreconf 与 configure 阶段分别设置匹配的逻辑 `PWD` |
| 5 | 原生 configure 无法识别 HarmonyOS，且 HMDFS 中运行 conftest 失败 | `config.guess` 不识别 `uname -s = HarmonyOS`，构建树不适合直接执行探针程序 | 原生构建显式指定 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，保持 Autoconf 交叉语义 |
| 6 | CI Worker 的 `config.status` 无法创建 `subs1.awk` | Autoconf 以 `umask 077` 创建临时目录，HMDFS 的运行时 UID 映射导致生成脚本无法访问该目录 | 仅在 OHOS 构建中将生成后 `configure` 的临时目录掩码调整为 `022` |

## 源码修改

无源码补丁；适配仅位于 Conan 配方和消费者测试中。

## 依赖版本

- curl/8.15.0.1
- jansson/2.15.1.1
- automake/1.18（构建工具）
- libtool/2.5.4（构建工具）

## 上游测试清点与实测

| 项目 | 数量 | 证据 |
|------|------|------|
| 上游测试目录 | 0 | 源码根目录不存在 `test/` 或 `tests/` |
| Automake 注册测试 | 1 | `Makefile.am` 声明 `TESTS = checkmsva` |
| 上游测试程序 | 1 | `checkmsva.c` |
| 上游实测 | 1/1 | HarmonyOS PC 真机使用兼容回环 MSVA 执行 `make check -j1` |

适配后保留 1 个同等 MSVA 集成测试，并新增 1 个 HarmonyOS 专项测试；测试程序总数为 2，不少于上游实测的 1 个。

## 验证结果

- HarmonyOS PC 真机原生 `conan create`：通过。
- 上游 Automake 测试：`1/1` 通过（`TOTAL: 1, PASS: 1, FAIL: 0`）。
- Conan 消费者与 HarmonyOS 专项测试：`14/14` 断言通过（集成路径 6 项、HarmonyOS 专项 8 项）。
- 产物：`lib/libmsv.a`、`include/msv/msv.h` 与 `licenses/COPYING` 均由干净源码构建并打包。

消费者测试实际调用 `msv_ctxt_init`、`msv_check_msva`、`msv_query_agent`、`msv_strerror`、`msv_response_destroy` 与 `msv_ctxt_destroy`，不是空壳测试。

## 注意事项

- libmsv 是库包，不安装命令行工具，因此不创建 `commands.json`。
- 上游测试的外部代理依赖已替换为确定性回环服务；不访问公网。
- 本机交叉构建可生成目标产物与测试 ELF；通用 Alpine QEMU 根文件系统不提供 HarmonyOS `libcurl` 所需的 `__fd_chk`，因此运行结果以真实 HarmonyOS PC 原生执行为准。
- 正式归档不包含下载的源码包、构建目录、日志或二进制产物。

**最终状态**：适配完成，状态 `built`；真机赛事 CI 同源脚本 L0/L1/L4/L5 全部通过。
