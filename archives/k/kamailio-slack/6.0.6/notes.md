# kamailio-slack 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（kamailio 经典 Makefile 体系，非 autotools/cmake）
- 编译日期: 2026-09-26
- 编译器: clang（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）
- 状态: published

## 一、适配对象与打包口径

kamailio 的 `slack` 模块（`src/modules/slack/slack.so`）：把消息推送到 Slack Incoming Webhook。
脚本侧入口 `slack_send("text")`，KEMI 侧入口 `slack.slack_send("text")`。

打包口径与同源码树先例一致（`archives/k/kamailio-snmpstats/6.0.6`、`kamailio-debugger/6.0.6`）：
取官方源码包全量构建，**只编译打包目标模块**，不提供 kamailio 本体包——模块 `.so` 由
kamailio 运行时 `loadmodule "slack.so"` 加载到模块目录使用。

## 二、编译步骤

```bash
# 1) 取官方源码包（sha256 见 conandata.yml）
#    https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz
# 2) 生成构建配置（必须，否则报 No rule to make target 'cfg-defs'）
make cfg include_modules=slack LOCALBASE=<curl package_folder> CURL_BUILDER=
# 3) 构建目标模块
make modules modules=modules/slack -j1 LOCALBASE=<curl package_folder> CURL_BUILDER=
# → src/modules/slack/slack.so
```

`<curl package_folder>` 即制品仓 `curl/8.15.0.1` 的包目录（含 `include/`、`lib/`）。

## 三、依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| curl | 8.15.0.1 | 模块 Makefile 的 `LIBS += -lcurl`；制品仓已发布二进制（W0 依赖检查通过，无需新建依赖分支） |

运行时模块依赖（非 conan 依赖）：`http_client` 模块。`slack.c` 的 `mod_init()` 调
`httpc_load_api(&httpapi)` → `find_export("bind_http_client")`，故 kamailio 侧配置里
**必须先 `loadmodule "http_client.so"` 再 `loadmodule "slack.so"`**；本包只提供 `slack.so`。

## 四、上游测试（R51 三步法）

### 1) 清点（口径可复现）

```bash
tar tzf kamailio-6.0.6_src.tar.gz | grep -E '/(test|tests)/' | grep -v '/$' | wc -l   # → 17
```

| 分组 | 文件数 | 性质 |
|------|--------|------|
| `utils/kamctl/dbtextdb/tests/` | 10 | `dbtextdb_test.py` 的用例数据 |
| `src/modules/janssonrpcc/test/` | 3 | jsonrpc-c 模块脚本 + 配置 |
| `src/modules/rtpproxy/test/` | 3 | rtpproxy 模块配置 + 命令行记录 |
| `src/modules/tm/test/` | 1 | tm 模块开发期 IPC 清理脚本 |
| **合计** | **17** | |

`slack` 模块自身源码目录内**无测试文件**、无 `check`/`ctest` 目标注册。

### 2) 实跑

17 个文件中唯一自包含、无需运行中 kamailio 实例的上游测试：

```bash
cd utils/kamctl/dbtextdb && python3 dbtextdb_test.py -v
# Ran 3 tests in ... OK（fixtures: tests/ 下 10 个数据文件）
```

该命令已内置在 `conanfile.py` 的 `build()` 末尾（`_run_upstream_tests()`），非零退出即构建失败，
因此「上游测试真实执行」与「产物完整性」在同一次 `conan create` 内完成，无跳过空间。

### 3) 回填

- 上游测试用例通过率：**3/3（100%）**
- 声明 N 与实测 N 一致：**N = 17**（清点口径 = 官方源码包内 `test/`、`tests/` 目录文件数）
- 未独立执行的 14 个文件逐项技术原因见 `test_package/MANIFEST.yml` 的
  `upstream_tests[].not_executed_reason`（数据文件 / 需 kamailio 主程序 / 需外部进程 / 破坏性脚本）

## 五、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 宿主 `curl-config`/`pkg-config` 会把构建机 x86_64 的头库路径带进交叉编译 | `slack/Makefile` 在 `CROSS_COMPILE` 为空时优先用宿主 `CURL_BUILDER --cflags/--libs` | 显式传 `CURL_BUILDER=`（空）使其回落 `LOCALBASE` 分支，并用 `LOCALBASE=<curl 包目录>` 钉死制品仓版本 |
| 2 | `make modules` 直接执行报 `No rule to make target 'cfg-defs'` | kamailio 经典 Makefile 需先由 `make cfg` 生成 `src/config.mak` | 先 `make cfg include_modules=slack` 再 `make modules modules=modules/slack` |
| 3 | — | — | —

## 六、验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

（本机实测输出与通过率见 `reports/conan-create.log`、`reports/test-report.md`；
产物结构 14 项断言 + 消费者 E2E 用例结果见 `reports/test-report.md`。）

## 七、交付物

| 文件 | 说明 |
|------|------|
| `lib/kamailio/modules/slack.so` | 目标模块（AArch64 ELF 共享对象） |
| `licenses/COPYING` | 上游许可证正文（GPL-2.0-or-later） |

## 八、注意事项

- 模块加载顺序：`http_client.so` 必须在 `slack.so` 之前加载（`mod_init()` 绑定其 API）。
- Webhook URL 通过 `modparam("slack", "slack_url", "https://hooks.slack.com/services/...")` 配置；
  未配置时模块可用但发送返回错误。
- 本包不含 kamailio 本体：`slack.so` 需放入既有 kamailio 安装的模块目录后由运行时加载。
