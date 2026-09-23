# open62541 1.5.6 适配笔记

## 当前状态

- 本轮目标：完成 W0-W4 的本机前置适配，并执行单包真机 shadow CI。
- 当前结果：Conan 配方、OHOS 补丁和消费者测试已准备；真机 shadow CI 已通过。
- 真机/shadow CI：通过（L0/L1/L4/L5 通过；静态库无可执行文件，L2 按规则跳过）。
- issue：按用户要求不再维护 issue 编号。
- 任务去重：继续使用已有 `feat/open62541-1.5.6` worktree；远端较早的
  `fix/open62541-1.5.6` 属于同库同版本任务线，本轮未创建第三个分支或第二个任务。
- 制品去重：CNB 的 `open62541/1.5.6` 精确包详情返回 `packageDetail.code=404`
  且无 package data；HTTP 200 仅是前端 SPA 壳，不能作为包存在证据。当前版本未发现
  已发布 recipe，因此保留上游版本号 `1.5.6`。

## W0 依赖检查

- 运行时依赖：无。
- 构建依赖：CMake、Clang/C99 编译器；这些是构建环境工具，不作为 Conan 运行时依赖。
- 测试依赖：官方 CTest 单元测试需要 Check/libcheck；仓库已有 `check/0.15.2`，但它只属于测试依赖，本轮不把它声明为生产依赖。
- 可选功能：禁用 mDNS discovery，避免引入外部 mDNS 实现。

W0 结论：

```text
依赖数量：0 个生产 Conan 依赖；1 个已存在的测试依赖 check/0.15.2
已满足依赖：无运行时依赖；Python3 是上游代码生成所需的构建工具
缺失依赖：无；本机已使用 DevEco OpenHarmony Native SDK 的 CMake/Ninja/Clang 和 Conan 2.29.1 完成交叉构建
是否需要拆分依赖适配：否，check/0.15.2 已在仓库中
阻塞点：无；官方 CTest 已在真机独立测试构建中完成验证
说明：Check/libcheck 仍未纳入生产包依赖，测试在隔离 job 中执行
```

## W1 源码和构建系统

- 上游：`https://github.com/open62541/open62541`
- 上游版本：`v1.5.6`
- 源码归档：`https://github.com/open62541/open62541/archive/refs/tags/v1.5.6.tar.gz`
- SHA256（配方声明值，沿用已有适配记录）：`920a4c05a9b32862d38f60a70bc0972f29352fd55ba2393fa6bf49b14bcba222`
- 构建系统：CMake；库主体为 C99。
- 上游测试入口：CTest，依赖 Check/libcheck；已在真机隔离测试构建中运行。生产配方仍关闭
  `UA_BUILD_UNIT_TESTS`，不把 Check/libcheck 引入生产依赖。
- 官方 tag archive 包含 `tests/`、`plugins/include/open62541/server_config_default.h` 和内置 `deps/`，适合 Conan `source()` + `strip_root=True`。

## W2 Conan 配方

配方使用静态库作为默认配置，并保留 `shared` 选项。OHOS 配置显式设置
`CMAKE_SYSTEM_NAME=OHOS`、`aarch64` 和 `CMAKE_INSTALL_LIBDIR=lib`，关闭
单元测试、示例、mDNS discovery、debug sanitizer 和 amalgamation。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'bits/stdio_lim.h' file not found` | glibc-only header included unconditionally for non-Android/Apple/OpenBSD platforms. HarmonyOS uses musl libc which does not provide this header. | `eventloop_posix.h` 仅在 `__GLIBC__` 定义时包含该私有头文件。 |
| 2 | `error: redefinition of 'sockaddr_storage'` | `eventloop_posix_eth.c` 引入的 Linux kernel headers 与 HarmonyOS sysroot 的 musl socket headers 冲突。 | 通过 CMake `UA_ENABLE_POSIX_ETHERNET` 能力开关从 `plugin_sources` 排除 raw Ethernet 源文件。 |
| 3 | `undefined symbol: UA_ConnectionManager_new_POSIX_Ethernet` | 默认注册条件与实际编译的插件源文件不一致，会在实现被排除后留下链接引用。 | 使用同一个 `UA_ENABLE_POSIX_ETHERNET` compile definition 控制默认 raw Ethernet 注册。 |

## W3 消费者测试

`test_package` 使用 CMakeDeps/CMakeToolchain 构建独立的 C 程序，链接
`open62541::open62541`，创建 `UA_Server`、取得配置并调用
`UA_ServerConfig_setMinimal`，再释放服务实例。测试不访问外网，也不需要启动 OPC UA 服务。
交叉构建时只确认编译和链接，避免在构建主机误执行目标架构 ELF。

## W4 本机前置验证

- 已执行：工作树、分支和变更范围检查。
- 已执行：源码、补丁、配方和 test_package 结构审计。
- 已执行：Windows 本机 OHOS 交叉构建；DevEco SDK CMake 3.28.2、Ninja 1.13.2、
  OHOS Clang 15.0.4 和 Conan 2.29.1 均已接入临时本机 profile。
- 已执行：`conan create` 的包构建与安装，100/100 个 CMake/Ninja 构建目标完成。
- 已执行：独立 `test_package` 的 CMake 配置、AArch64 编译和真实链接；生成物经
  `llvm-readelf` 确认为 ELF64 AArch64。Windows 主机不执行该目标 ELF。
- 已执行：真机隔离 shadow CI 的 `conan create`、CMake 编译、安装和消费者测试。
- 已执行：真机 AArch64 上游 CTest。`tests/` 源码清点为 205 个 C 文件、3521 个
  `START_TEST` 用例；当前 OHOS 配置注册 141 个 CTest，其中 140 个 Check 测试程序
  覆盖 3118 个源代码用例，另有 1 个跨命名空间代码生成测试。
- 上游 CTest 明确结果：首轮 `--timeout 120` 执行结果为 128/141 通过、13/141 超时；
  对这 13 项使用 `--timeout 300` 串行复测，结果为 13/13 通过。因此按完整测试入口合并
  统计为 141/141 通过、0 失败、0 个已注册测试未执行。13 项较慢是设备执行时间超过
  120 秒，不是测试失败。
- 未注册上游测试：65 个源文件、403 个 `START_TEST` 用例，均由上游 CMake 条件排除，
  不是运行失败；逐项文件、数量和原因见同目录 `reports/upstream-test-report.md`。
- 上游测试真机运行设置 `TMPDIR`/`TEMP` 为 job 内可写目录，因为设备 `/tmp` 只读；
  同时对设备临时测试树使用了 Check 查找脚本、空 subunit 静态库和 ranlib 替代命令，
  这些均未写入本 PR 的源码、配方或基础设施目录。
- 真机首次运行因环境缺少 `cmake` 失败；未修改共享环境，仅在隔离任务中补充 CMake 4.1.2 后重跑。
- 真机最终结果：open62541 本体构建、静态库打包、test_package 编译/链接/运行均通过；
  L1e 破坏性反向验证通过；L0/L1/L4/L5 通过，L2 因无可执行文件跳过。
- Windows 访问 GitHub 直链不稳定；本机通过可达代理取得同一官方归档并复核 SHA256，
  未改变仓库中的官方源码 URL 和校验值。
- 本机已有缓存 `D:\harmonyos\tmp\candidate-scan\open62541.tar.gz`，大小为 6,656,000
  字节，SHA256 为 `29BE7C3CB9B22D7E71EC7B449C509FFB38C5EA52FF02D37D94B287DFADF03F8A`；
  `tar -tzf` 报 `Truncated input file`，不能作为有效源码归档。
- 官方归档已通过可达代理下载；本机复核 SHA256 为
  `920a4c05a9b32862d38f60a70bc0972f29352fd55ba2393fa6bf49b14bcba222`，与配方声明一致。
- 已执行：Python 配方语法审计、补丁文本审计、test_package 结构审计。
- 已执行：`git diff --check`、YAML 解析和 manifest/test_package 字段一致性检查。
- 未执行：Windows 本机执行 AArch64 目标程序；Windows 主机无法直接运行目标 ELF，
  该项由真机 shadow CI 和真机上游 CTest 覆盖。
- 已新增：5 组与 open62541 直接相关的知识草稿，均含 `.md` 人类可读说明和
  `.kv` 结构化条目，已在 manifest `knowledge_ref` 登记。

## 下一步真机/shadow CI 命令

从真机隔离 job 的仓库根目录执行：

```sh
conan create archives/o/open62541/1.5.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

隔离 runner 入口：

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job <open62541-job> \
  --package archives/o/open62541/1.5.6 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/<open62541-job>/run-conan-heavy.sh"
```

## 当前限制与下一步

1. 官方 Check 测试已在独立真机测试构建中完成；生产 recipe 仍不接入
   `check/0.15.2`，因此上游测试不会随生产包构建自动执行。
2. Conan 客户端查询 ohpcd 时曾被远端 `system acceleration policy not enabled`
   拦截；本轮使用公开 CNB 精确包详情完成了 recipe 占用核验，未将该环境错误误判为
   “制品已存在”。
3. 本地和真机前置验证已完成，下一步可执行仓库 W4 审计与正式 PR 提交流程。
