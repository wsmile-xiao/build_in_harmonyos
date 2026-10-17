# enca 1.19 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (conan-verify 通过)
- 目标平台: aarch64-unknown-linux-ohos

## 编译步骤

1. 下载源码: https://github.com/nijel/enca/archive/refs/tags/1.19.tar.gz
2. 修改 config.guess: 添加 HarmonyOS 检测分支 (E007)
3. 修改 config.sub: 添加 linux-ohos 到 OS 识别列表 (E007)
4. 修改 configure: 将 umask 077 改为 umask 022 (E206)
5. 修改 src/filebuf.c: 将硬编码 /tmp 替换为 TMPDIR 环境变量 (E002)
6. 运行 ./configure --prefix=/storage/Users/currentUser/usr/local
7. 运行 make -j2
8. 运行 make install DESTDIR=$TEST_PREFIX
9. 运行 make check

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测 | 添加 HarmonyOS case 分支，输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 拒绝 linux-ohos 三元组 | E007: config.sub 不识别 linux-ohos OS | 添加 linux-ohos* 到 maybe_os 和 OS 验证列表 |
| 3 | config.status 无法创建临时文件 | E206: HMDFS setgid 目录权限，umask 077 导致非属主用户无法写入 | 将 configure 中 umask 077 改为 umask 022 |
| 4 | enca 运行时无法创建临时文件 | E002: /tmp 只读，enca 硬编码 /tmp 路径 | 修改 src/filebuf.c 使用 TMPDIR 环境变量 |

## 源码修改

4 个补丁文件:
1. 0001-config.guess.patch - 添加 HarmonyOS 检测
2. 0002-config.sub.patch - 添加 linux-ohos OS 支持
3. 0003-configure.patch - umask 077 → 022
4. 0004-src-filebuf.c.patch - /tmp → TMPDIR

## 依赖版本

- libiconv/1.17 (Conan 制品仓)

## 验证结果

```bash
$ enca --version
enca 1.19
Features: -librecode-interface +iconv-interface +external-converter +language-detection ...

$ make check
# TOTAL: 21
# PASS:  19
# SKIP:  2 (test-tex.sh, test-recode.sh — tex/recode 未安装)
# FAIL:  0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | Conan L1 测试 |
| patches/ | 4 个适配补丁 |
| commands.json | 命令行工具声明 (enca) |

---

**编译结束**: 2026-08-06 09:00
**最终状态**: built
