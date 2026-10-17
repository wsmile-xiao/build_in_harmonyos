# mspdebug 0.25 适配笔记

## 任务信息

- 平台任务号：9011（活动：开源鸿蒙PC专项积分赛-依赖；主号名额超限，经小号中转 relay 认领）
- 分支：feat/mspdebug-0.25；worktree：~/qzy/glm56-mspdebug-0.25
- 上游：https://github.com/dlbeer/mspdebug tag v0.25（GitHub archive sha256 347b5ae5…1503）
- 语言：C（任务登记 cpp 为 SCT 误标，如实更正）；构建系统：内核风格纯 Makefile
- 主理 agent：GLM-56（2026-09-19）

## W0 依赖检查

- 精确版本依赖：libusb-compat/0.1.7（ohpcd 已发布，`conan list` 实测确认）。mspdebug
  链接 libusb-0.1 老 API（usb.h/-lusb，util/usbutil.c、transport/cp210x.c 等 5 处），
  由 libusb-compat 在 libusb/1.x 上提供 0.1 兼容层；libusb/1.0.27 同时显式 require
  以便配方寻址两个包目录。
- WITHOUT_READLINE=1：OHOS 无 readline，Makefile 自带 console 输入回退（ui/input_console.c）。
- -lpthread -ldl：libc 内建。

## W0b 历史经验

- 仓库无 mspdebug 历史归档，首次适配；recipe-search 无同包配方。
- 复用知识库既有模式：E386 getcwd 双层修法（§12.38）、cpp_info 相对路径拼接
  包内绝对路径、CI worker 环境 make 变量显式覆盖（见 gnudos 适配 MKDIR_P 先例）。

## 上游测试清点（R51 证据）

上游 Makefile 无 check/test 目标；无 tests/ 目录、无测试框架。内置 `sim` 为
MSP430 指令级模拟器（主功能，非测试套件）；`C=1` 为 sparse 静态检查开关。
**上游静态测试数 N_static = 0**（如实申报）。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | Makefile 目标清点 |
| 构建系统注册 N_registered | 0 | 无上游测试资产 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（2 断言） | test_package/test.sh |

## 消费者测试设计

`test.sh` 经 conanrun 环境（VirtualRunEnv 解析打包的 libusb-compat/libusb 动态依赖）
真实运行打包产物：

1. `mspdebug --version` 输出含 `MSPDebug version 0.25`，退出码 0。

G2 实测输出：`ALL CONSUMER TESTS PASSED`。

## 源码修改

无补丁（patches: {}）。全部平台适配通过 make 命令行变量与配方级注入完成：

- `WITHOUT_READLINE=1`：上游自带开关，禁用 readline 启用 console 回退。
- `INSTALL=install`：上游硬编码 `INSTALL = /usr/bin/install`（OHOS 无此路径），
  命令行变量覆盖为 PATH 解析。
- `CC`/`CFLAGS`/`MSPDEBUG_LIBS`：hnp clang 与 libusb-compat/libusb 包的
  include/lib 路径显式注入（MSPDEBUG_LIBS = -L<compat> -L<usb1> -lusb -lusb-1.0
  -lpthread -ldl）。

## 路径 B 判断

- 本任务的适配点（Makefile 变量覆盖、libusb-0.1→compat 层）均为已沉淀模式的
  新实例，查重命中既有条目，无新增可复用知识。
- 结论：**纯路径 A，不申报路径 B**。

## 构建环境

- 设备真机（OHOS aarch64），CONAN_HOME=~/tmp/ch/home-glm56-mspdebug；
  profile ci/conan/profiles/ohos-aarch64。
- 源码下载：官方 GitHub archive URL（tag v0.25），sha256 校验；提交前核对 conandata 为官方标量形态（无 file:///ghfast/gh-proxy 注入残留——E017 预下载会写 file:// predl_cache 形态，仅查 gh 系镜像会漏）。

## 验证命令与结果

- `python3 scripts/ohc-run.py conan-verify mspdebug 0.25`：Verdict PASS（G0-G4）。
- 消费者测试实测输出：`ALL CONSUMER TESTS PASSED`。

## 已知限制

- TI USB FET 固件文件（*.fw.ihex）随包装入 `<prefix>/lib/mspdebug/`，而二进制内
  烧录的搜索路径为构建期 LIB_DIR；真实 FET 硬件调试需按文档放置固件，不影响
  编译链接与 --version/gdb/sim 功能。
- USB 硬件调试功能需真实 MSP430 适配器与 USB host 权限，CI 环境不可达，不在
  断言范围。

## finish 收尾块

- conan-verify：PASS（G0-G4）；W3 本地 CI：见 reports/w3-local-ci.log；W4 独立审计：提交前完成（P0/P1 清零）。
- 测试数字同源核对：notes.md = MANIFEST.yml = PR 正文 = result.json（N_static=0，N_executed=0，N_consumer=1，N_assertion=2）。
- 提交方式：精确 add archives/m/mspdebug/（commands.json 在软件级目录）。
---

**编译结束**: 2026-09-19 05:53
**最终状态**: built
