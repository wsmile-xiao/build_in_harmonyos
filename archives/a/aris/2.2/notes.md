# aris 2.2 适配笔记

## 编译环境
- 构建系统: autotools（GNU 正式 tarball 自带 configure；AC_CONFIG_AUX_DIR([build-aux])）
- 编译日期: 2026-09-14
- 编译器: clang（OHOS aarch64 交叉）
- 状态: built

## 编译步骤

1. GNU 发布 tarball 自带 configure，无需 autoreconf 自举。
2. E490：恢复 build-aux/ 下 autotools 辅助脚本执行位（HMDFS 适配路径可能丢执行位）。
3. E007：tarball 自带的 build-aux/config.guess、config.sub 早于 HarmonyOS，
   运行期替换为 OHOS-aware 自包含版本（dcfldd/1.9.3 同款）。
4. HMDFS getcwd 修复（adms/2.3.7 同款）：预置 PWD 环境变量 + configure 的 ac_pwd
   判定加 $PWD 回退 + 临时目录 umask 077→022（E011）。
5. configure（PKG_CHECK_MODULES 经 PkgConfigDeps 提供的 gtk+-3.0.pc /
   libxml-2.0.pc 解析）→ make -j1 → make install。

## 依赖版本

- gtk/3.24.43（pkg_config_name=gtk+-3.0，ayatana-ido/0.10.4-v2 同款钉版）
- libxml2/2.15.3.1（制品仓已发布，pkg_config_name=libxml-2.0）

## 设计取舍

- aris 为 GTK3 GUI 应用（bin_PROGRAMS=aris），按 R38 在软件级别声明
  commands.json（type=tool）。
- 消费者测试以 `aris --version` 行为断言（退出码 0 + 输出含 2.2），
  版本参数在 GTK 初始化前处理，无需显示服务，可无头运行。

## 上游测试清点（R51 三步法）

- 上游 aris 2.2 **无自动化测试套件**：顶层与 src/Makefile.am 均无 TESTS /
  check_PROGRAMS / check_SCRIPTS；src/*.c 无 TEST_CASE / ASSERT_ 测试宏。

### 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 上游无自动化测试（清点证据见上） |
| N_registered（构建系统注册） | 0 | TESTS/check_PROGRAMS 为空 |
| N_executed（实际执行） | 0 | 上游无测试可执行 |
| N_consumer（新增消费者测试） | 1 | test_package/test.sh（--version 行为断言 2 处） |

## 源码修改

无补丁（patches 为空）。配方仅做构建期注入（E007 脚本替换、PWD/umask 修正），
不修改上游源码文件。
---

**编译结束**: 2026-09-14 04:10
**最终状态**: built
