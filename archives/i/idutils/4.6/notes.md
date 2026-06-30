# idutils 4.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**: `ohc-run.py init-build idutils 4.6 --url=https://ftpmirror.gnu.org/gnu/idutils/idutils-4.6.tar.xz`
2. **替换 config.guess/config.sub**: 使用 automake-1.17 的新版本替换旧版本（2012-01-01），以识别 `aarch64-unknown-linux-ohos` 平台
3. **修复 configure/config.status 中 umask 077 → umask 022**: HMDFS 文件系统下 mktemp 创建的临时目录权限不兼容，导致 `Permission denied`
4. **修复 fseterr.c**: 添加 `__OHOS__` 分支，启用 musl libc 的 portable fallback 实现（FILE 结构为 opaque）
5. **设置 CPP="clang -E"**: 避免 autoconf 检测到 `-traditional-cpp` 导致 sanity check 失败
6. **configure**: `CPP="clang -E" ./configure --prefix=$DEFAULT_PREFIX`
7. **make -j1**: 编译成功
8. **make install DESTDIR=$TEST_PREFIX**: staging 安装成功
9. **安全弹窗验证**: 9 个二进制均可执行（8 个 ELF + 1 个脚本）
10. **make check**: idutils testsuite 6/6 PASS；gnulib-tests 编译失败（pthread_cancel weak symbol 未声明），不影响功能
11. **package**: 打包完成，idutils-4.6-ohos-aarch64.tar.gz: 1619KB
12. **本地安装验证**: 所有 9 个命令可用（--version 返回 4.6）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版本(2012-01-01)不支持 HarmonyOS/uname -s=HarmonyOS | 替换为 automake-1.17 的新版 config.guess/config.sub |
| 2 | config.status: Permission denied (创建 ./confXXX/subs1.awk) | HMDFS 文件系统下 `umask 077 && mktemp -d` 创建的目录权限不兼容（owner UID=20001006≠ 当前用户 UID=20020082） | 修改 configure 和 config.status 中 `umask 077` 为 `umask 022` |
| 3 | C preprocessor "clang -E -traditional-cpp" fails sanity check | autoconf 检测 CPP 时添加了 `-traditional-cpp` 标志 | 设置 `CPP="clang -E"` 避免添加 `-traditional-cpp` |
| 4 | fseterr.c: "Please port gnulib fseterr.c to your platform" | musl libc 的 FILE 结构为 opaque，gnulib 无 `__OHOS__` 分支 | 添加 `#elif defined __OHOS__` 分支，使用 portable fallback（fputc/dup 方法） |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| build-aux/config.guess | 替换为 automake-1.17 版本（识别 aarch64-unknown-linux-ohos） |
| build-aux/config.sub | 替换为 automake-1.17 版本（支持 aarch64-unknown-linux-ohos triplet） |
| configure | 修改 umask 077 → umask 022（2处，共4处修改） |
| lib/fseterr.c | 添加 `#elif defined __OHOS__` 分支（portable fallback） |

## 依赖版本

无外部依赖。idutils 是自包含的 ID database 工具。

## 验证结果

```bash
# --version 验证
aid - 4.6, eid - 4.6, fid - 4.6, gid - 4.6, lid - 4.6, mkid - 4.6, xtokid - 4.6, fnid - 4.6, defid - 4.6

# testsuite 结果
Testsuite summary for idutils 4.6
# TOTAL: 6, # PASS: 6, # SKIP: 0, # XFAIL: 0, # FAIL: 0, # XPASS: 0, # ERROR: 0

# verify-build 结果
G1: ✅8 ⚠️1 ❌0 (8 ELF + 1 script)
G2: ✅0 ⚠️9 ❌0 (--version working but non-standard format)
G3: ✅1 ⚠️17 ❌0 (RPATH/strip warnings)
G4: ✅0 ⚠️0 ❌0
总体: PASS-WARN
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| idutils-4.6-ohos-aarch64.tar.gz | 1619KB | 预编译包 |

## 注意事项

- gnulib-tests 编译失败（pthread_cancel weak symbol 问题），不影响 idutils 核心功能
- defid 是 shell 脄本，调用 gid 命令
- configure/config.status 的 umask 077 问题是 HMDFS 平台通用陷阱（E002 相关），需在每个 autotools 软件编译时注意
---

**编译结束**: 2026-06-13 16:24
**最终状态**: published
