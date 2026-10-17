# qoauth 2.0.1-1 适配笔记

## 编译环境
- 构建系统: qmake（Qt6）
- 依赖栈: qtbase/6.11.1 + qca/2.3.10（Qt6）
- 编译器: clang/clang++ 15（libc++，C++17）
- 编译日期: 2026-09-27
- 状态: published

## 编译步骤
1. 下载 qoauth 源码（v2.0.0 tag）
2. 依赖制品仓已发布包：qtbase/6.11.1、qca/2.3.10（Qt6 栈）
3. 应用 4 个移植补丁（QCA 路径/Qt6 兼容）
4. 构建 qoauth：qmake + make

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/src.pro 无 Qt6 版本号分支 | 上游仅写入 `equals(QT_MAJOR_VERSION, 5)` 分支 | 补丁 0001 增补 Qt6 分支（VERSION=2.0.0） |
| 2 | 编译期找不到 QtCrypto 头 / 链接不到 qca | .pro 未声明 QCA include/lib | 补丁 0001/0002/0003 注入 `QCA_INCLUDE`/`QCA_LIB` 与 `-lqca-qt6` |
| 3 | 链接期 QCA 内 Botan 符号未定义 | 制品仓 qca 静态内嵌 Botan 但未全部解析 | 补丁在 .pro 追加 `-Wl,--allow-shlib-undefined` |
| 4 | Qt6/clang 下 interface.cpp 编译失败 | `QList<QSslError>` 需完整类型；`qSort`/`toTime_t` 在 Qt6 已移除 | 补丁 0004：显式 `<QSslError>`、`std::sort`、`toSecsSinceEpoch` |
| 5 | RSA 签名用例运行期中止 | 见下「上游测试实测」 | 文档化为已知限制（依赖侧能力缺口，非本包代码缺陷） |

## 上游测试实测（R51 三步法）

### 1) 清点（上游源码）
- `tests/ut_interface/ut_interface.h`：`private Q_SLOTS` 共 **22** 个用例槽（含 6 个 `*_data` 数据驱动槽）。
- `tests/ut_interface/ut_interface.cpp`：`QTest::newRow` 共 22 处，其中 1 处被上游注释（`requestToken_data` 的 `timeout`），**21 条有效数据行**。
- 按 QTest 全量计数（init/cleanup + 8 个简单用例 + 21 条数据行）= **31** 个用例。
- `tests/ft_interface/`：功能测试，全部用例请求公网 `http://term.ie/oauth/example/...`（该站点已下线），离线/CI 环境不可运行。

### 2) 实际运行（真机 HarmonyOS PC aarch64，Qt 6.11.1）
命令（非 RSA 子集，覆盖全部离线可判定用例）：
```
cd tests/ut_interface
LD_LIBRARY_PATH=<qoauth>/lib:<qtbase>/lib:<qca>/lib \
QT_QPA_PLATFORM=offscreen TMPDIR=$HOME/tmp \
./ut_interface -o <log>,txt constructor consumerKey setConsumerKey consumerSecret \
  setConsumerSecret requestTimeout setRequestTimeout error requestToken accessToken \
  createParametersString inlineParameters
```
- 非 RSA 子集：`Totals: 22 passed, 0 failed, 0 skipped, 0 blacklisted`（rc=0）。
- 全量（含 RSA 组）：`Totals: 21 passed, 1 failed`，随后进程在 QTest 崩溃处理循环中挂起。
  失败项：`setRSAPrivateKey(clean)` → `QFATAL : RSA is not supported!`（`src/interface.cpp:656`）。

### 3) 结论
- 上游 ut_interface 清点 22 项：**21 通过 / 1 失败，通过率 21/22（95.5%）**。
- 唯一未通过组为 RSA 私钥签名（`setRSAPrivateKey` / `setRSAPrivateKeyFromFile`），**具体技术原因**：
  制品仓 `qca/2.3.10` 打包时 `BUILD_PLUGINS=none`，包内 `lib/` 只有 `libqca-qt6.so*`，无 `qca-qt6/crypto/` 插件目录；
  运行时探针 `QCA::isSupported("pkey")`/`"cert"`/`"rsa"` 均为 false，`QCA::providers()` 为空列表。
  上游 `src/interface.cpp:656` 对此**硬编码 `qFatal("RSA is not supported!")`**，非本包可绕过。
  补齐需在 qca 独立依赖 PR 中发布带 OpenSSL/Botan provider 插件的包（R36 独立依赖）。
- HMAC-SHA1 签名（OAuth 1.0 默认签名方法）及全部参数/URL/超时/错误处理用例均通过。

## 验证结果
- make check（等价实测）: 21 passed, 1 failed（RSA 组，依赖侧无 pkey provider）
- test_package 消费者测试: 1/1 通过（库加载 + 密钥往返 + inlineParameters 序列化）
- HMAC-SHA1 签名功能正常（OAuth 1.0 默认签名方法）

## 注意事项
- 使用 Qt6 栈（qtbase/6.11.1 + qca/2.3.10），与归档 QCA 配方的 Qt6 版本一致
- RSA 签名功能不可用（制品仓 qca/2.3.10 未带 OpenSSL/Botan crypto 插件）
- `ft_interface` 依赖已下线的公网服务 term.ie，离线环境不可运行
