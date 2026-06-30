# flock 2.40.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

1. **init-build**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build flock 2.40.2 --url=https://github.com/util-linux/util-linux/archive/refs/tags/v2.40.2.tar.gz`
   - flock 是 util-linux 的子命令，需要指定整个 util-linux 的源码 URL

2. **configure**:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX \
     --disable-liblastlog2 --disable-libmount --disable-libblkid \
     --disable-libfdisk --disable-libsmartcols --disable-libuuid \
     --disable-python --disable-asciidoc --disable-manpages
   ```
   - 耗时约 241 秒（util-linux 项目 configure 步骤较慢）
   - configure 成功完成，exit code 0

3. **选择性编译**: `make flock`
   - 由于 util-linux 的 `wall` 命令在 OpenHarmony 上编译失败（缺少 `getutxent()`/`endutxent()` utmpx API），无法执行完整的 `make`
   - 只编译 flock 子命令，使用 `make flock` 选择性构建

4. **staging 安装**: 手动将 flock binary 复制到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/flock`
   - DESTDIR 模式：`cp flock $TEST_PREFIX/$DEFAULT_PREFIX/bin/flock`

5. **make check**: 无法执行完整的 `make check`（因为只编译了 flock）
   - 改用功能性手动测试验证

6. **verify-build**: `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build flock 2.40.2 --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX`
   - 需要指定 `--install-prefix` 为 `$TEST_PREFIX/$DEFAULT_PREFIX`（DESTDIR 模式下实际安装路径）
   - 结果: PASS

7. **package**: `python3 $SKILL_ROOT/scripts/ohc-run.py package flock 2.40.2`
   - 产物: flock-2.40.2-ohos-aarch64.tar.gz (85KB)
   - debug: flock-2.40.2-ohos-aarch64-debug.tar.gz (49KB)

8. **安装到 DEFAULT_PREFIX**: flock 已存在于 `$DEFAULT_PREFIX/bin/flock`（前次安装），版本正确

9. **finish**: `python3 $SKILL_ROOT/scripts/ohc-run.py finish flock 2.40.2 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 全量编译失败（wall.c 报错） | OpenHarmony 缺少 utmpx API（`getutxent()`/`endutxent()`） | 使用 `make flock` 选择性编译，只构建需要的子命令 |
| 2 | `make check` 无法执行 | 只编译了 flock，其他命令未构建 | 用功能性测试代替：测试 flock 的排他锁、共享锁、非阻塞锁、超时锁等功能 |
| 3 | verify-build 的 G4 检查 `build_system:` 字段 | manifest.yaml 嵌套格式 `build.system:` 不被识别，脚本要求顶层字段 `build_system:` | 在 manifest.yaml 中添加顶层 `build_system: autotools` |
| 4 | verify-build 的 G1/G2 找不到二进制文件 | DESTDIR 模式下文件在 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`，但 verify 默认检查 `$TEST_PREFIX/bin/` | 使用 `--install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX` 参数 |
| 5 | cp 到 DEFAULT_PREFIX 报 "Operation not permitted" | 已有 flock binary 来自前次安装，HMDFS 不允许覆盖 | 已有正确版本，无需重新安装 |

## 源码修改

无补丁。flock 原生代码在 OpenHarmony 上编译无问题。

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.16.5

## 验证结果

```bash
$ flock --version
flock from util-linux 2.40.2

$ flock --help
Usage:
 flock [options] <file>|<directory> <command> [<argument>...]
 flock [options] <file>|<directory> -c <command>
 flock [options] <file descriptor number>

# 功能性测试：
$ flock /tmp/flock-test.lockfile echo "lock acquired successfully"
lock acquired successfully
$ flock -n /tmp/flock-test-nb.lockfile echo "non-blocking lock acquired"
non-blocking lock acquired
$ flock -s /tmp/flock-test-shared.lockfile echo "shared lock acquired"
shared lock acquired
$ flock -w 5 /tmp/flock-test-w.lockfile echo "timeout lock acquired"
timeout lock acquired
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| flock-2.40.2-ohos-aarch64.tar.gz | 85KB | 主制品包（包含 flock binary，已 strip + 签名） |
| flock-2.40.2-ohos-aarch64-debug.tar.gz | 49KB | debug 符号包 |

## 注意事项

1. **选择性编译**: flock 是 util-linux 的子命令，源码 URL 是整个 util-linux 项目。由于 `wall` 命令在 OpenHarmony 上编译失败（缺少 utmpx API），只编译了 flock 子命令。其他 util-linux 命令（mount, umount 等）未包含在此包中。
2. **DESTDIR 模式**: 使用 DESTDIR 模式进行 staging 安装时，verify-build 需要指定 `--install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX` 才能正确找到二进制文件。
3. **打包只包含 flock**: 此包仅包含 flock binary，不包含其他 util-linux 命令。
---

**编译结束**: 2026-06-09 11:19
**最终状态**: published
