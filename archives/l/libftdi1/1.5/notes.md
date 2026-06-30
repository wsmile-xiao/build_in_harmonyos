# libftdi1 1.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**: 从官方网站下载 libftdi1-1.5.tar.bz2
   - URL: https://www.intra2net.com/en/developer/libftdi/download/libftdi1-1.5.tar.bz2
2. **初始化编译环境**: `python3 scripts/ohc-run.py init-build libftdi1 1.5`
3. **配置**: cmake 自动配置，使用默认参数
   - `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
   - `-DCMAKE_BUILD_TYPE=Release`
4. **编译**: `make -j1` (首次失败，自动重试成功)
   - 失败原因: make jobserver mkfifo 权限问题
   - 重试时 unset C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH
5. **安装**: `make install DESTDIR=$TEST_PREFIX` (staging 验证通过)
6. **打包**: 自动打包为 libftdi1-1.5-ohos-aarch64.tar.gz
7. **部署**: 手动部署到 ~/usr/local (遇到 HMDFS 权限问题)
8. **验证**: ftdi_eeprom 命令可用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | Savannah 镜像链接失效 | 改用官方网站 intra2net.com |
| 2 | SSL 证书验证失败 | Python urllib SSL 问题 | 手动下载后使用本地文件 |
| 3 | make jobserver 权限问题 | HMDFS 文件系统限制 | 脚本自动重试绕过 |
| 4 | 部署阶段权限错误 | HMDFS 不能直接覆盖文件 | 手动删除旧文件后重新部署 |

## 源码修改

无补丁，无需修改源码

## 依赖版本

- libusb-1.0: 系统已安装
- cmake: 4.1.2
- make: GNU Make 4.4.1
- pkg-config: 0.29.2

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/ftdi_eeprom --help
FTDI eeprom generator v0.17
(c) Intra2net AG and the libftdi developers <opensource@intra2net.com>

$ ls -lh ~/usr/local/lib/libftdi1*
libftdi1.a    (79KB)
libftdi1.so   (154KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libftdi1-1.5-ohos-aarch64.tar.gz | 728KB | 预编译包（含 ftdi_eeprom 和依赖库） |
| libftdi1-1.5-ohos-aarch64-debug.tar.gz | 144KB | 调试符号包 |

## 功能测试结果 (2026-06-05)

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 二进制完整性 | ✅ PASS | ELF 64-bit arm64, musl 链接 |
| 功能可用性 | ✅ PASS | ftdi_eeprom 命令可执行 |
| 可移植性 | ✅ PASS | RPATH 设置正确 |
| 档案完整性 | ✅ PASS | manifest.yaml, notes.md 完整 |

### 发现并修复的问题

1. **EXCLUDE_LIST 导致 bin 目录遗漏**: 原预编译包 bin 目录为空，清理 EXCLUDE_LIST 后重新打包
2. **manifest.yaml build_system 字段错误**: 从 `autotools` 更正为 `cmake`

## 注意事项

1. **HMDFS 文件系统限制**: 不能直接使用 ln -sf 或 shutil.copytree 覆盖文件，需先删除旧文件
2. **依赖 libusb-1.0**: 运行时需要 libusb 库支持（已打包到 lib/external）
3. **构建工具**: 使用 cmake 构建系统，非 autotools
4. **USB 设备权限**: 使用 FTDI 设备需要相应的 USB 设备访问权限**功能测试**: 2026-06-05 11:28 - 全项通过，符合上库要求
---

**编译结束**: 2026-06-05 11:29
**最终状态**: published
