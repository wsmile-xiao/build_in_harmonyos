# libiio 0.25 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-linux-ohos, musl)
- 任务认领: 2404_87638649
- 状态: built

## 源码
- 上游: https://github.com/analogdevicesinc/libiio/archive/refs/tags/v0.25.tar.gz
- SHA256: 21972599a3c143ab1f98002ad2b3f28f4aff927fde5f677478311cd4e517730c
- 零 patch 适配（见下）

## 后端裁剪策略（任务策略记录）

libiio 核心库（context/device/channel/buffer 对象模型 + XML 描述解析）零外部依赖。
可选后端按 OHOS PC 平台能力逐项决策：

| 后端 | 开关 | 决策 | 理由 |
|------|------|------|------|
| XML | WITH_XML_BACKEND=ON | **保留** | 内存 XML context（iio_create_xml_context_mem）是唯一无需内核 IIO 子系统的 context 创建路径，test_package 用它做全链路 API 验证；唯一代价是 libxml2/2.15.3（制品仓已发布） |
| Network | WITH_NETWORK_BACKEND=OFF | 禁用 | 需要 avahi (HAVE_DNS_SD) + iiod-client；avahi 不在制品仓且 OHOS 无 D-Bus 生态 |
| IIOD | WITH_IIOD=OFF | 禁用 | IIO 守护进程需要 systemd/sysvinit init 集成与真实 IIO 设备 |
| USB | WITH_USB_BACKEND=OFF | 禁用 | libusb-1.0 后端面向 ADI USB 评估板；OHOS 无相关设备节点 |
| Serial | WITH_SERIAL_BACKEND=OFF | 禁用 | 上游默认 OFF（libserialport 依赖） |
| Local | （未显式设置） | 自动禁用 | upstream `IF(CMAKE_SYSTEM_NAME MATCHES "Linux")` 块在 HarmonyOS 下不定义 WITH_LOCAL_BACKEND option → local.c/libini/librt/pthread 整块跳过。OHOS PC 无 /sys/bus/iio（实测不存在），local 后端即使编出来也无法创建 context。**无需 patch** |
| ZSTD | WITH_ZSTD=OFF | 禁用 | 压缩元数据传输（网络后端特性，网络已禁） |
| Tests/工具 | WITH_TESTS=ON | 保留 | 构建 iio_info 等 CLI 工具（R38 软件级 commands.json） |
| Man/Doc/Examples | OFF | 禁用 | 文档与示例非交付物 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMAKE_SYSTEM_NAME=HarmonyOS 不匹配上游 `MATCHES "Linux"` | 上游只认 Linux/Darwin/Win32 | **不 patch**：该行为恰好把 local backend/iiod/udev 打包路径挡在门外，符合裁剪策略（W0b 历史核验：0.26 在途适配用 patch 启用 local，本任务策略相反——零依赖核心库） |
| 2 | OHOS SDK lld 动态依赖 libxml2.so.16 不在加载器路径 (E120/E132) | lld 二进制被 strip 无 RUNPATH | generate() 加 `-fuse-ld=/data/service/hnp/bin/ld`（GNU ld）+ `add_rpath_link`（0.26 在途适配同款方案） |
| 3 | 上游无 install(EXPORT)，无 CMake config 包 | 只提供 libiio.pc | test_package 用 PkgConfigDeps + pkg_check_modules IMPORTED_TARGET 消费（与上游预期一致） |
| 4 | 上游 tests/ 工具需真实 IIO 设备 | iio_info 等要打开 /sys/bus/iio 或 iiod | OHOS PC 无 IIO 子系统（/sys/bus/iio 不存在，平台限制），工具二进制构建成功 + 运行时 graceful 报错退出路径已实测；API 级验证转由 test_package 的 XML 内存 context 承担（R34） |

## 上游测试执行记录（W5 上游测试）

libiio 0.25 上游**无 CTest 注册用例**（`ctest -N` 为空；tests/ 目录是 6 个交互式 CLI 工具，
无 assert 基础设施）。上游工具对 IIO 设备的依赖属内核/硬件平台限制，逐条说明：

| 工具 | 需要 | OHOS PC 现状 | 处置 |
|------|------|--------------|------|
| iio_info | 真实 IIO context（/sys/bus/iio 或 iiod） | /sys/bus/iio 不存在 | 二进制可执行，运行返回 "Unable to create IIO context" 非零退出（graceful 路径正确），跳过设备级断言 |
| iio_genxml | 同上 | 同上 | 同上 |
| iio_attr | 真实设备+属性 | 同上 | 同上 |
| iio_readdev | 真实设备+缓冲 | 同上 | 同上 |
| iio_reg | 真实设备+寄存器 | 同上 | 同上 |
| iio_writedev | 真实设备+缓冲 | 同上 | 同上 |

**上游测试通过率：可执行验证 6/6（工具二进制链接+加载+运行），设备相关断言 0/6 不可用（平台无 IIO 子系统）。
API 级验证由 test_package 的 15 项断言承担（XML 内存 context 全链路）。**

## 验证结果

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... → 通过
test_package: test_iio 15/15 断言通过（版本/backend 表/XML context/设备枚举/通道属性）
L2 smoke: iio_info --help 退出码 0
```

## 依赖版本
- libxml2/2.15.3（conan 制品仓，唯一依赖）
---

**编译结束**: 2026-09-05 01:40
**最终状态**: built
