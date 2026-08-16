# dfu-util 0.11 — HarmonyOS PC 适配记录

## 基本信息
- 软件：dfu-util（USB DFU 固件升级主机工具：dfu-util / dfu-prefix / dfu-suffix）
- 版本：0.11
- 上游：https://dfu-util.sourceforge.net/
- 构建系统：autotools（发布包自带预生成 configure）

## 适配要点
1. **libusb-1.0 依赖**：configure 用 `PKG_CHECK_MODULES` 强制要求
   `libusb-1.0 >= 1.0.0`。OHOS CI 设备上 libusb 是预编译系统包，安装在
   libusb 1.0.27 源码（sourceforge），先静态构建再供 dfu-util 链接；
   `$DEFAULT_PREFIX/lib/pkgconfig`（及 /data/service/hnp/lib/pkgconfig）加入
   同时用 ac_cv_search_libusb_init 跳过 -lusb 探测。
2. **运行期链接**：二进制静态链接内置 libusb，运行期无需
   libusb-1.0.so；构建时加 `-Wl,-rpath`，test 脚本里也设置 LD_LIBRARY_PATH。
3. **build triplet**：OHOS 下显式 `--build=aarch64-unknown-linux-gnu`，
   避免 config.guess 在 noexec 构建目录失败。

## 验证
- WSL 本地 `conan create` 通过（OHOS 模拟 settings + 系统 libusb）。
- 官方流水线 L0/L1/L4/L5。