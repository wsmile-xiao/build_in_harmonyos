# BCUnit

BCUnit 是 Belledonne Communications 维护的 C 单元测试框架(CUnit 的 fork),为
Linphone/bctoolbox 等项目提供单元测试基础设施。提供框架层(registry、suite、
test、断言)与三种输出接口:Basic(stdout)、Automated(XML 报告)、Console
(交互式),curses 接口上游默认关闭。

- 上游仓库:https://github.com/BelledonneCommunications/bcunit
- 许可证:LGPL-2.0-or-later
- 构建:CMake(无第三方依赖,仅 libc)

## 已适配版本

| 版本 | 内容 | 状态 | 细节 |
|------|------|------|------|
| 3.0.2 | tag 3.0.2(2017 内容) | built | `3.0.2/manifest.yaml`、`3.0.2/notes.md` |
| 5.3.113 | tag 5.3.113(linphone-sdk 5.3 线内容) | built | `5.3.113/manifest.yaml`、`5.3.113/notes.md` |

两个 tag 的**文件内声明的项目版本号都是 "3.0.2"**(BC 把 linphone-sdk 锁步快照
打在 bcunit 仓上),选版本要按内容时代:5.3.113 才含 `CU_Suite.pUserData`、
`CU_automated_enable_partial_junit` 等 5.3 线 API,bctoolbox 5.3.115 的 tester
依赖这些 API。

## OHOS 适配要点

- **5.3.113**:框架头文件目录被改成只挂在 `bcunit` 目标上,`bcunit_test` 失去
  Headers 路径,`-DENABLE_BCUNIT_TEST=ON` 编译即错;补丁 0001 给该目标补回
  源码/生成 Headers 目录。
- **3.0.2**:CMake 4.x 移除对 `cmake_minimum_required(<3.5)` 的兼容,上游
  2017 年代声明 2.8.12;补丁 0001 提升到 3.5。
- **两版本同型**:`CU_trace_handler` 存储定义放在接口文件 `Basic/Basic.c`,而
  `bcunit_test` 静态库只含框架源文件,上游自测程序链接报
  `undefined symbol: CU_trace_handler`;补丁把存储定义移入 `Framework/Util.c`。
- **上游缺陷(不改上游)**:5.3.113 的 `CU_automated_run_tests()` 同进程二次
  调用必然崩溃(原始源码同样复现),消费侧需分进程调用。
- 上游测试:内部自测 3915 断言全部通过(统计口径与命令见各版本 notes.md §7)。
- 消费方式:`#include "BCUnit/BCUnit.h"`,Conan 包名 `bcunit`,库名 `bcunit`
  (默认静态 `libbcunit.a`;`shared=True` 得到 `libbcunit.so`)。
