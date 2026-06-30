# kvazaar 2.3.2 — 编译笔记

## 基本信息
- **软件**: kvazaar (Ultravideo HEVC encoder)
- **版本**: 2.3.2
- **构建系统**: autotools (autoconf/automake/libtool)
- **语言**: C/C++
- **平台**: aarch64-unknown-linux-ohos (HarmonyOS HongMeng Kernel 1.12.0)
- **编译器**: clang 15.0.4
- **链接器**: ld.lld (LLVM)

## 编译流程

### 1. 源码下载
GitHub 直连超时，使用 `curl -k` 下载到本地后通过 `file://` 协议传递。
原始大小: 600,315 bytes (tar.gz)。

### 2. autoreconf -fi
GitHub archive 不含 configure 脚本。运行 `autoreconf -fi` 后生成 configure + config.status。
有少量废弃宏警告（AC_PROG_CC_C99, $as_echo），不影响功能。

### 3. greatest 子模块获取
GitHub archive 不含 git submodule (`greatest` 测试框架)，手动下载填充:
```
curl -k https://github.com/ultravideo/greatest/archive/refs/heads/master.tar.gz
tar xzf greatest.tar.gz --strip-components=1 -C greatest/
```

### 4. configure
```bash
CONFIG_SHELL=bash bash ./configure --prefix=$DEFAULT_PREFIX
```
配置参数仅 `--prefix`（R1 铁律），平台自动检测为 `aarch64-unknown-linux-ohos`。

### 5. 关键问题：HMDFS umask 077 权限问题

**问题**: autoconf 生成的 config.status 使用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录。
在 HMDFS 文件系统上，umask 077 创建的目录（权限 `drwx--S---`）无法在其中创建文件，导致:
```
config.status[1070]: can't create ./confTzL6sL/subs1.awk: Permission denied
```

**根因**: HMDFS 对 umask 077 创建的目录有文件系统级写入限制。
验证: `umask 022 && mktemp -d` 创建的目录（`drwxr-s--x`）可正常写入。

**解决方案**: 将 config.status 和 configure 中的 `umask 077` 替换为 `umask 022`。
```bash
sed -i 's/umask 077/umask 022/g' config.status configure
```

**影响范围**: 任何使用 autoconf/automake 的软件都可能遇到此问题。

### 6. make
```bash
make -j2
```
编译成功。50+ 源文件编译通过，仅 1 个无关警告:
```
search_intra.c:729:14: warning: variable 'bits' set but not used
```
注意: `make -j` 的 jobserver 因 HMDFS 不支持 mkfifo 而失败，但 make 自动降级为串行模式。

### 7. make install DESTDIR (R20 模式)
```bash
make install DESTDIR=$TEST_PREFIX
```
产物安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/`。

### 8. make check
- **单元测试** (kvazaar_tests): **92 项全部通过**，41073 条断言
  - sad_tests: 53/53 PASS
  - intra_sad_tests: 10/10 PASS
  - satd_tests: 15/15 PASS
  - dct_tests: 10/10 PASS
  - coeff_sum_tests: 1/1 PASS
  - mv_cand_tests: 3/3 PASS
- **外部符号检查** (test_external_symbols.sh): PASS
- **集成测试** (12 个 shell 测试): 全部 FAIL — 需要 `ffmpeg` 生成测试输入（非编译依赖）

### 9. make install (本地验证)
```bash
$ kvazaar --version
Kvazaar v2.3.2
Kvazaar license: 3-clause BSD
```

## 产物清单
| 路径 | 大小 | 说明 |
|------|------|------|
| bin/kvazaar | 68,032 B | HEVC 编码器 CLI |
| lib/libkvazaar.so.7.5.0 | 416,128 B | 共享库 (API 7:5:0) |
| lib/libkvazaar.so | → libkvazaar.so.7.5.0 | 软链接 |
| lib/libkvazaar.so.7 | → libkvazaar.so.7.5.0 | 软链接 |
| lib/libkvazaar.a | 651,976 B | 静态库 |
| include/kvazaar.h | — | 公共头文件 |
| lib/pkgconfig/kvazaar.pc | — | pkg-config 配置 |
| share/man/man1/kvazaar.1 | — | 手册页 |
| share/doc/kvazaar/* | — | 文档 |

## SIMD 优化说明
在 ARM aarch64 平台上，kvazaar 的 SIMD 策略（AVX2/SSE2/SSE41/Altivec）不会被激活
（这些是 x86/PowerPC 指令集）。代码回退到 generic C 实现，功能完整正确。

## 知识沉淀
1. HMDFS 不支持在 umask 077 创建的目录中写入文件（影响所有 autotools 软件）
2. HMDFS 不支持 mkfifo（影响 make -j 并行编译，但 make 自动降级为串行模式）
3. 系统默认 /bin/sh 是 mksh R59，autotools 编译建议使用 CONFIG_SHELL=bash
4. GitHub archive 需 autoreconf -fi 生成 configure 脚本，git submodule 需单独获取

---

**编译结束**: 2026-06-18 01:38
**最终状态**: published
