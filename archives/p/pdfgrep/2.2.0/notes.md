# pdfgrep 2.2.0 适配笔记

## 编译环境
- 构建系统: autotools（手动创建 config.h + 手动编译）
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

因 HarmonyOS HMDFS 文件系统限制，autotools 的 `configure` + `config.status` 无法正常运行（`mktemp -d` 创建临时目录后无法写入文件）。采用手动编译方式：

1. 修补 `config.guess` 和 `config.sub` 添加 HarmonyOS 平台检测
2. 手动创建 `config.h`（基于 configure.ac 中检测到的功能）
3. 手动编译源码：
   ```bash
   clang++ -std=c++14 -fPIC -O2 -I./src -I./ -I.../include/poppler/cpp -I.../include/poppler -I.../include -c src/*.cc
   clang++ -L.../lib -Wl,-rpath,.../lib -o pdfgrep *.o -lpoppler-cpp -lgcrypt -lpcre2-8 -lpoppler -lintl
   ```
4. 同时编译 Debug 版本（-g -O0）
5. ELF 签名二进制文件
6. 创建 tar.gz 打包（含 lib/external 依赖）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: 平台未在已知列表中 | 修改 config.guess 添加 `aarch64:HarmonyOS:*:*)` case |
| 2 | config.sub 不接受 "ohos" OS | ohos不在OS验证列表中 | 修改 config.sub 添加 `ohos*` 和 `linux-ohos*` 识别 |
| 3 | config.status 创建临时文件失败 | HMDFS限制：mktemp创建目录后无法写入子文件 | 手动创建 config.h + 手动编译 |
| 4 | pdfgrep 需要 poppler-cpp >= 0.36.0 | poppler不在预编译包列表中 | 编译 poppler 23.12.0 作为依赖 |
| 5 | poppler 26.05.0 需要 C++20 | clang 15 不支持 std::ranges::sort | 降级使用 poppler 23.12.0 (C++17) |
| 6 | libgpg-error 预编译包只有 .a 无 .so | libgcrypt.so 运行时找不到 libgpg-error.so | 静态链接 libgcrypt.a + libgpg-error.a |

## 源码修改

| 文件 | 原因 | 方式 |
|------|------|------|
| config.guess | 添加 HarmonyOS 平台检测 | 添加 `aarch64:HarmonyOS:*:*)` case → `aarch64-unknown-linux-ohos` |
| config.sub | 支持 ohos OS 名 | 添加 `ohos*` 到 OS 验证列表 + `ohos-linux` 到 maybe_os + `linux-ohos*` 到 kernel-os 验证 |
| config.h | 替代 autotools 生成 | 手动创建 config.h，包含 PACKAGE/VERSION/HAVE_* 等宏定义 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| poppler-cpp | 23.12.0 | 本地编译 |
| poppler | 23.12.0 | 本地编译 |
| libgcrypt | 1.11.0 | cmd-pkgs 预编译 |
| libgpg-error | 1.55 | cmd-pkgs 预编译（静态库） |
| libpcre2-8 | 10.40 | 本地编译 |
| libintl | built-in | 系统内置 |

## 验证结果

编译成功，Release 和 Debug 两个版本均已编译。由于运行时依赖链（libgcrypt→libgpg-error.so）问题，直接运行验证需要将所有 .so 依赖打包到 lib/external 中。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pdfgrep-2.2.0-ohos-aarch64.tar.gz | 13.3MB | Release 制品（strip 二进制 + lib/external 依赖） |
| pdfgrep-2.2.0-ohos-aarch64-debug.tar.gz | 14.4MB | Debug 制品（含调试符号 + lib/external 依赖） |

## 注意事项

- poppler 23.12.0 作为 pdfgrep 的硬依赖需要预先编译安装
- config.h 是手动创建的（替代了 autotools configure），未来升级版本需要重新检测功能宏
- libgpg-error 只有静态库可用，链接时需手动指定 .a 路径

## 编译结束
**编译结束**: 2026-05-25
**最终状态**: built