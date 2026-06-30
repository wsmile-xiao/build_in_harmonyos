# libptytty latest 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-11
- 编译器: clang/clang++ (v15.0.4)
- 状态: built

## 编译步骤

1. **初始化编译环境**
   - URL 搜索：使用 search-url 策略，从 GitHub 找到项目地址
   - URL: https://github.com/yusiwen/libptytty/archive/refs/heads/master.tar.gz
   - 执行 `ohc-run.py init-build libptytty latest --url=...`

2. **CMake 配置**
   - 创建 build 目录：`mkdir -p build && cd build`
   - 配置命令：`cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DBUILD_SHARED_LIBS=OFF -DUTMP_SUPPORT=OFF -DWTMP_SUPPORT=OFF -DLASTLOG_SUPPORT=OFF ..`
   - **关键参数**：
     - `BUILD_SHARED_LIBS=OFF`：编译为静态库（鸿蒙 ELF 签名要求）
     - `UTMP_SUPPORT=OFF`：禁用 utmp 支持（鸿蒙缺少 utmpx API）
     - `WTMP_SUPPORT=OFF`：禁用 wtmp 支持
     - `LASTLOG_SUPPORT=OFF`：禁用 lastlog 支持

3. **编译**
   - 执行 `make ptytty -j1`
   - 仅编译库文件，跳过 c-sample 示例程序（链接问题）

4. **手动安装**
   - 创建目标目录结构
   - 复制 libptytty.a 到 lib/
   - 复制 libptytty.h 到 include/
   - 复制 libptytty.pc 到 lib/pkgconfig/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 缺失 | registry 中无记录 | 使用 search-url 策略，从 GitHub 搜索找到项目地址 |
| 2 | utmpx API 缺失 | 鸿蒙系统缺少 setutxent/getutxid/pututxline/endutxent 函数 | 禁用 UTMP/WTMP/LASTLOG 支持（`-DUTMP_SUPPORT=OFF`） |
| 3 | c-sample 链接失败 | C 程序链接 C++ 库缺少 C++ 标准库符号 | 跳过示例程序编译，只编译库文件 |
| 4 | cmake 平台识别警告 | CMake 不认识 HarmonyOS | 可忽略，不影响编译 |

## 源码修改

无补丁。所有修改通过 CMake 配置参数实现。

## 依赖版本

- cmake: 4.1.2
- clang/clang++: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
# 检查静态库
ls -lh /storage/Users/currentUser/test-install-libptytty-latest/storage/Users/currentUser/usr/local/lib/libptytty.a
-rw-rw---- 1 20001006 file_manager  50K 2026-06-11 15:53 libptytty.a

# 检查头文件
ls -lh /storage/Users/currentUser/test-install-libptytty-latest/storage/Users/currentUser/usr/local/include/libptytty.h
-rw-rw---- 1 20001006 file_manager  1737 2022-12-29 22:06 libptytty.h

# 检查 pkgconfig
cat /storage/Users/currentUser/test-install-libptytty-latest/storage/Users/currentUser/usr/local/lib/pkgconfig/libptytty.pc
prefix=/storage/Users/currentUser/usr/local
Name: libptytty
Version: 2.0
Cflags: -I/storage/Users/currentUser/usr/local/include
Libs: -L/storage/Users/currentUser/usr/local/lib -lptytty
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libptytty.a | 50K | 静态库（已禁用 utmp/wtmp/lastlog） |
| libptytty.h | 1737 bytes | 头文件 |
| libptytty.pc | 280 bytes | pkgconfig 文件 |

## 注意事项

1. **平台限制**：鸿蒙系统不支持 utmp/wtmp/lastlog 功能，必须禁用这些选项
2. **静态库编译**：建议编译为静态库，避免 ELF 签名问题
3. **版本号**：使用 GitHub master 分支，版本号为 2.0
4. **示例程序**：c-sample 示例程序无法在鸿蒙上编译，跳过
---

**编译结束**: 2026-06-11 15:56
**最终状态**: built
