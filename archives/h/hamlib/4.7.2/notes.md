# hamlib 4.7.2 适配笔记

## 编译环境

- 构建系统：Autotools
- 目标：OpenHarmony PC arm64 (`aarch64-linux-ohos`)
- 构建方式：静态库，关闭 libusb/readline/HTML matrix/WinRadio/parallel
- 官方源码：Hamlib 4.7.2 release，SHA-256 绑定在 `conandata.yml`

## OHOS 兼容修复

- Linux `linux/wireless.h` 在 OHOS sysroot 与 `sys/socket.h` 重定义
  `sockaddr_storage`；OHOS 不进入 Linux wireless ioctl 分支。
- OHOS libc 不提供 `pthread_cancel`；Hamlib 核心线程停止路径在 OHOS
  跳过取消调用并 join。
- ARS rotator 后台线程在 OHOS 改为可 join 的协作停止标志，避免 detached
  线程泄漏或 cleanup 后访问已释放状态。

## 验证

- 本地 Autotools configure 与 `make -j1` 已通过。
- 本地 `make install INSTALL=install` 已生成 `libhamlib.a`、`libhamlib++.a`、
  头文件和命令行工具；消费者测试与目标机测试仍由 Conan/W3 阶段完成。

## r36/r009 验证补充

- r36 `conan create` 返回 `CONAN_CREATE_RC=0`；最终 package 含 16 个头文件、2 个
  静态库和 14 个 CLI。w64devkit 安装 helper 的两段多行 awk 归并程序报告 `not found`，
  因此 recipe 对明确的 `source_folder` 输出执行显式复制，并按类别复核包内容。
- Conan test_package 生成文件写在其 `source_folder`；验证后已移出 CMake/Conan 生成物、
  consumer ELF 和 `__pycache__`，候选目录只保留源码、CMakeLists、MANIFEST 和 test.c。
- 当前候选 W3 successor `hamlib-4.7.2-w3-r009-150125` 在
  `10.62.150.125:8022` 单次 launch 通过 consumer 4/4 assertions、非空 `rigctl -l`
  和 upstream 12/12；release 后独立回读远端根为 `ABSENT`。
