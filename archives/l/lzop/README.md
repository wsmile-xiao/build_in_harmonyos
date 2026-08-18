# lzop 1.04 — OpenHarmony 编译记录

## 基本信息
- 软件: lzop
- 版本: 1.04
- 构建系统: autotools
- 目标: ohos-aarch64
- 依赖: lzo2/2.10

## 编译指导
- Autotools + AutotoolsDeps（lzo2 的 -I/-L/-l 由 AutotoolsDeps 传递）
- make -j1（HMDFS jobserver FIFO EPERM，E074）
- 补丁应用后 configure 可识别 aarch64-linux-ohos

## 补丁清单
- 0001-autoconf-config.guess.patch — config.guess 更新，识别 OHOS（E007）
- 0002-autoconf-config.sub.patch — config.sub 更新，接受 aarch64-linux-ohos（E007）
- 0003-configure.patch — configure umask 077→022（E011/E114）

## 已知限制
- 上游 lzop 1.04 无测试套件（make check 为空目标），功能验证由 test_package
  真实执行 lzop 二进制（--version + 压缩/解压往返内容比对）完成

## 功能验证
- test_package/test.sh: lzop --version + lzop -c / lzop -dc 往返 cmp 内容一致
