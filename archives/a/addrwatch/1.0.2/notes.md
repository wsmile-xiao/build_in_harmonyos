# addrwatch 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -kfsSL -o addrwatch-1.0.2.tar.gz https://github.com/fln/addrwatch/releases/download/v1.0.2/addrwatch-1.0.2.tar.gz`
2. 解压源码到工作目录
3. 安装依赖: `libpcap 1.10.6`, `libevent 2.1.12`, `argp-standalone 1.5.0` (通过 cmd-pkgs 预编译包安装)
4. 运行 configure:
   ```bash
   export PKG_CONFIG_PATH="$DEFAULT_PREFIX/lib/pkgconfig"
   export LDFLAGS="-L$DEFAULT_PREFIX/lib"
   export CPPFLAGS="-I$DEFAULT_PREFIX/include"
   export LIBS="-lintl"
   ./configure --prefix=$DEFAULT_PREFIX
   ```
5. 编译: `make -j1`
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 测试: `make check` (无测试套件)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: can't create subs1.awk: Permission denied | mktemp 创建的临时目录 owner(20001006) 与当前用户(20020101) 不匹配，umask 077 导致其他用户无法写入 | 补丁 0003: 修改 configure 脚本中 umask 077→000 |
| 2 | make 触发 aclocal/automake/autoconf 重新生成 | missing 脚本调用系统 autotools 重新生成 configure，丢失平台修复 | 补丁 0005: 替换 missing 脚本为 no-op (exit 0) |
| 3 | 重新生成的 configure 恢复 umask 077 | autoconf 重新生成 configure 后覆盖了修改 | 补丁 0005 确保 missing 脚本为 no-op，补丁 0003 修复 umask |
| 4 | argp_parse 符号未找到 | libargp.a 引用 libintl_dgettext | 链接时添加 -lintl |
| 5 | config.guess 不识别 OHOS | addrwatch 源码不含 config.guess/config.sub 文件 | 补丁 0003: 将 configure 中 config.guess/config.sub 引用改为条件式（文件存在时才引用）。R15: 不使用 --build/--host 绕过 |

## 源码修改

共 6 个补丁文件，均在 conandata.yml 中声明，通过 `apply_conandata_patches(self)` 自动应用：

| 补丁文件 | 说明 |
|---------|------|
| 0001-Makefile.in.patch | 更新 Makefile.in 从 automake 1.16.1 到 1.16.5 |
| 0002-aclocal.m4.patch | 更新 aclocal.m4 从 automake 1.16.1 到 1.16.5 |
| 0003-configure.patch | 修复 configure: umask 077→000 (HMDFS 兼容), config.guess/config.sub 引用改为条件式 (E007/E078) |
| 0004-doc-Makefile.in.patch | 更新 doc/Makefile.in 从 automake 1.16.1 到 1.16.5 |
| 0005-missing.patch | 替换 missing 脚本为 no-op (防止 autotools 重新生成) |
| 0006-src-Makefile.in.patch | 更新 src/Makefile.in 从 automake 1.16.1 到 1.16.5 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | cmd-pkgs 预编译包 |
| libevent | 2.1.12 | cmd-pkgs 预编译包 |
| argp-standalone | 1.5.0 | cmd-pkgs 预编译包 |
| libintl (gettext) | 8.4.0 | cmd-pkgs 预编译包 |

## 验证结果

### make check 输出
```
Making check in src
make[1]: Entering directory '.../src'
make[1]: Leaving directory '.../src'
Making check in doc
make[1]: Nothing to be done for 'check'.
Making check in .
make[1]: Nothing to be done for 'check-am'.
```
addrwatch 无测试套件，make check 输出 "Nothing to be done for 'check'"。

### 二进制验证
```bash
$ addrwatch --help
Usage: addrwatch [OPTION...] [INTERFACE1 INTERFACE2 ...]
Keep track of ethernet/ip address pairings for IPv4 and IPv6.
```
二进制可正常运行，显示帮助信息。

### conan-verify 结果
全部 8 道门禁通过:
- G0: PASS (预构建风险评估)
- G1: PASS (配方完整性检查)
- G2: PASS (conan create 干净构建)
- G3: PASS (系统同名库隔离验证 R26)
- G4: PASS (产物完整性检查)
- L2: PASS (平台功能矩阵 smoke test)
- L4: PASS (静态安全扫描 checksec)
- L5: PASS (产物基线对比)

## 交付物

| 文件 | 说明 |
|------|------|
| bin/addrwatch | 主程序 (301568 bytes) |
| bin/addrwatch_stdout | 共享内存输出工具 (31168 bytes) |
| bin/addrwatch_syslog | syslog 输出工具 (31168 bytes) |
| share/man/man8/addrwatch.8 | 手册页 |

## 注意事项

- 配置环境变量时不能设置 `LD_LIBRARY_PATH` 包含 `$DEFAULT_PREFIX/lib`，否则 Python 解释器加载 libintl.so.8 时会出错
- argp-standalone 必须链接 -lintl，否则会出现 libintl_dgettext 符号未定义
- 该项目无测试套件，make check 不会执行任何测试
- R15: 不使用 --build/--host 参数，addrwatch 源码不含 config.guess/config.sub，configure 补丁(0003)将引用改为条件式
---

**编译结束**: 2026-06-30 11:40
**最终状态**: published
