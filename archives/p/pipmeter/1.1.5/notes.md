# pipmeter 1.1.5 编译笔记

## 版本信息

- 编译版本：1.1.5（上游最新稳定版，2021-01-09 发布）
- 源码来源：https://launchpad.net/pipemeter （trunk/1.1.5 下载页官方归档）
- 源码包：pipemeter-1.1.5.tar.gz（149052 字节，sha256 e470ac5f…ab2e87d8）
- 作者：Clint Byrum，许可证 GPL-2.0-or-later
- 认领身份：GitCode 用户名 gcw_6a3w2yXz，队伍名称 来都来了

## 构建系统

- Autotools（autoconf 2.59 预生成 configure，tarball 自带，无需 autoconf）
- 单文件 C 程序 pipemeter.c + Makefile.in，无第三方依赖
- configure.in 未使用 AC_CANONICAL_HOST，tarball 内无 config.sub/config.guess 依赖
- 安装产物：bin/pipemeter（可执行文件）+ share/man/man1/pipemeter.1（手册页）

## 遇到的问题

### 1. HMDFS umask 权限问题（E011，同 pv/1.7.24）

- autoconf 2.59 生成的 configure 含 `umask 077 && mktemp -d`，在 HMDFS 上失败
- 修复：build() 内 `sed -i 's/umask 077/umask 022/g' configure`（R6：configure 为生成文件，不进 patches/）

### 2. Makefile.in 无 VPATH，不支持 out-of-source 构建

- `pipemeter: pipemeter.c` 要求源码与构建同目录
- 修复：build() 内 `chdir(source_folder)` 做 in-source 构建

### 3. 上游 make install 依赖 GNU install -Dp -t

- OHOS 精简环境无 GNU install -D/-t 组合
- 修复：package() 内用 copy() 直接安装二进制与手册页，不调用 make install

## 上游测试审计结论：无自动化测试

- Makefile.in 目标仅 all/debug/clean/distclean/install/dist，无 check/TESTS 目标
- testscript.sh 为手工基准脚本（生成 200M 文件、依赖 /usr/bin/time 与 /proc/cpuinfo、把 results.txt 邮件发给作者），不可自动化
- test_package/MANIFEST.yml 已写入 upstream_tests_exist: false 及完整审计，build() 不运行 make check

## test_package 功能测试（4 个真实用例）

1. `pipemeter -V` 输出含 1.1.5，退出码 0
2. stdin->stdout 2 MiB 透传与输入字节完全一致（cmp，前置非空断言防空对空）
3. `-s SIZE` 进度模式数据一致且 stderr 含百分号进度
4. `-f 文件` 模式输出与输入文件一致（cmp）

## 编译状态

- configure：待真机预检
- make：待真机预检
- conan create（含 test_package）：待 HMBS 真机预检
- 最终状态：built（工作树未提交，等待真机全部门禁）
