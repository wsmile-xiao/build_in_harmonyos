# DRAFT-gnustep-gui-gnustep-env-closure - GNUstep GUI 需要完整的 GNUstep Make/Base 环境闭包

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-29
> **Source event**: gnustep-gui 0.32.0 HarmonyOS PC adaptation, PR #7095

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

GNUstep GUI 不是普通 C 库。它的构建和测试都依赖 GNUstep Make 提供的 makefiles、
GNUstep Base 提供的头文件/库/工具，以及一致的 GNUstep 安装域。

在 HarmonyOS PC 的 Conan 适配里，如果只传播了部分环境变量，常见结果是：

- `configure` 还能找到源码树，但后续生成的 GNUstep 规则找不到 Makefiles；
- AppKit 代码能进入编译阶段，但 `AppKit/AppKit.h` 或 base 头文件缺失；
- `test_package` 运行时看见了错误的 GNUstep 域或库搜索路径。

## 根因

`gnustep-make`、`gnustep-base` 和 `gnustep-gui` 不是松散的独立包，而是一条需要
同时成立的环境闭包：

1. `PATH` 必须能找到 `gnustep-make` 的辅助工具；
2. `GNUSTEP_MAKEFILES` 必须指向 `share/GNUstep/Makefiles`；
3. `GNUSTEP_CONFIG_FILE` 和 `GNUSTEP_SYSTEM_ROOT` 必须来自同一包前缀；
4. `CPPFLAGS`、`LDFLAGS`、`LD_LIBRARY_PATH` 必须同时覆盖 base 的头文件和库目录。

只补其中一项，往往会把失败从 configure 延后到 build 或 test_package。

## 推荐方法

在 recipe 中把同一套包前缀环境同时用于 configure、build 和测试：

```sh
export PATH="<gnustep-make>/bin:<gnustep-base>/Tools:$PATH"
export GNUSTEP_MAKEFILES="<gnustep-make>/share/GNUstep/Makefiles"
export GNUSTEP_SYSTEM_ROOT="<gnustep-base>"
export GNUSTEP_CONFIG_FILE="<gnustep-base>/GNUstep.conf"
export GNUSTEP_INSTALLATION_DOMAIN=SYSTEM
export CPPFLAGS="-I<gnustep-base>/Library/Headers $CPPFLAGS"
export LDFLAGS="-L<gnustep-base>/Library/Libraries $LDFLAGS"
export LD_LIBRARY_PATH="<gnustep-base>/Library/Libraries:$LD_LIBRARY_PATH"
```

如果 recipe 已经像本库一样把这段逻辑封装进 helper，那么 build 和 test_package
都要复用同一 helper，而不是在单个阶段手工拼环境。

## 与已有知识的差异

- E011、E052 处理的是 HMDFS / mktemp 之类的通用构建环境问题，不涉及 GNUstep 的
  安装域和 makefiles 约束。
- 本草稿补充的是 GNUstep 体系的闭环约束：构建工具、基础库、安装域和消费者测试
  必须同源，否则 AppKit 适配会在后续阶段才暴露缺件。

## 禁止做法

- 不要依赖宿主机的 `/usr/share/GNUstep`。
- 不要只给 `test_package` 补环境而让 build 阶段走另一套前缀。
- 不要把 `GNUSTEP_INSTALLATION_DOMAIN` 留空后再靠宿主默认值碰运气。

## 证据来源

- `archives/g/gnustep-gui/0.32.0/conanfile.py`
- `archives/g/gnustep-gui/0.32.0/test_package/conanfile.py`
- `archives/g/gnustep-gui/0.32.0/test_package/CMakeLists.txt`
