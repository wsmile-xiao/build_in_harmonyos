# wmgtemp 1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-29
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18)
- 状态: published

## 编译步骤

```bash
# 进入 OHOS 构建环境
PATH=/data/storage/el1/bundle/libs/arm64/python/bin:/system/bin:/bin:$HOME/tmp/bin:/data/storage/el2/base/cache/bin:/data/service/hnp/bin:$HOME/.local/bin:$HOME/usr/local/bin:/usr/bin
CONAN_HOME=/data/storage/el2/base/cache/conan-home
TMPDIR=/data/storage/el2/base/cache

# 构建并测试
conan create archives/w/wmgtemp/1.2/conanfile.py \
  --version=1.2 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --profile:host=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: C compiler cannot create executables` | LDFLAGS 中的 `-L<linker-view>` 在 configure 阶段导致测试编译失败 | 将 linker-view 的 -L 从 configure_args 移到 make 阶段的 LDFLAGS 环境变量 |
| 2 | `fatal error: 'sensors/sensors.h' file not found` | lm-sensors 只有静态库，且 configure 阶段未传递 include 路径 | 在 configure 和 make 阶段通过环境变量传递 lm-sensors 的 include/lib 路径 |
| 3 | `sort: stat failed: -: Permission denied` | HMDFS 上 bash 的 getcwd  bug | 使用 `/system/bin/sh` 运行 configure 和 make |
| 4 | `Your 'rm' program is bad` | Electron safe-bin shim 中的 rm 有损坏的 shebang | 在 _run_ohos 中清理 PATH，移除 safe-bin 目录 |
| 5 | test_package case3 失败 | 系统 `/system/bin/env` 有 OpenSSL 符号缺失 | 改用 bash 内置 `unset DISPLAY` 代替 `env -u DISPLAY` |

## 源码修改

无补丁文件。wmgtemp 1.2 不单独提供 config.guess/config.sub，平台检测内置在 configure 中。conanfile 在 build() 阶段将 configure 中的 `umask 077` 替换为 `umask 022`（FUSE 文件系统兼容性）。

## 依赖版本

- libdockapp/0.7.3
- lm-sensors/3.6.0 (仅静态库 libsensors.a)
- libx11/6.4.0 (传递依赖)
- libxpm/3.5.17 (传递依赖)
- libxext/6.4.0 (传递依赖)

## 验证结果

```bash
# 二进制类型
$ file /data/storage/el2/base/cache/conan-home/p/b/wmgtef6f2a0c877b8e/p/bin/wmgtemp
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# test_package 结果
PASS [PASS] wmgtemp -h prints Usage and exits 0
PASS [PASS] wmgtemp -h prints version v1.2
PASS [PASS] wmgtemp loads full shared-lib closure on OHOS
total=3 passed=3 failed=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/wmgtemp | 104896 | aarch64 ELF 可执行文件 |
| share/man/man1/wmgtemp.1 | 手册页 |
| licenses/Artistic | Artistic 许可证 |

## 注意事项

- lm-sensors 只有静态库，wmgtemp 链接时需 `-lsensors` 和 `-L<lm-sensors lib>`
- 上游无自动化测试（Makefile.am 中无 TESTS/check_PROGRAMS）
- test_package 使用 3 个消费者用例验证 CLI、版本和运行时链接
---

**编译结束**: 2026-09-29 11:27
**最终状态**: published
