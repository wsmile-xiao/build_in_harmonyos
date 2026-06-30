# acct 6.6.4 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

```bash
source .build-context-acct-6.6.4
export CC=clang CXX=clang++ CC_FOR_BUILD=clang
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess (2012年版) 不包含 HarmonyOS 检测分支，uname -s 返回 HarmonyOS 无法匹配 | 修改 config.guess: 添加 HarmonyOS 到 Linux case 模式 + 添加 aarch64:HarmonyOS case |
| 2 | config.status 创建临时文件失败 | HMDFS 文件系统上 umask 077 创建的目录权限为 drwx--S---，写入文件报 Permission denied | 修改 configure 和 config.guess: umask 077 -> 022 |
| 3 | SSL 证书下载失败 | Python urllib 无法验证 SSL 证书 | 设置 SSL_CERT_FILE 指向 certifi 的 cacert.pem |
| 4 | accton off 崩溃 | E051: HarmonyOS 内核未实现 acct() 系统调用 | 平台限制，不阻塞编译，记录为已知限制 |

## 源码修改

补丁文件: `patches/0001-ohos-platform-fix.patch`

修改文件:
1. **config.guess**:
   - `Linux|GNU/*)` → `Linux|GNU/*|HarmonyOS)` (第一 case 语句，LIBC 检测)
   - 新增 `aarch64:HarmonyOS:*:*) echo aarch64-unknown-linux-gnu` (第二 case 语句)
   - `umask 077` → `umask 022` (set_cc_for_build 函数中的临时目录创建)

2. **configure**:
   - `umask 077` → `umask 022` (临时目录创建，2处)

## 依赖版本

无外部依赖。acct 使用 gnulib 内置库 (lib/libgnu.a)。

## 验证结果

- 7 个二进制文件全部编译成功 (ac, last, lastcomm, dump-utmp, dump-acct, accton, sa)
- 全部为 aarch64 ELF 动态链接可执行文件
- --help 和 --version 输出正常
- conan-verify 全部门禁通过 (G0-G4 + L2/L4/L5)

## 注意事项

1. accton 的 `off`/`on` 功能依赖 `acct()` 系统调用，在 HarmonyOS 上会触发 Bad system call (E051)
2. ac/last 等工具依赖 wtmp/utmp 文件，HarmonyOS 上默认路径为 /dev/null/wtmp，需配置正确的系统日志路径
3. 补丁中的 umask 修改是 HMDFS 文件系统特定修复，不影响其他平台
---

**编译结束**: 2026-06-30 12:00
**最终状态**: published
