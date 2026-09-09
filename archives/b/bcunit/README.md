# BCUnit

BCUnit 是 Belledonne Communications 维护的 C 单元测试框架(CUnit 的 fork),为
Linphone/bctoolbox 等项目提供单元测试基础设施。提供框架层(registry、suite、
test、断言)与三种输出接口:Basic(stdout)、Automated(XML 报告)、Console
(交互式),curses 接口上游默认关闭。

- 上游仓库:https://github.com/BelledonneCommunications/bcunit
- 许可证:LGPL-2.0-or-later
- 构建:CMake(无第三方依赖,仅 libc)

## OHOS 适配

当前适配版本:3.0.2(状态与细节见 `3.0.2/manifest.yaml`、`3.0.2/notes.md`)。

要点:

- CMake 4.x 兼容:`cmake_minimum_required` 2.8.12 → 3.5(补丁 0001)
- 上游自测程序 test_bcunit 的链接缺陷修复:`CU_trace_handler` 存储定义从
  Basic/Basic.c 移入框架 Util.c(补丁 0002)
- 上游测试:内部自测 3915 断言全部通过(统计口径与命令见版本级 notes.md §7)
- 消费方式:`#include "BCUnit/BCUnit.h"`,Conan 包名 `bcunit`,库名 `bcunit`
