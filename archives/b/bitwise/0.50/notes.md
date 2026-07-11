# bitwise 0.50 — 编译笔记

## 基本信息
- **软件**: bitwise 0.50 (终端位运算计算器)
- **源码**: https://github.com/mellowcandle/bitwise/releases/download/v0.50/bitwise-v0.50.tar.gz
- **SHA256**: 806271fa5bf31de0600315e8720004a8f529954480e991ca84a9868dc1cae97e
- **构建系统**: autotools (configure/make/make install)
- **目标平台**: aarch64-unknown-linux-ohos
- **编译器**: clang 15.0.4
- **最终状态**: published

## 编译过程

### 1. 源码准备
- 使用 init-build 下载源码到 BUILD_SRC_DIR
- 创建工作副本 bitwise-0.50.work
- 注意: Savannah URL (download.savannah.nongnu.org) 返回 404，使用 GitHub releases URL 替代

### 2. config.guess/config.sub 修补 (Patch 0001/0002)
- 问题: OHOS 平台不被识别
- 解决: 使用 patch-autotools-ohos.pl 脚本修补 config.guess
- 手动在 config.sub 的 kernel-OS 有效组合列表中添加 `linux-ohos*`

### 3. mktemp 临时目录问题 (Patch 0003)
- 问题: config.status 和 configure 脚本使用 mktemp 在 /tmp 下创建临时文件，但 OHOS 上 /tmp 只读
- 解决: 修补 mktemp 调用为使用 $TMPDIR ($HOME/tmp)
- 额外: umask 077 → umask 022（OHOS 文件系统不支持 700 权限）

### 4. config.h.in 行尾问题 (Patch 0004)
- 问题: CRLF 行尾导致 autotools 处理异常
- 解决: 统一为 LF 行尾

### 5. l64a 缺失函数 (Patch 0005/0006)
- 问题: 链接时出现 `undefined reference to l64a`
- 根因: OHOS libc (musl) 不提供 l64a() 函数
- 解决:
  - 在 src/misc.c 中实现 l64a() 函数 (Patch 0006)
  - 在 src/main.c 中添加 `extern char *l64a(long value);` 声明 (Patch 0005)
- 关键: 缺少 extern 声明时，编译器假设返回 int 而非 char*，在 aarch64 上导致指针截断和 segfault

### 6. 依赖准备
- ncurses: 预编译 .a 库可用，但头文件需从 ncurses 6.4 源码组装 (curses.h, form.h, panel.h 等)
- readline: 8.2 预编译包可用，头文件完整
- 安装路径: /storage/Users/currentUser/usr/local

### 7. 手动编译验证
```
CC=clang CFLAGS="-I/storage/Users/currentUser/usr/local/include -DNCURSES_WIDECHAR" \
LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -static" \
./configure --host=aarch64-unknown-linux-ohos --prefix=$DEFAULT_PREFIX
make -j1
make install
```
- 所有 .c 源文件编译成功
- 静态链接生成 ~1.9MB ELF binary

### 8. Conan 配方生成与修复
- conan-init 生成骨架
- 手动修复 conanfile.py:
  - R26: 不在 requires() 中引用系统预构建库（ncurses/readline），通过 CFLAGS/LDFLAGS 指向
  - R26: LDFLAGS 添加 -static 实现静态链接
  - R32: settings.os 判断使用 `in ("Linux", "OHOS")`
  - R33: build() 不依赖未定义的 shell 环境变量，所有路径在 generate() 中设置
  - basic_layout 创建 build-release/ 子目录，破坏 -I./inc 相对路径，通过 extra_cflags 补充
  - DESTDIR 嵌套修复: 显式设置 --prefix=/ 避免 AutotoolsToolchain 默认 --prefix=package_folder 与 DESTDIR 双重嵌套
- conandata.yml:
  - sources: GitHub releases URL + SHA256
  - 6 个补丁文件，名称与 patches/ 目录一致
- test_package: CLI 工具测试模式，不链接库，仅验证二进制可执行

### 9. 测试
- make check: CUnit 不可用，跳过（非编译依赖）
- Conan test_package: PASS (--version + 0xFF 转换)
- 功能测试: 13 项全部通过（详见 reports/test-report.md）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁 |
|---|------|------|----------|------|
| 1 | config.guess 不识别 OHOS | 缺少 linux-ohos 支持 | patch-autotools-ohos.pl | 0001 |
| 2 | config.sub 拒绝 linux-ohos | kernel-OS 组合列表缺失 | 手动添加 linux-ohos* | 0002 |
| 3 | mktemp 创建临时文件失败 | /tmp 只读 + umask 0700 不支持 | 修补为 $TMPDIR + umask 022 | 0003 |
| 4 | config.h.in 行尾问题 | CRLF 行尾 | 统一 LF | 0004 |
| 5 | l64a 运行时 segfault | 缺少 extern 声明导致隐式 int 返回 | 添加 extern char *l64a(long) | 0005 |
| 6 | l64a 链接错误 | musl libc 无 l64a | 在 misc.c 实现 | 0006 |
| 7 | ncurses 头文件缺失 | 预编译包无头文件 | 从 ncurses 6.4 源码组装 | - |
| 8 | Conan basic_layout 路径问题 | build-release/ 破坏 -I./inc | extra_cflags 补充 -I./inc | - |
| 9 | Conan DESTDIR 嵌套 | --prefix=package_folder + DESTDIR=package_folder | 显式设置 --prefix=/ | - |
| 10 | Savannah URL 404 | 镜像不可达 | 使用 GitHub releases URL | - |

## 知识图谱贡献
- E110: l64a() missing in OHOS libc (musl) — 新知识条目（草稿）

---

**编译结束**: 2026-07-06 20:31
**最终状态**: published
**Conan 包 ID**: bitwi4067df297a92c
