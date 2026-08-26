# exodriver 2.7.0 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，非 autotools/cmake）
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4 / llvm-ar / llvm-ranlib
- 平台: HarmonyOS PC (aarch64, OHOS 6.0)
- 状态: built

## 软件简介
exodriver（又名 liblabjackusb）是 LabJack USB 设备访问库。源码包内实际库代码位于
`liblabjackusb/` 子目录，包含 Makefile、labjackusb.c、labjackusb.h。examples/ 目录
包含 U3/U6/UE9/U12/Modbus 等示例程序。

## 编译步骤

### Step 1: init-build
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build exodriver 2.7.0 \
  --url=https://github.com/labjack/exodriver/archive/refs/tags/v2.7.0.tar.gz --auto
```
注意：init-build 的嵌套源码提升有误（误将 examples/Modbus 当源码），需手动重新解压：
```bash
cd /storage/Users/currentUser/tmp/builds
rm -rf exodriver-2.7.0.work && mkdir -p exodriver-2.7.0.work
tar xzf exodriver-2.7.0.tar.gz -C exodriver-2.7.0.work --strip-components=1
```

### Step 2: 获取 libusb 依赖路径
```bash
conan install --requires=libusb/1.0.27 -r=ohpcd -pr:b .../ohos-aarch64 -pr:h .../ohos-aarch64 --build=missing
# libusb header: <pkg>/include/libusb-1.0/libusb.h
# libusb lib: <pkg>/lib/libusb-1.0.so
```

### Step 3: 编译 liblabjackusb
```bash
cd liblabjackusb
make CC=clang CFLAGS="-fPIC -O2 -I<libusb_inc>" \
     LIBFLAGS="-L<libusb_lib> -lusb-1.0 -lc" \
     RUN_LDCONFIG=0 -j1
# 产物: liblabjackusb.so.2.7.0, labjackusb.o
# 静态库: llvm-ar rcs liblabjackusb.a labjackusb.o
```

### Step 4: 验证 (examples 编译+运行)
```bash
cd examples/Modbus
make CC=clang CFLAGS="-Wall -g -I<libusb_inc> -I<labjack_dir>" \
     LDFLAGS="-L<labjack_dir> -L<libusb_lib>" \
     LIBS="-lm -llabjackusb -lusb-1.0" -j1
./testModbusFunctions  # ✅ 通过（纯协议测试）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码提升误识别 | exodriver 包内有多层目录，init-build 把 examples/Modbus 误当主源码 | 手动 tar xzf --strip-components=1 重新解压 |
| 2 | 编译需要 libusb 头文件路径 | 源码 `#include <libusb-1.0/libusb.h>` 需 libusb include 路径 | CFLAGS 传 -I<libusb_inc> |
| 3 | 链接需要 libusb 库路径 | LIBFLAGS 中 -lusb-1.0 需 lib 路径 | LIBFLAGS 传 -L<libusb_lib> |
| 4 | 静态库不存在 | Makefile 只构建 .so，无 .a 目标 | 用 llvm-ar rcs liblabjackusb.a labjackusb.o 手动创建 |
| 5 | examples 链接报 undefined libusb_* | 静态库链接顺序：-llabjackusb 在 -lusb-1.0 前 | LIBS 中确保 -lusb-1.0 在 -llabjackusb 之后 |
| 6 | readModbusExample 运行报 "Couldn't find a LabJack" | 需物理 LabJack USB 设备 | 预期行为（E046 硬件依赖），不阻塞 |

## 依赖版本
- libusb/1.0.27@ohpcd/stable（已发布于 ohpcd 制品仓）

## 验证结果
```
库编译: ✅ 通过 (liblabjackusb.so.2.7.0 + liblabjackusb.a)
产物验证: ✅ readelf NEEDED: libusb-1.0.so.0, libc.so; SONAME: liblabjackusb.so
examples 编译: ✅ 通过 (testModbusFunctions, readModbusExample, writeModbusExample)
testModbusFunctions 运行: ✅ PASS
硬件依赖测试: ⚠ 跳过（无 LabJack 设备）
```

## 注意事项
- exodriver 的库名是 `labjackusb`（非 exodriver），package_info().libs=["labjackusb"]
- 源码无 configure/make check，是裸 Makefile
- make install 中有 ldconfig 调用（OHOS 上不生效），设 RUN_LDCONFIG=0 跳过
- 默认构建为 static（default_options shared=False），符合库的典型用法
---

**编译结束**: 2026-08-26 10:09
**最终状态**: published
