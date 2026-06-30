# libfixposix 0.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: published

## 编译步骤

```bash
source .build-context-libfixposix-0.5.1
cd $BUILD_SRC_DIR

# 1. autoreconf -fi (源码无 configure 脚本)
# 2. 修补 configure: mktemp -d 使用 $TMPDIR 而非 ./ (HMDFS 权限问题)
# 3. CONFIG_SHELL=bash bash ./configure --prefix=$DEFAULT_PREFIX
# 4. make -j1
# 5. make install DESTDIR=$TEST_PREFIX
# 6. make check (0 tests)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 ohos 三元组 | E072: 原始源码缺少 ohos 支持 | autoreconf -fi 重新生成 config.sub（系统版已含 ohos） |
| 2 | 源码无 configure 脚本 | tarball 只含 configure.ac | autoreconf -fi 生成完整构建系统 |
| 3 | configure/config.status temp dir 权限错误 (Permission denied) | HMDFS: mktemp -d "./confXXXXXX" 创建目录后 chmod 不生效，文件无法写入 | 修改 configure 中 mktemp 路径为 $TMPDIR 替代 "./" |
| 4 | make -j2 失败 (mkfifo: Operation not permitted) | HMDFS 不支持 mkfifo (jobserver) | 使用 make -j1 替代 make -j2 |
| 5 | /bin/sh (toybox sh) configure 执行问题 | toybox sh 与 autoconf 兼容性问题 | 使用 CONFIG_SHELL=bash 运行 configure |

## 源码修改

仅保留 2 个补丁（精简后移除 autoreconf 产物补丁 0001/0002/原0003）：

- `configure`: mktemp 路径修改 `"./confXXXXXX"` → `"${TMPDIR:-$HOME/tmp}/confXXXXXX"`，umask 077 → 022（HMDFS 限制）
- `src/include/lfp/strerror.h`: 头文件守卫 `_LFP_STRING_H_` → `_LFP_STRERROR_H_`（消除与 string.h 守卫冲突）

**autoreconf -fi 自动处理（无需补丁）**：
- `config/aux/config.guess`: autoreconf 重新生成（含 ohos 支持）→ 无需补丁
- `config/aux/config.sub`: autoreconf 重新生成（含 ohos 支持）→ 无需补丁
- `configure`: autoreconf 生成完整脚本 → 无需全文件补丁，仅手动修改 4 行 mktemp 路径

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.16.5
- libtool 2.4.7

## 验证结果

```bash
pkg-config --modversion libfixposix
# 0.5.1

ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/libfixposix.so.4.0.1
# exists
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfixposix.so.4.0.1 | 84KB | 共享库（已 stripped） |
| libfixposix.la | 1KB | libtool 档案 |
| *.h | 21个 | 头文件（含修复的 strerror.h） |
| libfixposix.pc | | pkg-config 元数据 |

## 注意事项

- HMDFS 限制：mktemp -d 在当前目录创建的目录权限受限（umask 077 生效但 chmod 不生效），需要使用 $TMPDIR 路径
- make 必须用 -j1（jobserver mkfifo 在 HMDFS 上不支持）
- 源码需要 autoreconf -fi 才能生成 configure（原始 tarball 不含）

## 功能测试结果（2026-06-04）

| 模块 | 测试数 | PASS | FAIL | 说明 |
|------|--------|------|------|------|
| errno | 3 | 3 | 0 | lfp_errno/set_errno |
| fcntl | 10 | 10 | 0 | lfp_open/creat/set_fd_cloexec/set_fd_nonblock |
| unistd | 9 | 9 | 0 | lfp_pipe/pread/pwrite/lseek/truncate/ftruncate/clearenv |
| select | 5 | 5 | 0 | lfp_select/fd_set/fd_clr/fd_isset/fd_zero |
| string/stdlib | 6 | 6 | 0 | lfp_strerror/strnlen/strndup |
| 符号完整性 | 1 | 1 | 0 | 119 个 lfp_ API 符号导出 |
| pkg-config | 1 | 1 | 0 | modversion=0.5.1 |
| **合计** | **34** | **34** | **0** | **✅ ALL PASS** |

### make check 说明

`make check` 返回 RC=2（No rule to make target 'check'），这**不是编译缺陷**，而是上游不提供测试套件：
- test-suite.log 显示 TOTAL=0
- 原始 Makefile 无 `check` 目标
- 已通过自定义功能测试覆盖验证（34 项全部通过）

### 修复记录（2026-06-04 补充）

1. ✅ **头文件守卫冲突已修复**: 补丁 `0004-strerror-header-guard.patch` 将 `lfp/strerror.h` 的守卫从 `_LFP_STRING_H_` 改为 `_LFP_STRERROR_H_`，消除 `lfp_strerror()` 隐式声明警告
2. ✅ **打包库已 strip**: 重新打包后 `libfixposix.so.4.0.1` 从 92KB 缩减至 84KB（stripped），symlinks 从硬链接副本改为正确的符号链接
3. ✅ **sha256 已补录**: 源码校验和 `0c698a4483fee0b5830de668f113c242932adc68dfbffeb09bec527aa28539ce` 已填入 manifest.yaml
4. ✅ **ELF 签名格式已澄清**: `.note.ohos.ident` 格式（Owner="OHOS", namesz=0xc, descsz=0x4）与系统所有二进制一致，readelf 警告是其解析限制而非签名缺陷

---

**编译结束**: 2026-06-04 09:54
**最终状态**: published
-04 09:54
**最终状态**: published
