# E6340-draft-A7F3：Qt Declarative 扩展插件测试需要安装态 QML 测试数据

> 状态：DRAFT
> 来源：`qtdeclarative` 6.11.1.1 适配 PR #7677
> 贡献者：AtomCode
> 更新：2026-09-08

## 现象

在 HarmonyOS PC 真机的 Conan 构建树中直接运行
`tst_qqmlextensionplugin` 时，测试进程可能终止于：

```text
QFATAL ... iidCheck() ASSERT failure
Test data requested, but no testdata available.
```

诊断时还能看到 `QLibraryInfo::QmlImportsPath` 指向构建依赖的 QML 目录，
例如 qtbase 包下的 `qml` 路径，而不是已经安装并带有
qtdeclarative 测试资源的安装前缀。

## 根因

`tst_qqmlextensionplugin` 不只是运行 C++ 内置断言，它还需要 QML import、
插件和测试数据。构建树尚未完成完整安装时，`QmlImportsPath` 可能可解析，
但目录内没有该测试所请求的数据行。QTest 因此报告没有可用 testdata 并
以失败状态退出。

这属于测试前置条件和路径布局问题。它不能被解释为所有
Qt Declarative 上游测试失败，也不能通过把目标从 CTest 列表中删除后仍
声称完整上游测试已经通过来解决。

## 历史证据与当前 CI 口径

早期真机验证曾选择了不依赖安装态 QML 测试数据的八个稳定目标：

```text
tst_registrationmacros
tst_qjsprimitivevalue
tst_qjsvalueiterator
tst_qqmlfile
tst_qjsonbinding
tst_linebylinelex
tst_qqmlerror
tst_qjsengine
```

在设备 `10.62.134.118:2222` 上，八个目标均已实际执行并通过：

```text
Total Tests: 8
100% tests passed, 0 tests failed out of 8
Total Test time (real) = 18.27 sec
```

这组 `8/8` 仅是历史真机证据，不是当前 CI 的上游测试分母或通过数。
当前 CI 构建完整 CMake 图，并从同一构建树动态读取 `ctest -N` 注册表后
执行不带 `-R` 过滤的全部 CTest。若测试需要安装态 QML import、插件或
testdata，recipe 必须先完成对应安装/运行时布局；任一构建或运行失败都
直接使 Conan/CI 失败，不得将未执行项折算为通过。

## 文件级逐项审计

为满足 rule4 的“逐项技术原因”要求，已从上游 Qt Declarative
`v6.11.1`（commit `a02bed441965ee1f18f856352c7d5ee5ba35d795`）重新派生
`tests/auto/` 文件清单。清单共 `10372` 行；其中曾被早期真机子集覆盖的
8 个目标源文件与其余文件都只作为文件级追踪证据，不能作为当前运行时
CTest 分母或通过数。每行保留精确上游路径，并标记第一适用门控和技术原因。

权威文件：

- `archives/q/qtdeclarative/6.11.1.1/test_package/UPSTREAM_TEST_INVENTORY.md`
- `archives/q/qtdeclarative/6.11.1.1/test_package/UPSTREAM_TEST_MATRIX.md`

这份文件级清单不把 CMakeLists、fixture、QML/JS 数据文件或工具辅助文件
冒充独立通过的可执行测试，也不把未执行项计入分子；每行只回答该计数项为何
在当前 HarmonyOS PC package-only 测试契约下未执行/未通过。

## 推荐方案

当前构建和交付流程中，应使用完整动态 CTest 注册表：

1. 先用 `ctest -N --no-tests=error` 列出同一构建树的全部注册目标。
2. 用 `ctest --output-on-failure --no-tests=error` 实际运行全部注册目标。
3. 记录动态注册数、实际运行结果和失败目标；测试数量不从源文件清单推断。
4. 若某目标依赖安装态资源，先完成真实安装和运行时路径配置；不能以创建空目录或静默跳过代替。

如果发布要求覆盖该目标，另一条合规路径是先执行：

```sh
cmake --install "${BUILD_DIR}" --prefix "${INSTALL_PREFIX}"
ctest --test-dir "${BUILD_DIR}" --output-on-failure \
  -R "^tst_qqmlextensionplugin$"
```

安装态测试必须使用与 Qt Declarative 对应的 QML import、插件和 testdata，
不能只创建空目录或复用 qtbase 的无关 `qml` 目录。

## 查重与关系

- `DRAFT-upstream-test-runtime-libs` 讨论测试运行期动态库可达性，属于
  运行环境问题；本草稿讨论 QML testdata 和安装态路径，阶段不同，互补。
- `E324` 讨论静态库上游测试的 CMake target identity，不覆盖 QML 测试
  数据前置条件。
- 当前未发现已有 `qtdeclarative` 或 `QmlImportsPath` 专题草稿，本条目
  保留了具体目标、错误签名和安装态前置条件；当前 CI 使用完整动态
  CTest，不再复用八目标过滤命令。

## 禁止做法

- 不要把 `0/0`、未启动或因前置条件缺失排除的目标写成通过。
- 不要只在主机或 Linux 构建树中运行测试，再作为 HarmonyOS PC 真机
  证据。
- 不要用空的 QML 目录冒充安装态 testdata。
- 不要为了满足“全量”字样删除失败日志或隐去 `N` 到 `N'` 的缩减理由。

## 来源与边界

本草稿对应 PR #7677 的 `qtdeclarative` 6.11.1.1 适配，只对
`tst_qqmlextensionplugin` 在当前 Conan build-tree 的失败模式提供证据。
CI 在运行完整动态 CTest 前必须补齐对应安装态 QML 资源，并以动态注册数
和真实运行结果更新统计；不能沿用历史八目标子集结论或将其扩展为全量通过。
