# libfreehand 0.1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://dev-www.libreoffice.org/src/libfreehand-0.1.1.tar.bz2
2. 解压到工作目录
3. 修改 config.guess / config.sub 添加 HarmonyOS 平台识别
4. 修复 configure/config.status 中的 umask 077 权限问题
5. 设置 PKG_CONFIG_PATH 指向 librevenge 0.0.5 预编译包
6. 执行 `./configure --prefix=$DEFAULT_PREFIX`
7. 执行 `make -j1`
8. 执行 `make install DESTDIR=$TEST_PREFIX` (staging 验证)
9. 执行 `make check`
10. 打包: `python3 ohc-run.py package libfreehand 0.1.1`
11. 安装: `make install` (不带 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | uname 返回 HarmonyOS，config.guess 无匹配分支 | 修改 config.guess 添加 HarmonyOS 识别分支 (E007) |
| 2 | config.sub 拒绝 linux-ohos | config.sub 无 ohos 平台条目 | 修改 config.sub 添加 ohos-linux 条目 (E007) |
| 3 | configure 临时文件创建失败 | umask 077 导致 HMDFS 上 mktemp 目录权限不足 | 将 configure/config.status 中 umask 077 改为 umask 022 (E082/E097) |
| 4 | -Wmismatched-tags 错误 | FHPath.h 前向声明 class FHTransform，但 FHTransform.h 定义为 struct | 将前向声明改为 struct FHTransform |
| 5 | -Wdeprecated-copy 错误 | FHTransform 有用户定义的赋值运算符，编译器隐式生成拷贝构造函数被标记为废弃 | 添加 #ifdef __OHOS__ 守卫的拷贝赋值运算符 |
| 6 | U16_NEXT 宏后缺少分号 | libfreehand_utils.cpp 中 U16_NEXT 宏调用后未加分号 | 在 U16_NEXT 宏调用后补充分号 |

## 源码修改

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| config.guess | 平台适配 | 添加 HarmonyOS 识别分支 |
| config.sub | 平台适配 | 添加 ohos-linux 条目 |
| configure | 权限修复 | umask 077 → umask 022 |
| src/lib/FHPath.h | 编译修复 | class FHTransform → struct FHTransform |
| src/lib/FHTransform.h | 编译修复 | 添加 #ifdef __OHOS__ 拷贝赋值运算符 |
| src/lib/FHTransform.cpp | 编译修复 | 添加 #ifdef __OHOS__ 拷贝赋值运算符实现 |
| src/lib/libfreehand_utils.cpp | 编译修复 | U16_NEXT 宏后补充分号 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| librevenge | 0.0.5 | cmd-pkgs 预编译包 |
| liblcms2 | 2.x | 系统预装 (运行时依赖) |

## 功能测试结果

### 命令行工具测试
- **fh2raw**: 正常解析 AGD/FH3 格式文件 (exit 0)，无效文件正确报错 ✅
- **fh2svg**: 检测格式正常，最小文件 SVG 生成失败为预期行为 ✅
- **fh2text**: 检测格式正常，最小文件解析失败为预期行为 ✅
- **--help / --callgraph**: 所有工具帮助信息正确 ✅
- **错误处理**: 无效文件/空文件/无参数均优雅处理，无崩溃 ✅

### 库 API 测试 (C++ 链接验证)
- **编译链接**: clang++ 成功编译链接 libfreehand 程序 ✅
- **isSupported()**: 正确检测 AGD/FH3 格式，拒绝无效/空文件 ✅
- **parse()**: 最小文件返回失败（预期行为），无 segfault ✅

### pkg-config 集成
- `--modversion` → 0.1.1 ✅
- `--cflags` → 正确的 include 路径 ✅
- `--libs` → 正确的链接路径和库 ✅

### ELF 二进制验证
- 三个工具均为有效 ELF，RUNPATH 正确 ✅
- 所有 NEEDED 依赖库在系统中可用 ✅

## 验证结果

```bash
# staging 验证
ls $TEST_PREFIX/storage/Users/currentUser/usr/local/lib/libfreehand-0.1.so.1.0.1
ls $TEST_PREFIX/storage/Users/currentUser/usr/local/bin/fh2raw fh2svg fh2text

# 安装验证
pkg-config --modversion libfreehand-0.1  # → 0.1.1
ls $DEFAULT_PREFIX/bin/fh2raw fh2svg fh2text
ls $DEFAULT_PREFIX/lib/libfreehand-0.1.so.1.0.1

# make check
make check  # 全部测试通过

# 功能测试
fh2raw test-minimal.fh  # exit 0 ✅
fh2raw test-invalid.fh  # ERROR: Unsupported file format! ✅
# C++ API 测试程序编译链接成功，isSupported() 工作正常
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfreehand-0.1.1-ohos-aarch64.tar.gz | 3204KB | 预编译包 |
| libfreehand-0.1.1-ohos-aarch64-debug.tar.gz | 884KB | 调试符号包 |

## 安装产物

| 产物 | 路径 | 说明 |
|------|------|------|
| fh2raw | ~/usr/local/bin/fh2raw (22KB) | FreeHand → Raw 转换工具 |
| fh2svg | ~/usr/local/bin/fh2svg (31KB) | FreeHand → SVG 转换工具 |
| fh2text | ~/usr/local/bin/fh2text (22KB) | FreeHand → Text 转换工具 |
| libfreehand-0.1.so.1.0.1 | ~/usr/local/lib/ (461KB) | 共享库 |
| libfreehand-0.1.pc | ~/usr/local/lib/pkgconfig/ | pkg-config 文件 |
| libfreehand 头文件 | ~/usr/local/include/libfreehand-0.1/ | 开发头文件 |

## 注意事项

- 源码下载 URL 为 dev-www.libreoffice.org，Savannah 镜像可能 404 或 SSL 失败
- librevenge 是必需依赖，需先安装并设置 PKG_CONFIG_PATH
- 生成文件补丁（fh2raw, fh2svg, fh2text, .rc 文件等）应排除，仅保留源码修改补丁
- G0 干净构建验证使用 /bin/sh (toybox) 运行 configure 会失败，需用 bash 运行（已知平台限制）

---

**编译结束**: 2026-06-25 15:09
**功能测试**: 2026-06-25 16:10
**最终状态**: published
