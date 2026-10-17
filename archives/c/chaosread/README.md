# chaosread

chaosread 是 Keith Packard（X Window / Cairo / Pixman 作者）开发的小型
USB 工具，用于从 ChaosKey 硬件设备读取原始随机数（真随机熵源）。ChaosKey
是一个 USB 加密狗，Linux 内核驱动把它当作熵源使用，chaosread 则可以绕
过内核直接读 raw noise endpoint，常被用来审计熵源质量或做硬件 RNG 自举
测试。

## 描述

chaosread 通过 libusb-1.0 与 ChaosKey USB 设备通信，发送 GET_NOISE 控制
请求并解析返回的熵样本。支持 `--version` 输出版本、 `--help` 输出选项列表
（上游不带任何测试，conan 适配以这两条 CLI 输出作为 L2 smoke 验证）。

## 已编译版本

- 1.1 (2026-09-07, OHOS 适配版本)

## 特性

- 单一 C 源文件（~322 行），编译产物为单可执行文件
- 跨平台编译（Linux / OHOS aarch64 验证通过）
- 依赖 libusb-1.0（conan 适配在 recipe 内用 `libusb_stub/` 100 行 C stub 替代）
- Keith Packard 个人项目（git.keithp.com），无官方签名 tarball；适配
  从 Debian primary sourcefiles 镜像取 SHA256 锁定的 orig 包

## 使用方法

```bash
# 输出版本
chaosread --version
# 期望输出包含: chaosread 1.1

# 输出选项
chaosread --help
# 期望输出包含: --version
```

## OHOS 适配

- 跳过上游 autotools：conanfile 直接用 clang 编译 chaosread.c（仅 322 行），
  避免 autogen + configure 的跨工具链配置开销。
- 手工生成 `config.h`：上游 configure.ac 仅产生 PACKAGE / VERSION /
  RELEASE_DATE 三个宏，conanfile 在 build() 步骤中用 echo 写入临时
  config.h，绕开 autoconf。
- libusb-1.0 用 stub 替代：上游 chaosread.c 调用 libusb API 极少，conanfile
  配 `libusb_stub/` 100 行 C stub 模拟 libusb_init / libusb_open 等接口，
  避免 vendor 完整 libusb 源码 + autotools 在 OH cross-toolchain 下的编译坑。
- 上游无测试：test_package 用 `--version` + `--help` 输出作为 L2 smoke
  验证（两条 case 都在 qemu-aarch64-static 6.2.0 验证通过）。
- R32 合规：os 判断写 `in ("Linux", "OHOS")`，不是 `== "Linux"`。
