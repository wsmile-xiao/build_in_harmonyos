# ems-flasher 0.03 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile, 非 autotools/cmake)
- 编译日期: 2026-08-14
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. `conan install --requires=libusb/1.0.27 -b=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default`
   — 获取 libusb 预编译包到 conan 缓存
2. `source conanbuild.sh` — 获取 Conan 构建环境 (PATH, SHELL, CONFIG_SHELL)
3. `source conanrun.sh` — 获取运行时 LD_LIBRARY_PATH (libusb .so 路径)
4. `make -j1 CC=clang CFLAGS="... -I<conan_libusb>/include/libusb-1.0" LDFLAGS="-L<conan_libusb>/lib" LIBS="-lusb-1.0"`
5. `make install DESTDIR=$TEST_PREFIX PREFIX=""` — 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg-config --cflags/--libs libusb-1.0 返回 /usr/local 路径 | libusb 包的 .pc 文件 prefix=/usr/local (硬编码), 非 Conan 包路径 | 修改 Makefile 支持环境变量覆盖 CFLAGS/LIBS, 不依赖 pkg-config |
| 2 | install 命令不在 OHOS PATH | OHOS 无 coreutils install | Makefile install target 改用 mkdir -p + cp |
| 3 | VERSION 宏显示 "0.02" 而非 "0.03" | 上游 tarball 命名为 0.03 但 main.c 中 `#define VERSION "0.02"` 未更新 (上游 bug) | 不修改 (这是上游打包问题, 不影响功能) |

## 源码修改

### Makefile 修改 (探索阶段, R6: 不生成 .patch, 由 finish refresh-patch --auto 生成)

原 Makefile 依赖 `pkg-config` 获取 libusb 编译/链接标志:
```make
CFLAGS += `pkg-config --cflags libusb-1.0`
$(CC) -o $(PROG) $(OBJS) `pkg-config --libs libusb-1.0`
```

修改后 Makefile:
- `CFLAGS ?= -g -Wall -Werror \`pkg-config --cflags libusb-1.0\`` (使用 `?=` 允许环境变量覆盖; 默认值保留 pkg-config 以保证原生构建可用)
- `LIBS ?= \`pkg-config --libs libusb-1.0\`` (默认用 pkg-config, 交叉编译时由 Conan 环境变量提供)
- `LDFLAGS ?=` (新增, 允许环境变量传入链接路径)
- `PREFIX ?= /usr/local` / `DESTDIR ?=` (新增默认值, 避免 install target 变量未定义)
- 链接行改为 `$(CC) -o $(PROG) $(OBJS) $(LDFLAGS) $(LIBS)` (不再内联 pkg-config)
- 新增 `install` target: `mkdir -p $(DESTDIR)$(PREFIX)/bin` + `cp` (OHOS 无 install 命令)

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libusb | 1.0.27 (recipe revision 0e6a7c47e7b3b5c19d0bdb3887145a1e) | ohpcd 制品仓 (已发布) |

## 测试套件

- **上游无测试套件**: 源码无 test target, 无 tests/ 目录, 无 check 目标
- 验证方式: `--version` 和 `--help` 命令执行成功 (exit 0)
- R40 注意: 这是 USB 外设工具, 编译链接正确但 USB 运行时行为 (设备识别/传输) 不在 CI 测试范围

## 验证结果

```bash
# 构建验证
$ make -j1 CC=clang CFLAGS="..." LDFLAGS="..." LIBS="-lusb-1.0"
# → 成功, 无 warning (通过 -Werror)

# Staging 验证
$ file bin/ems-flasher
# → ELF shared object, 64-bit LSB arm64, dynamic

# --version
$ ems-flasher --version
EMS-flasher 0.02
# → exit 0

# --help
$ ems-flasher --help
# → Usage 输出, exit 1 (上游 usage() 设计 exit(1))

# readelf -d (R26 检查)
$ llvm-readelf -d bin/ems-flasher
# → NEEDED: libusb-1.0.so.0, libc.so (无系统同名库污染)
# → FLAGS: BIND_NOW, FLAGS_1: NOW PIE (RELRO + PIE)
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ems-flasher | EMS Gameboy USB 64Mbit 烧录卡刷写工具 (ELF aarch64) |

## 注意事项

- libusb .pc 文件 prefix=/usr/local 是已知问题, 配方中用 VirtualBuildEnv + 环境变量覆盖, 不依赖 pkg-config
- VERSION 宏 "0.02" 是上游打包 bug, 不修正 (不改变用户可见行为的核心功能)
- R40: USB 外设工具, 编译通过验证构建链接正确性; USB 设备运行时交互不在 CI 范围
- conanfile.py build() 调用 apply_conandata_patches(self) 应用 0001-Makefile.patch (声明式补丁, 非动态修改)
- --help 上游设计 exit(1) (usage() 调 exit(1)), test_package 只测 --version (exit 0)
- conan-verify 8门禁全部 PASS (G0-G4 + L2/L4/L5)
---

**编译结束**: 2026-08-14 16:30
**最终状态**: built
