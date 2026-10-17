# cdpr 2.4 — OpenHarmony 编译记录

## 基本信息
- 软件: cdpr
- 版本: 2.4
- 构建系统: makefile（无 configure, 单 Makefile）
- 目标: ohos-aarch64
- 依赖: libpcap/1.10.6

## 编译指导
- Raw Makefile: `make CC=<工具链 cc> CFLAGS="-Wall -W -O2 -I<libpcap include>" LDFLAGS="-L<libpcap lib> -lpcap" -j1`
- 补丁应用后 Makefile 接受 `$(CC)`，全局变量兼容 -fno-common
- make -j1（HMDFS jobserver FIFO EPERM，E074）

## 补丁清单
- 0001-makefile-use-cc-variable.patch — Makefile 链接行 `gcc` 改 `$(CC)`，接 Conan 工具链编译器
- 0002-cdpr-h-extern-globals-fno-common.patch — cdpr.h 全局变量改 extern，cdpr.c 单一定義（-fno-common 多重定义修复）

## 已知限制
- 上游 cdpr 2.4 无测试套件（Makefile 仅 cdpr/clean 目标），功能验证由 test_package
  真实执行 cdpr 二进制（`cdpr -h` 的版本横幅/用法说明/选项说明三断言）完成
- `cdpr` 运行时需抓包权限与 Cisco 设备，test_package 仅覆盖 `-h` 安全路径，不做真实抓包

## 功能验证
- test_package/test.sh: `cdpr -h` 退出码与非空输出 + 版本横幅断言 + 用法说明断言
