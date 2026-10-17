# wolfmqtt 1.19.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am + LT_INIT）
- 编译日期: 2026-09-14
- 编译器: clang（OHOS aarch64 交叉）
- 状态: built

## 编译步骤

1. `autoreconf` 自举：GitHub archive tarball 不含 configure（仅 git tree 快照），
   配方 `build_requirements()` 声明 `tool_requires(automake/1.18)` + `tool_requires(libtool/2.5.4)`
   （`LT_INIT` 需要 libtoolize），运行期检测无 configure 即 `Autotools.autoreconf()`。
2. E007：autoreconf 安装的 config.guess/config.sub 不识别 HarmonyOS，运行期替换为
   OHOS-aware 自包含版本（merged 先例 dcfldd/1.9.3 同款）。
3. `configure --enable-static --disable-shared --disable-examples
   --with-libwolfssl-prefix=<wolfssl 包目录>`：configure 的
   `--with-libwolfssl-prefix` 要求 `<prefix>/lib` 与 `<prefix>/include` 存在并自行追加
   -L/-I，与 Conan 依赖的 package_folder 布局完全吻合（generate() 注入）。
4. `make -j1` 编译，`make install` 打包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 configure，无法直接 configure | archive tarball 只是 git tree 快照 | tool_requires automake/libtool + autoreconf 自举（dcfldd/argp-standalone 同款先例） |
| 2 | TLS 默认启用且 AC_CHECK_LIB 硬依赖 libwolfssl | configure.ac `ENABLED_TLS=yes` 为默认 | 引入已发布的 wolfssl/5.7.0 依赖，前缀经 --with-libwolfssl-prefix 注入 |
| 3 | config.guess/sub 不识别 HarmonyOS | automake/1.18 自带版本不含 linux-ohos 三元组 | E007 运行期替换（dcfldd 先例） |

## 设计取舍

- `--disable-examples`：examples 为网络演示程序（mqttclient/aws/azure/firmware），
  不属于库交付物；消费者测试由 test_package 承担。
- 保留上游默认 TLS（ENABLE_MQTT_TLS），不做 --disable-tls 降配，保真度更高。
- LT_INIT([disable-static ...]) 仅是 libtool 默认值；配方显式传
  --enable-static --disable-shared 覆盖（wolfmqtt 非系统同名库，静态交付由 Conan 管依赖）。

## 上游测试清点（R51 三步法）

- 上游源码（tag v1.19.0）**无自动化测试套件**：顶层无 tests/ 目录；Makefile.am
  `TESTS =`、`check_PROGRAMS =`、`check_SCRIPTS =` 全为空；全源码 grep
  `TEST_CASE`/`add_test`/`ASSERT_` 零命中（examples/ 为演示程序非测试）。
- 因此上游静态用例数 N_static=0，`make check` 无可执行目标。

### 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 上游无自动化测试（清点证据见上） |
| N_registered（构建系统注册） | 0 | TESTS/check_PROGRAMS 为空 |
| N_executed（实际执行） | 0 | 上游无测试可执行 |
| N_consumer（新增消费者测试） | 1 | test_package/test_wolfmqtt（API 断言 4 处） |

## 依赖版本

- wolfssl/5.7.0（TLS，制品仓已发布，`conan download --only-recipe` 实测可拉）
- automake/1.18、libtool/2.5.4（tool_requires，autoreconf 自举）

## 源码修改

无补丁（patches 为空）。配方仅注入构建参数，不改上游源码。
---

**编译结束**: 2026-09-14 01:46
**最终状态**: built
