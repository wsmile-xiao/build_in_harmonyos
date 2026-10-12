# schroot

`schroot` 允许用户在受控的 chroot 环境中执行命令，是 Debian/Ubuntu 上构建与调试
工具链的常用会话管理程序。上游仓库为 Codeberg 上的
[`shelter/reschroot`](https://codeberg.org/shelter/reschroot)（Debian 上游源码的
持续维护镜像）。

## 产物

| 路径 | 内容 |
|------|------|
| `bin/schroot` | 主程序（会话管理，`--info`/`--list`/`--chroot`/`--session-name` 等）|
| `libexec/schroot/schroot-mount` | 挂载 helper（按 chroot 定义挂载文件系统）|
| `libexec/schroot/schroot-listmounts` | 挂载点列举 helper |
| `lib/libsbuild.a` | `sbuild` 静态库（chroot 定义解析、配置读取、会话/认证后端）|
| `include/sbuild/**` | 公共头（含 configure 生成的 `sbuild-config.h`）|
| `etc/schroot/**` | 配置与 setup 脚本（`schroot.conf`、`default/`、`buildd/`、`setup.d/` 等）|

## 依赖（制品仓 `ohpcd`）

`boost/1.84.0`（headers + filesystem/iostreams/program_options/regex）、
`linux-pam/1.7.2`、`libuuid/2.40.4`、`gettext/0.22.5.1`；
开启上游测试（`with_upstream_tests`，默认开）时另需 `cppunit/1.15.1`。

## 适配要点（HarmonyOS PC / aarch64-linux-ohos）

- CMake 无 `HarmonyOS` 平台模块，配方以 `CMAKE_SYSTEM_NAME=Linux` + OHOS clang/musl
  工具链构建（ABI 兼容），并按需给出交叉编译下不可靠的探测结果（uuid/pam 头与函数）。
- 安装期 RPATH 重链产物在 HarmonyOS 上 `execve` 返回 `EPERM`：配方令安装期 RPATH 与
  构建期一致（跳过重链），`package()` 再用构建树产物覆盖安装副本。
- 上游 `install` 不含 configure 生成的 `sbuild-config.h`，而公共头会引用它，
  `package()` 一并装入。
- OHOS 侧无真实 `libintl`（`libintl.h` 为空壳）：NLS 关闭，运行期与实际调用所需的
  gettext 能力由制品仓 `gettext` 包提供（`-lintl`），三枚补丁补 `<libintl.h>` 包含。
- 快照/回环特性（LVM/ZFS/Btrfs/loopback/personality）在本平台不可用，配方显式关闭。

## 测试

- 上游：CMake/CTest 共 8 个套件，其中 `sbuild-chroot-config` 的 testdata 要求 root
  属主（上游安全设计，非特权沙箱无法满足），以上游等价方式自调 `ctest` 并
  `-E sbuild-chroot-config` 运行其余 **7 套件：100% 通过，0 失败**。
- 鸿蒙适配补全：`test_package/` 提供**完整消费者用例**（CMake 工程链接包内
  `libsbuild.a`，调用 `sbuild::basename/dirname/normalname/is_absname/unique_identifier`
  等公共 API 并断言 HarmonyOS 运行时特征），外加 `bin/schroot` 与 helper 的
  CLI/布局检查，见 `1.6.13/reports/test-report.md`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.6.13 | built | 首次适配（7 枚可移植性补丁）|
