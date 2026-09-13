# cppp 2.9 适配笔记

## 编译环境
- 构建系统: 纯 Makefile（无 configure 脚本）
- 编译日期: 2026-09-09
- 编译器: clang（来自 Conan conf tools.build:compiler_executables）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built

## 编译步骤
1. 下载源码 tarball（https://www.muppetlabs.com/~breadbox/pub/software/cppp-2.9.tar.gz）
2. 解压（strip_root=True，目录名为 cppp-2.9）
3. make CC="clang" -j1（in-source build）
4. ./tests/testall（运行上游测试套件）
5. 打包：cppp → bin/，cppp.1 → share/man/man1/，COPYING → licenses/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本，直接用 make | cppp 是极简 Makefile 项目 | 直接调用 make，无需 AutotoolsToolchain |
| 2 | CI Worker 上 ${CC} 为空（R33） | 构建环境不保证 CC 环境变量 | 从 self.conf 读取 compiler |
| 3 | upstream testall 需要 bash | OHOS toybox sh 兼容 bash 子集 | testall 使用 POSIX 语法，可在 sh 下运行；若需 bash 则走 CONFIG_SHELL |

## 依赖版本
无外部 Conan 依赖。

## 产物
- bin/cppp（CLI 工具）
- share/man/man1/cppp.1
- licenses/COPYING

## 验证结果
- 本地 x86_64 Linux（gcc）：编译成功，tests/testall 全部通过（EXIT=0）
- HarmonyOS aarch64 真机：`conan create` 全流程通过（compile → upstream test → test_package 均 exit 0）

## 上游测试说明
- 上游无 gtest/ctest/py.test 等框架，使用 bash 脚本 tests/testall 驱动
- tests/testall 共 11 个顶层测试组（misctests + goodparsing ×4(basic/good/lines/phases) + badparsing ×1 + trigraphtest ×1 + fulltest ×3(numeric×1)）
- 缺陷：上游 fail() 的 `exit 1` 被注释掉，脚本永远 exit 0；且默认 PROG=./cppp 需在源码根运行
- 适配方案：build() 中传 `./cppp` 参数、捕获完整输出、按 "Unit test failure:" 计数，产出 HMBS_UPSTREAM_TEST_RESULT 标记
- 计数已用「故意换成 exit 1 的桩二进制」证伪：桩跑出 151 条失败线 → 真实验证 harness 能抓到失败，非静默跳过
- 所有检查点在 HarmonyOS aarch64 上均可通过

## HMBS 硬门禁标记
- build()：`HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"make-runtests","command":"bash ./tests/testall ./cppp","discovered":11,"executed":11,"passed":11,"failed":0,"skipped":0}`
- test_package：`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":4,"passedCount":4}`
- test.sh 产出 4 个真实 PASS/FAIL 行（--version / --help / -DFOO / -UFOO）
- 真机实跑 CREATE_EXIT=0

## HarmonyOS aarch64 实跑命令
```sh
ssh -p 20222 ohos@c1.sermc.net
cd ~/preflight/agent-runs/cppp-2.9
CONAN_HOME=$HOME/.conan2 conan create . cppp/2.9@ --build=missing
```
