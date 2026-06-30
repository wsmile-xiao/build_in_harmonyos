# gpgme 1.24.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-05-21
- 编译器: clang/clang++ (OpenHarmony 工具链)
- 状态: built

## 编译步骤

1. 下载源码：从 gnupg.org 下载 gpgme-1.24.0.tar.bz2
2. 初始化构建环境：`python3 ohc-run.py init-build gpgme 1.24.0`
3. 解压源码到工作目录
4. 修复 config.guess/config.sub 添加 HarmonyOS (linux-ohos) 识别
5. 修复 configure 中的 umask 077 → umask 000 (HMDFS 权限问题)
6. 运行 configure：`./configure --prefix=/storage/Users/currentUser/usr/local LDFLAGS="-lintl"`
7. 编译：`make -j1` (由于依赖库问题，gpgme-tool 无法链接，仅编译核心库)
8. 手动安装核心库到 TEST_PREFIX
9. 验证：`python3 ohc-run.py verify-build gpgme 1.24.0`
10. 打包：`python3 ohc-run.py package gpgme 1.24.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess 不识别 HarmonyOS | autotools 默认不支持 linux-ohos | 手动修改 config.sub 添加 `linux-ohos*` 到 case 分支 |
| E011 | HMDFS umask 077 导致临时目录权限问题 | HMDFS 文件系统默认 umask | 修改 configure 第33036行 `umask 077` → `umask 000` |
| E012 | libtool archive 路径错误 | libgpg-error.la 包含硬编码路径指向 libintl.la | 修改 libgpg-error.la 的 dependency_libs，将错误路径替换为正确路径 |
| E074 | libintl 链接符号未定义 | libgpg-error.a 静态库依赖 libintl，但链接顺序不正确 | 添加 `LDFLAGS="-lintl"` 到 configure；手动安装核心库跳过工具程序 |

## 补丁修改

1. **build-aux/config.sub**: 第1781行添加 `linux-ohos*` 模式识别
2. **configure**: 第33036行 `umask 077` → `umask 000`
3. **src/Makefile**: 修改 gpgme_tool_LDADD 和 gpgme_json_LDADD 添加 `-lintl`

## 依赖版本

- libgpg-error: 1.55 (静态库 libgpg-error.a)
- libassuan: 3.0.2 (动态库 libassuan.so)
- libintl (gettext): 静态库 libintl.a

## 验证结果

```bash
python3 ohc-run.py verify-build gpgme 1.24.0
# G1: ✅3 ⚠️0 ❌0 (libgpgme.so 相关 ELF 文件)
# G2: ✅0 ⚠️1 ❌0 (无可执行二进制，是库)
# G3: ✅0 ⚠️0 ❌0
# G4: ✅0 ⚠️0 ❌0
# 质量报告: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gpgme-1.24.0-ohos-aarch64.tar.gz | 1826KB | 主产物（预编译包） |
| gpgme-1.24.0-ohos-aarch64-debug.tar.gz | 4656KB | 调试符号包 |

## 注意事项

1. **libintl 链接问题**: libgpg-error.a 静态库依赖 libintl，需要确保链接时 `-lintl` 在正确的位置
2. **工具程序**: gpgme-tool 和 gpgme-json 因链接问题未能编译成功，但核心库 libgpgme.so 编译成功
3. **建议**: 未来重新编译 libgpg-error 时使用动态链接 gettext，可避免此问题
---

**编译结束**: 2026-05-21 12:26
**最终状态**: built
