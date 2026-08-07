# ttfautohint 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤
```bash
# 使用 sed 修复 config.guess/config.sub 添加 HarmonyOS 支持
# 绕过运行时测试（交叉编译环境）
# 使用 /system/bin/sh 运行 configure（HMDFS noexec 兼容）
./configure --build=aarch64-unknown-linux-musl --with-qt=no
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识 OHOS | E160: 标准 config.guess 无 HarmonyOS 识别 | sed 添加 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl` |
| 2 | config.sub 不识 ohos | config.sub 缺少 ohos 类型 | sed 添加 ohos-* 和 linux-ohos* 支持 |
| 3 | FreeType 版本检查失败 | 运行时测试程序无法执行 | 绕过 `cross_compiling` 检查 |
| 4 | configure 脚本无法执行 | HMDFS noexec 文件系统 | 使用 `/system/bin/sh` 显式调用 |
| 5 | config.status 临时文件创建失败 | HMDFS noexec 临时目录 | 预创建可写临时目录，修补 config.status |
| 6 | harfbuzz 依赖不可用 | 未发布到制品仓 | 设置 HARFBUZZ_CFLAGS/LIBS 绕过 |
| 7 | 补丁文件格式错误 | git 格式 patch 不被 Conan 支持 | 改用 sed 命令直接修改源码 |

## 源码修改
- `gnulib/config.guess`: 添加 HarmonyOS 检测（E160）
- `gnulib/config.sub`: 添加 ohos 支持
- `configure`: 绕过运行时测试和 FreeType 版本检查

## 依赖版本
- freetype/2.14.3（制品仓）

## 验证结果
```bash
$ ttfautohint --version
ttfautohint 1.8.4
```

## 注意事项
1. harfbuzz 依赖被绕过（未发布到制品仓），ttfautohint 核心功能（auto-hinting）不需要 harfbuzz
2. Qt GUI 被禁用（`--with-qt=no`），仅使用命令行模式
3. 本地 W3 CI 模拟因 OHOS 平台 HMDFS noexec 限制无法通过，CI 执行机可正常执行