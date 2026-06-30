# ucon64 2.2.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- libc: musl (HarmonyOS)
- 状态: built

## 编译步骤

1. 下载源码包 `ucon64-2.2.2-src.tar.gz` 并解压
2. 源码包有嵌套 `src/` 目录，需将其内容提升到顶层
3. 修补 `config.guess` 和 `config.sub`（2017 格式，原地修补）以支持 HarmonyOS 平台识别
4. 修补 `configure` 中的 `umask 077` → `umask 022`（HMDFS 权限限制）
5. 运行 `./configure --prefix=$DEFAULT_PREFIX --disable-parallel`
6. `make -j1`（使用 -j1 避免 HMDFS 上 mkfifo jobserver 问题）
7. 手动复制 `ucon64` 二进制到目标 bin/ 目录（install.sh 使用 sudo，无法直接使用）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 2017 版 config.guess 无 HarmonyOS/__OHOS__ 检测分支 | 原地修补 config.guess：添加 HarmonyOS case 块 + __OHOS__ LIBC 检测 |
| 2 | config.sub 不识别 linux-ohos | 2017 版 config.sub 无 ohos 平台 | 原地修补 config.sub：添加 linux-ohos* + ohos-linux 到 android-linux 块 |
| 3 | configure 创建目录权限 0700 | umask 077 在 HMDFS 上创建的目录无法写入 | 修补 configure：umask 077 → umask 022 |
| 4 | parallel.c 编译失败 | aarch64 无 I/O 端口访问（inb/outb 不可用） | configure 添加 --disable-parallel |
| 5 | Conan out-of-tree 构建失败 | ucon64 不支持 VPATH/out-of-tree 构建 | conanfile.py build() 改为 in-tree 构建（cwd=source_folder） |
| 6 | install.sh 使用 sudo | install.sh 脚本硬编码 sudo 和路径 | conanfile.py package() 手动 copy 二进制 |
| 7 | Conan 2 test_package API 变更 | deps_cpp_info 在 Conan 2 中不存在 | 改用 self.dependencies["ucon64"].package_folder |
| 8 | mkfifo 在 HMDFS 失败 | HMDFS 不支持 mkfifo 操作 | make 使用 -j1 避免 jobserver mkfifo |

## 源码修改

| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| config.guess | 添加 HarmonyOS case 块 + __OHOS__ LIBC 检测 | 0001-config.guess.patch |
| config.sub | 添加 linux-ohos* + ohos-linux 到 android-linux 块 | 0002-config.sub.patch |
| configure | umask 077 → 022 | 0003-configure.patch |
| misc/parallel.c | 并口支持禁用适配 | 0004-misc-parallel.c.patch |

## 依赖版本

无外部依赖。ucon64 是独立的终端工具，仅需 C 标准库和 zlib（内嵌）。

## 验证结果

```bash
$ file bin/ucon64
bin/ucon64: ELF executable, 64-bit LSB arm64, static, stripped

$ readelf -d bin/ucon64
There is no dynamic section in this file.

$ ucon64 --version
uCON64 2.2.2 UNIX (Linux) 1999-2021
version: 2.2.2 (Jun 26 2026)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ucon64 | 816,256 bytes | 静态链接 ELF 二进制 (aarch64) |

## 注意事项

1. ucon64 是终端工具，必须静态链接（R26），LDFLAGS=-static
2. aarch64 平台无 I/O 端口访问，必须 --disable-parallel
3. 源码包有嵌套 src/ 目录，conanfile.py source() 需处理
4. Conan 构建必须 in-tree（不支持 out-of-tree）
5. make 必须用 -j1（HMDFS 不支持 mkfifo）
---

**编译结束**: 2026-06-29 15:25
**最终状态**: published
