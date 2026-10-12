# mptp 0.2.5 HarmonyOS PC

任务 #8983；基础库活动；领取账号 2501_91199785；团队“诶，云朵”。
分支 feat/mptp-0.2.5；同步 main b644cbf8ed30f647dff8a29240c8b7738edd5e65。

官方发行归档包含完整 generated parser/lexer，configure 却硬要求 Flex/Bison；
目标没有这两个开发工具。本配方以 CMake 编译全部 22 个生产 C 文件，保留
算法、rooted/unrooted 解析、MCMC、SVG、手册和补全，不生成替代 parser。
使用的 PACKAGE/PACKAGE_VERSION 原本来自 config.h；源码没有使用其他 HAVE_* 宏。
修正了架构/系统品牌显示的 AArch64/OHOS 宏分支，未修改算法。

上游 0.2.5 发布记录已经移除 GSL，运行依赖只需 libc/libm。
当前官方归档的 Makefile.am 无 TESTS/check_PROGRAMS 或 tests 目录：上游 N=0。
新增消费者测试 8/8，通过真实安装的 Conan bin/mptp 执行；不是上游用例。

本机证据位于本任务目录 w3-mptp-20261011T071000Z 与
w3-mptp-finish-20261011T074000Z。两者都完成独立 exact-byte transfer/readback、
唯一 launch、12 phase 回执及 release/postrelease。第二事务执行原始
FinishPipeline.step35_local_ci()，setup/build_and_test RC0；校验结果由 helper 生成。

当前仅验证成功，未 commit/push/创建 Issue 或 PR，未发布到制品仓。
提交前仍需完整 finish 收尾、HD1–HD4 重判、Issue 关联和 Pre-PR v2 合同。
