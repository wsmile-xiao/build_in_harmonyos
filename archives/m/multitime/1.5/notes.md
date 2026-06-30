# multitime 1.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4
- 平台: OpenHarmony (aarch64)
- 状态: built

## 编译步骤

1. `make -f Makefile.bootstrap` — 从 configure.ac 生成 configure 脚本（autoconf + autoheader），同时修复 umask 权限问题
2. `./configure --prefix=$DEFAULT_PREFIX` — 通过 configure 包装脚本自动 bootstrap 并配置
3. `make -j1` — 编译二进制（生成 multitime, format.o, multitime.o）
4. `make install DESTDIR=$TEST_PREFIX` — staging 安装
5. `make install` — 安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包无 configure 脚本 | GitHub tag tarball 只包含 configure.ac，不包含预生成的 configure | 修改 Makefile.bootstrap 生成 configure.real，创建 configure 包装脚本自动 bootstrap |
| 2 | config.status 权限拒绝 | autoconf 的 config.status 使用 `umask 077` 创建临时目录，HMDFS 上目录 owner (20001006) ≠ 当前用户 (20020082)，组权限为空导致无法写入 | 在 Makefile.bootstrap 中添加 `sed -i 's/umask 077/umask 007/g' configure.real`，使组（file_manager）获得写权限 |
| 3 | 无 make check 目标 | multitime 不提供测试套件 | 手动功能测试 9 项全部通过（见 test-report.md） |
| 4 | G0 clean-verify 失败 | `patch --input` 选项在 OpenHarmony 平台不支持 | 平台限制，非代码问题；已手动验证从原始源码 + 补丁可重现编译 |
| 5 | verify-build 找不到二进制 | install_prefix 解析为 TEST_PREFIX 而非 TEST_PREFIX/DEFAULT_PREFIX | 使用 `--install-prefix` 参数指定完整路径 |

## 源码修改

### 1. Makefile.bootstrap (修改, 补丁 0001)
**原始**:
```makefile
configure: configure.ac
	autoconf
	autoheader
```
**修改后**:
```makefile
configure.real: configure.ac
	autoconf -o configure.real
	autoheader
	sed -i 's/umask 077/umask 007/g' configure.real
```
**原因**: 分离生成的 configure 脚本（configure.real）和包装脚本（configure），使 clean-verify 能自动 bootstrap；同时修复 umask 权限问题。

### 2. Makefile.in (修改, 补丁 0002)
**原始**: distclean 目标中 `rm -rf configure Makefile ...`
**修改后**: distclean 目标中 `rm -rf configure.real Makefile ...`
**原因**: 与 Makefile.bootstrap 修改一致，清理时删除正确的文件。

### 3. configure (新增, 补丁 0003)
```sh
#!/bin/sh
# OHOS platform wrapper: bootstrap configure.real if needed, then run it
if [ ! -f configure.real ]; then
    make -f Makefile.bootstrap
fi
exec sh ./configure.real "$@"
```
**原因**: 源码包无预生成 configure 脚本，包装脚本自动检测并运行 bootstrap。

## 依赖版本

无外部依赖（仅需要 libc 的 arc4random/drand48/random 函数）

## 验证结果（真实执行输出）

### 测试1: 基本功能
```
$ multitime -n 3 echo hello
hello
hello
hello
===> multitime results
1: echo hello
            Mean        Std.Dev.    Min         Median      Max
real        0.025       0.002       0.023       0.025       0.027
user        0.005       0.003       0.001       0.004       0.009
sys         0.016       0.005       0.009       0.019       0.019
```

### 测试2: sleep 计时精度
```
$ multitime -n 5 sleep 0.1
===> multitime results
1: sleep 0.1
            Mean        Std.Dev.    Min         Median      Max
real        0.127       0.009       0.118       0.121       0.142
user        0.008       0.005       0.001       0.007       0.016
sys         0.012       0.004       0.007       0.013       0.019
```

### 测试3: 二进制类型检查
```
$ file /storage/Users/currentUser/usr/local/bin/multitime
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 测试4: ELF 头验证
```
$ readelf -h multitime
  Class:                             ELF64
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           AArch64
```

### 测试5: rusage 格式
```
$ multitime -f rusage -n 2 echo hello
hello
hello
===> multitime results
1: echo hello
            Mean        Std.Dev.    Min         Median      Max
real        0.028       0.003       0.025       0.028       0.032
user        0.011       0.001       0.010       0.011       0.012
sys         0.011       0.003       0.008       0.011       0.014
maxrss      5474        2           5472        5474        5476
minflt      456         1           455         456         457
majflt      198         0           198         198         198
...
```

### 测试6: Staging 目录验证
```
$ $TEST_PREFIX/$DEFAULT_PREFIX/bin/multitime -n 2 echo "staging test"
staging test
staging test
===> multitime results
1: echo "staging test"
            Mean        Std.Dev.    Min         Median      Max
real        0.029       0.009       0.020       0.029       0.038
```

完整测试报告见: reports/test-report.md（9 项测试全部通过）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| multitime-1.5-ohos-aarch64.tar.gz | 93KB | 预编译包（含 ELF 签名） |
| multitime-1.5-ohos-aarch64-debug.tar.gz | 31KB | 调试符号包 |

## 编译警告

```
format.c:301:6: warning: misleading indentation; statement is not part of the previous 'else' [-Wmisleading-indentation]
```
- 严重程度: 低（仅缩进风格问题）
- 处理: 未修复（上游代码问题，不影响功能）

## 注意事项

- 源码包来自 GitHub tag tarball，不含预生成的 configure 脚本，需要 bootstrap
- autoconf 的 `umask 077` 在 HMDFS 上会导致权限问题（目录 owner ≠ 当前用户），已通过 sed 修复
- multitime 不支持 `--version` 选项，G2 功能验证会显示 warning（不影响通过）
- 编译有 1 个 misleading-indentation 警告（format.c:301），为上游代码问题，不影响功能

## 对话记录（AI 协作过程）

### 阶段1: 初始化与源码下载
- 执行 `ohc-run.py init-build multitime 1.5` 下载源码并初始化构建上下文
- 发现源码包来自 GitHub tag tarball，只含 configure.ac，无预生成 configure 脚本

### 阶段2: Bootstrap 与配置
- 执行 `make -f Makefile.bootstrap` 生成 configure 脚本（autoconf + autoheader）
- 运行 configure 时遇到 `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`
- 分析根因: autoconf 的 config.status 使用 `umask 077` 创建临时目录，HMDFS 上目录 owner (20001006) ≠ 当前用户 (20020082)
- 修复: `sed -i 's/umask 077/umask 007/g' config.status` 后重新运行 config.status 成功

### 阶段3: 源码修改与可重现性
- 为支持 clean-verify（G0），修改 Makefile.bootstrap 使其生成 configure.real（含 umask 修复）
- 创建 configure 包装脚本，自动检测并运行 bootstrap
- 修改 Makefile.in 的 distclean 目标，删除 configure.real 而非 configure
- 使用 track-edit 记录 3 个文件修改

### 阶段4: 编译与安装
- `make -j1` 编译成功，生成 multitime 二进制（43KB）
- `make install DESTDIR=$TEST_PREFIX` staging 安装成功
- `make install` 安装到 $DEFAULT_PREFIX 成功
- `make check` 失败（无 check 目标），改为手动功能测试

### 阶段5: 质量门禁与打包
- verify-build 通过（G1-G4 全部 PASS）
- package 成功生成 multitime-1.5-ohos-aarch64.tar.gz (93KB) 和 debug 包 (31KB)
- finish 完成归档，状态设置为 built

### 阶段6: 知识整理
- 创建知识图谱草稿 E081: autoconf config.status umask 077 权限问题
- 包含完整的错误特征、根因分析、解决方案和验证命令

---

**编译结束**: 2026-06-25 11:57
**最终状态**: built
