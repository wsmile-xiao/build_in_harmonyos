# schedtool 1.3.0 适配记录

日期：2026-09-23，2026-09-24 复核。状态：OHOS 真机原生构建及 Conan 从上游源码创建包均成功，直接与包内功能测试各 18/18、103 断言；正式 W3 本地 CI 已通过，完整 `finish` 后续收尾、官方 CI 和 PR 尚未完成。

## 源码与依赖

- 官方 tag 源码：<https://github.com/freequaos/schedtool/archive/refs/tags/schedtool-1.3.0.tar.gz>；SHA256：`6c3388771849c96c4c3d4405096a3e147709ff48eb5f53adb8354735cf110500`。
- 官方 tag 归档与先前使用的 Debian `.orig` 归档（SHA256 `6628e4e805fab9c72b2daeb300c599d3de581f48eb21ce6caee3ae530b18450e`）在去掉顶层目录名后，15 个相对文件逐字节相同；两种归档本身的哈希不同。改用官方 URL 是为符合源码来源门禁，不改变被编译的源码内容。
- 源码 `VERSION` 为 1.3.0，固定 tag 与校验和，不使用会变化的 master。
- 无第三方库依赖。包含标准/POSIX 头与 `sched.h`，链接系统 C 运行库。

## 改动

1. `0001-schedtool-c-portability.patch`：修复 `set_process` 将字符串指针和整数放入同一个条件表达式再传给变参格式化函数的问题；分支分别匹配 `%s` 和 `%d`。同时零初始化 `sched_param`、移除已有 `<errno.h>` 后的冗余声明。Linux GCC 严格警告构建复现了条件表达式错误；尚无目标 Clang 失败证据，不能称为鸿蒙特有缺陷。
2. `0002-standard-help-version-options.patch`：添加 `--help`、`--version` 和原先 switch 有分支但 getopt 未接受的 `-V`，供标准 CLI 检查与上游 L2 烟雾验证使用，保留原短选项。新增选项均有输出断言。
3. 原生 Make 配方显式传入 Conan 配置中的 C 编译器和目标 shell，构建 PIE 并设置 RELRO；不执行安装到系统目录。打包 binary、man page、文档和 GPL 许可证。

## 测试来源与已知限制

原始归档仅有 15 个文件，Makefile 无 `check`/`test` 目标，没有 tests 目录。`make -n check` 返回 2（No rule to make target），这是测试清点证据，不是通过或平台失败。

补充 17 个功能用例和 1 个前提检查，成功路径共 103 次断言。涵盖参数、查询、执行参数和退出码、nice、自进程 CPU 亲和性和两条错误格式化路径；由 Python `os.*` 独立读回结果，且只操作新启动进程。查询失败可能仍返回零，故同时检查输出字段和真实值。`test_package/MANIFEST.yml` 标明无上游测试和补充测试范围。

H1 首轮十六进制用例以 CPU19 (`0x80000`) 为目标时失败。对照探针显示原生 Python、schedtool 列表及十六进制输入请求 CPU19 都会读回更宽的 CPU 集合，而 `0x3` 能精确读回 CPU0、1；这不能归咎于十六进制解析器。现改为用基线前两个 CPU 组成十六进制掩码，保留独立读回精确匹配的断言。此轮自动测试不覆盖高 CPU 位的精确设置；H1 高位异常及其原始证据保留在工作区验证报告，不能把它说成已修复。

Linux x86_64 GCC 辅助构建、Conan 2.29.1 的干净 `conan create` 和打包后的全部 18 项检查已通过。H1 的 OHOS aarch64 原生构建和使用隔离 profile/cache 的 Conan 源码构建也已通过；两者功能测试各 18/18、103 断言，详情见 `reports/`。以 `/usr/bin/true` 替换被测程序的 Linux 反向控制使全部 17 个功能用例失败，确认不是仅判断退出码。OHOS 缺少接口、Python 未暴露相应 API、权限失败和实际读回错误都会作为失败记录，不以成功跳过掩盖。

`SCHED_ISO=4` 是历史扩展；上游 `SCHED_IDLEPRIO=5` 与当前 OpenHarmony musl 的 `SCHED_IDLE=5` 名称不同，实际语义和支持度以真机头文件/内核为准。保留历史名称，未通过假实现禁用 affinity 或调度功能。FIFO/RR/ISO 等策略修改及提权不在本次常规测试范围内。`-v -e` 在 exec 前未刷新 stdout 是已有上游行为；测试使用执行后的独立 probe。

## 后续验收

H1 单文件运行包已回传源码校验、原始与补丁构建日志、18 项结果、编译器 target/头文件宏、ELF 与 Conan create 的原始日志，且已核对传输哈希。后续隔离完整框架 009 的正式 `finish` 内执行 W3：`setup.sh` 和完整 `build_and_test.sh` 均返回 0，包内 18/18、103 断言，工具生成的 `.ci-result.json` 完整性哈希与日志 SHA256 已独立核对。W3 是本地模拟，官方 CI、W4 和上游合入尚无通过结果；不能手写状态回执或虚构测试通过数。

2026-09-24 框架诊断 007 在隔离 checkout 中再次从源码构建，包内 18/18、103 断言，同轮包内 AArch64/musl ELF 已回收；但框架验证器 G4 报“无法找到程序包 ID”，L2/L4/L5 因无 cache 路径而跳过，报告标题的 PASS 不代表这些门禁真实执行。独立 CI 预跑最后可见 G0e，后经定向终止退出 -15，无法据缓冲输出定位停点或判断自然结局。007 不是正式 `finish`/W3。009 的独立 W3 内 L2/L4/L5 实际执行并通过，但同轮 `conan-verify` 的 G4/L2/L4/L5 语义缺口仍在；完整 `finish` 在 W3 后因本地 packaging/staging 就绪与共享知识图谱、SUMMARY 问题退出 1。`built` 表示已有真机构建与测试证据，不表示已发布。

## 最终状态（本地构建阶段）

版本 manifest 为 `built`：真机原生与 Conan 源码构建、包内功能测试和 W3 本地 CI 均已有真实通过证据。上游 PR、远端 CI、维护者审核与发布状态仍待后续实际结果。
