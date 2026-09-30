# libdfu-ahp 1.0-git20221215.dd2df39 适配笔记

## 源码与依赖

- 上游提交：`dd2df39301cff5760c065fd70ad58f3f0c388dde`。
- 源码 URL 和 SHA-256 见 `conandata.yml`，锁定任务指定快照。
- 依赖 `libusb/1.0.27`（无 user/channel）、系统 `m` 和 `pthread`。
- 许可证元数据依据库源文件头的 `GPL-2.0-or-later`；上游 Debian `debian/copyright` 却写 `LGPL-3+`，两处声明不一致。没有将 Debian 声明解释成对 GPL 源文件的重新授权。CMake 查找模块另带 BSD 许可说明，保留所有原始声明。

## 适配修改

1. 将 CMake 最低版本由 2.6 提升至 3.15，兼容真机 CMake 4.x。
2. 将库、头文件和 CMake 模块安装目录改为相对路径，支持 Conan 安装前缀；保留原有动态库构建方式。
3. 配方声明 `shared-library`。OHOS 的 CMake 平台没有默认 SONAME 标志，因此显式设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`，使消费者依赖 `libdfu.so.1`，不写入构建机 Conan 缓存绝对路径。

## 真机验证（2026-09-28）

在 HarmonyOS PC 6.1、aarch64、Clang 15.0.4、CMake 4.4.3、Conan 2.29.1 环境执行：

```sh
conan create archives/l/libdfu-ahp/1.0-git20221215.dd2df39 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

本机 profile 使用赛事 Conan 仓库兼容的 `os=OHOS`、`os.version=6.0`、`arch=armv8`、`compiler=clang`、`compiler.version=15`、Release 配置。

- 库本体编译、安装、打包以及独立消费者编译、链接、运行通过。
- 产物为 AArch64 ELF 共享库，SONAME 为 `libdfu.so.1`；动态依赖为 `libusb-1.0.so.0` 和 `libc.so`。
- 消费者 DT_NEEDED 为 `libdfu.so.1` 和 `libc.so`，不含构建机缓存路径。
- 真机工具链已为库和消费者生成 `.codesign` 签名段。

## 官方检查脚本

在同一鸿蒙 PC 上运行 `origin/main`（`c54cf81de`）的 `ci/conan/build_and_test.sh`，限定当前软件和任务分支。脚本逻辑未修改；检查副本仅将上游 CRLF 转为 LF，并通过临时 PATH 将 `readelf` 指向同一 SDK 的 `llvm-readelf`。

G0、KC、JC、L0、L1、L4、L5 均为 pass；L2 因纯库没有 bin 目录而跳过。L1e 反向测试确认移走本包的 lib/include 后消费者失败，恢复后正常。此处为本地真机预检，远程 PR CI 结果单独确认。

## 上游测试与验证边界

锁定快照无独立 tests、CTest 或 make check 入口，上游测试数为 0；没有删除或改写上游测试。新增消费者用例调用公开 API `dfu_flash_filename`，传入不存在的固件路径并断言返回 `ENODEV`，共 1 个断言。

该测试覆盖库加载、链接和错误返回，不覆盖 USB 外设枚举、DFU 接口声明或固件传输。未连接可刷写的 DFU 外设，因此不宣称设备刷写通过。
