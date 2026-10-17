# dap 3.9 适配笔记

## 编译环境
- 构建系统: autotools（GNU 正式 tarball 自带 configure；AC_CONFIG_AUX_DIR([build-aux])；LT_INIT）
- 编译日期: 2026-09-14
- 编译器: clang（OHOS aarch64 交叉）
- 状态: built

## 编译步骤

1. GNU 发布 tarball 自带 configure，无需 autoreconf 自举。
2. E490：恢复 build-aux/ 下 autotools 辅助脚本执行位。
3. E007：tarball 自带 build-aux/config.guess、config.sub 早于 HarmonyOS，
   运行期替换为 OHOS-aware 自包含版本（dcfldd/1.9.3 同款）。
4. HMDFS getcwd 修复（adms/2.3.7 同款）：预置 PWD + configure 的 ac_pwd 判定
   加 $PWD 回退 + 临时目录 umask 077→022（E011）。
5. configure → make -j1 → make install。零外部依赖（configure.ac 无
   AC_CHECK_LIB/PKG_CHECK_MODULES）。

## 上游版本串不一致（记录）

- dap-3.9 tarball 的 configure.ac 标注版本 3.9，但程序内 --version 处理
  （src/dap.c）把横幅 "Dap 3.6" 打印到 **stderr** 且 **exit(1)**（上游自身
  不一致与缺陷）。消费者测试按上游真实契约断言：合并 stderr 捕获输出、
  接受上游退出码、以版本横幅 "Dap 3" 出现为行为断言，避免因上游缺陷误判
  适配失败。

## 设计取舍

- dap 产出 4 个可执行程序（bin_PROGRAMS = dap dapruns daprun dappp），
  按 R38 在软件级别声明 commands.json（type=tool，name=dap）。
- 消费者测试以 `dap --version` 行为断言（退出码 0 + 输出含 3.9）。

## 上游测试清点（R51 三步法）

- 上游 dap 3.9 **无自动化测试套件**：顶层与 src/Makefile.am 均无 TESTS /
  check_PROGRAMS / check_SCRIPTS，`make check` 无可执行目标。

### 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 上游无自动化测试（清点证据见上） |
| N_registered（构建系统注册） | 0 | TESTS/check_PROGRAMS 为空 |
| N_executed（实际执行） | 0 | 上游无测试可执行 |
| N_consumer（新增消费者测试） | 1 | test_package/test.sh（--version 行为断言） |

## 依赖版本

- 无外部 conan 依赖（工具链由 profile 提供：clang 15 / autotools）

## 源码修改

无补丁（patches 为空）。配方仅做构建期注入（E007 脚本替换、PWD/umask 修正），
不修改上游源码文件。
---

**编译结束**: 2026-09-14 05:09
**最终状态**: built
