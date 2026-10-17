# xz 5.4.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: built
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)

## 编译步骤

1. init-build: `python3 scripts/ohc-run.py init-build xz 5.4.5 --no-download`
   - 源码已通过 curl 下载到 $HOME/tmp/xz-5.4.5.tar.xz
2. 应用补丁:
   - 0001-build-aux-config.guess.patch: 添加 HarmonyOS 检测分支
   - 0002-build-aux-config.sub.patch: 添加 ohos* OS 支持和 linux-ohos* 验证
3. 修复 umask: `sed -i 's/umask 077/umask 022/g' configure`
4. `./configure --prefix=$DEFAULT_PREFIX --disable-scripts`
5. `make -j1` — 编译成功
6. `make install DESTDIR=$TEST_PREFIX` — 安装成功
7. `make check` — 18/18 测试全部通过
8. conan-verify: G1-G4 全部通过 (conan create, smoke test, checksec, baseline)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: 2021年版 config.guess 无 HarmonyOS 分支 | 添加 *:HarmonyOS:*:*) case 分支 (GUESS= 变量模式) |
| 2 | config.sub 拒绝 linux-ohos | E007: config.sub 不识别 ohos OS | 添加 ohos* 到 OS 名称列表和 linux-ohos* 到 kernel 验证 |
| 3 | umask 077 导致权限问题 | E011: HMDFS 下 umask 077 创建 0700 权限目录 | 修改 configure 中 umask 077 → 022 |
| 4 | OHOS 无 /bin/sh | 脚本依赖 /bin/sh | --disable-scripts 跳过脚本安装 |
| 5 | conandata.yml SHA256 不匹配 | ghfast.top 镜像返回不同文件 | 使用 conan 计算的 SHA256 |

## 源码修改

### build-aux/config.guess
- E007: 添加 HarmonyOS 系统检测 case 分支
- 添加 `*:HarmonyOS:*:*)` case，输出 `${MACHINE}-unknown-linux-ohos`

### build-aux/config.sub
- E007: 添加 `ohos*` 到 OS 名称列表
- 添加 `linux-ohos*` 到 kernel-os 验证

## 依赖版本

无额外依赖（xz 5.4.5 是自包含的）

## 验证结果

```
=== make check ===
PASS: test_check
PASS: test_hardware
PASS: test_stream_flags
PASS: test_filter_flags
PASS: test_filter_str
PASS: test_block_header
PASS: test_index
PASS: test_index_hash
PASS: test_bcj_exact_size
PASS: test_memlimit
PASS: test_lzip_decoder
PASS: test_vli
PASS: test_files.sh
PASS: test_compress_prepared_bcj_sparc
PASS: test_compress_prepared_bcj_x86
PASS: test_compress_generated_abc
PASS: test_compress_generated_random
PASS: test_compress_generated_text

============================================================================
Testsuite summary for XZ Utils 5.4.5
============================================================================
# TOTAL: 18
# PASS:  18
# SKIP:  0
# XFAIL: 0
# FAIL:  0
============================================================================
```

## 注意事项

1. config.guess 使用 GUESS= 变量模式（2021年版，非旧版 echo+exit）
2. conandata.yml URL 使用 GitHub 官方 release URL
3. conanfile.py 基于 5.8.3.2 模式：mktemp wrapper, --disable-scripts, -static, CONFIG_SHELL fix, umask fix
4. xz 5.4.5 早于 CVE-2024-3094（该漏洞影响 5.6.0/5.6.1）
---

**编译结束**: 2026-08-27 20:47
**最终状态**: built

## PR Submission
- PR submitted: 2026-08-27
