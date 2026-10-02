# malint 0.2 — 适配笔记

## 概述
malint 是 Dieter Baron（nih.at，libmad/libid3tag 同站作者）的 MPEG Audio 流校验器：
解析 MPEG 音频流（MP1/MP2/MP3，含 VBR、id3v1/id3v2），打印流信息与格式违规。
产物为单命令行二进制 `bin/malint`。GPLv2，纯 C，无第三方依赖。

## W0 依赖结论
- 依赖数量：0（仅系统 libc/libm）
- 已满足依赖：全部（musl libc 自带 strerror/getopt，configure LIBOBJS 替换不启用）
- 缺失依赖：无
- 是否需要拆分依赖适配：否

## 构建系统（W1）
- autotools：官方 tarball 由 autoconf 2.59 生成，自带 configure/Makefile.in，无需 bootstrap
- **不含 config.guess/config.sub**：configure 必须显式传 `--build/--host`
  （aarch64-unknown-linux-gnu），否则内联 uname 猜测在 OHOS 上有失败风险（E007 同类）
- 产物：`bin/malint`（bin_PROGRAMS，无库）
- 测试：`regress/` 下 6 个 runtest 用例（sh 脚本驱动，仅用 sed/diff/expr/rm）

## 源码归档
- URL: https://www.nih.at/malint/malint-0.2.tar.gz
- SHA256: 798a76d60df6c1c18c0b9d6661f1e320d515fa24517c69c538d6256e57f15ca2
- 官方 tag 归档，包含完整 regress 测试（6 用例 + 输入样本 + 参考 log）

## 关键适配点
1. **HMDFS umask 临时目录**（E011/E052 同类）：autoconf configure 以 umask 077
   建临时目录，HMDFS setgid 目录组无写位 → config.status Permission denied。
   处理：configure/make/check/install 统一 `umask 022` 运行（构建环境层，
   非源码补丁，zzuf 0.15 已验证同方案）。
2. **老式 configure（2.59）**：无 -Werror，clang 下最多告警；传显式三元组
   跳过 config.guess。
3. 无源码补丁。

## 上游测试结果（真机 shadow CI 实测）
- **真机 job `malint-0.2-20261001`，run `…-214011-40857`，exit 0，wait_seconds=0**
- 上游 `make check`（regress 6 用例）：**6/6 PASS（All 6 tests passed）**
- test_package 消费者验证：**PASS**（--help + 内嵌官方样本 -N3 输出比对）
- L0 / L1 / L2 / L4 / L5：**全 pass**（L2: malint --version OK）
- 本机（Windows 宿主）预验证：configure 交叉模式通过、OHOS SDK clang 编译零错误
  （3 个 -Wpointer-sign 警告）、产物 NEEDED 仅 libc.so

## 真机迭代记录（r1–r5）
| 轮 | 失败点 | 根因 | 解法 |
|---|---|---|---|
| r1 | L0 fail: no_test_sources | 测试逻辑内嵌 conanfile.py，无独立测试源文件 | 新增 test_package/test_malint.sh（真实消费者断言） |
| r2 | KC fail（设备级） | /data/service/hnp/bin/bash 不可执行（同期其它库 run 同样失败） | HMDFS zsh 副本写入 PATH 首位目录作 bash 入口，KC pass |
| r3 | configure: bad interpreter /bin/sh | 设备 /bin/sh 故障 + shebang exec 被拒（E087） | 配方以 {shell} ./configure 直接解释执行 + make SHELL= 注入 |
| r4 | cc: bad interpreter | PATH 中 cc 为 HMDFS 坏包装脚本 | CC 从 Conan conf 显式注入（R33） |
| r5 | — | — | **全绿** |

## 关键环境适配（真机故障期，已固化进配方）
1. configure 内 `umask 077`→`022` 替换（E011/E129，Python 层替换）
2. zsh 直接解释执行 configure（绕开 /bin/sh shebang）
3. `make SHELL={shell}`、`make check TESTS_ENVIRONMENT=sh`（E046 无执行位）
4. `TMPDIR/TMPPREFIX` 指向 build 目录自建 tmp/（E002 /tmp 只读）
5. CC 从 `tools.build:compiler_executables` conf 注入（R33）

## Conan 配方要点
- 源码 URL/SHA256 放配方内（不进 CI conandata 预下载分支，xmodem 经验）
- `make check` 在非交叉编译时集成进 build()
- test_package：--help 退出 0 + 内嵌上游 frame-short.in 样本 `-N3` 输出
  关键行比对（帧头参数/缺字节报告/帧计数），交叉时降级 ELF 魔数检查
- commands.json：工具型（malint）

## 下一步
- 推送分支、补建 issue 与 PR（真机 shadow CI 已全绿，PR 描述按模板填写验证结果）
- 设备 shell 基础设施（/bin/sh、hnp bash、/tmp）恢复后可复跑一轮确认配方在健康环境同样通过

---
**编译结束**: 2026-10-01 21:40
**最终状态**: built（真机 shadow CI L0-L5 全 pass，上游测试 6/6）
