# fakesteak 0.2.4 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools，无 configure）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 (clang version 15.0.4)
- 编译参数: CC=clang CFLAGS="-Wall -O3 -fPIC" LDLIBS="-lm"
- PREFIX: /storage/Users/currentUser/usr/local
- DESTDIR: /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4
- 状态: built

## 编译步骤（真实执行记录）

### Step 1: 初始化编译环境
```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py init-build fakesteak 0.2.4 --url=https://github.com/domsson/fakesteak/archive/refs/tags/v0.2.4.tar.gz
✅ tarball 已存在: 54KB
✅ .orig 已存在
✅ .work 已存在
✅ 基线指纹: 9 个文件
ℹ️ 历史档案: published
✅ 历史参数验证通过 (3 项)
✅ 所有依赖已就绪
✅ 环境检查通过 (TMPDIR, CC, CXX, CFLAGS, DEFAULT_PREFIX)
```

### Step 2: 检查构建系统
```bash
$ ls -la /storage/Users/currentUser/tmp/builds/fakesteak-0.2.4.work/
Makefile  LICENSE  README.md  src/  bin/  example.png  example2.png
```
- 构建系统: 简单 Makefile（无 configure 脚本、无 autotools）
- 源码结构: 单文件 `src/fakesteak.c`（924行，纯 C）
- 产出文件: `bin/fakesteak`（单个可执行文件）

### Step 3: 修改 Makefile（R20 DESTDIR + -fPIC）
原始 Makefile 不支持 DESTDIR 模式，需要修改：

**修改内容**:
1. 新增 `DESTDIR :=` 变量（默认空值）
2. `CFLAGS` 从 `-Wall -O3` 改为 `-Wall -O3 -fPIC`（鸿蒙需要 PIE）
3. install/uninstall 路径从 `$(PREFIX)/bin` 改为 `$(DESTDIR)$(PREFIX)/bin`

使用 `track-edit add fakesteak 0.2.4 Makefile` 记录编辑追踪。

### Step 4: 编译
```bash
$ cd /storage/Users/currentUser/tmp/builds/fakesteak-0.2.4.work
$ make clean && make CC=clang CFLAGS="-Wall -O3 -fPIC" LDLIBS="-lm" PREFIX=/storage/Users/currentUser/usr/local -j1
rm -f bin/fakesteak
mkdir -p bin
clang -Wall -O3 -fPIC -o bin/fakesteak src/fakesteak.c -lm
src/fakesteak.c:335:1: warning: unused function 'mat_get_ascii' [-Wunused-function]
src/fakesteak.c:353:1: warning: unused function 'mat_get_tsize' [-Wunused-function]
src/fakesteak.c:472:1: warning: unused function 'mat_debug' [-Wunused-function]
3 warnings generated.
```
✅ 编译成功

### Step 5: DESTDIR 隔离安装（R20）
```bash
$ make install CC=clang CFLAGS="-Wall -O3 -fPIC" LDLIBS="-lm" PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4
mkdir -p /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4/storage/Users/currentUser/usr/local/bin
cp bin/fakesteak /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4/storage/Users/currentUser/usr/local/bin
chmod +x /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4/storage/Users/currentUser/usr/local/bin/fakesteak
```
✅ DESTDIR 安装成功

**注意**: 首次尝试 DESTDIR 安装时遇到 `cp: Operation not permitted`，因 HMDFS 不允许覆盖已存在文件。解决方法：先 `rm -f` 旧文件再 `cp`。

### Step 6: 安全弹窗验证 (R7)
```bash
$ /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4/storage/Users/currentUser/usr/local/bin/fakesteak -V
fakesteak 0.2.4
https://github.com/domsson/fakesteak
```
✅ 安全弹窗验证通过，二进制可直接执行

### Step 7: make check（跳过）
```bash
$ make check
make: *** No rule to make target 'check'.  Stop.
```
无 check 目标，简单 demo 程序，符合预期。

### Step 8: Staging 验证
```bash
$ find /storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4 -type f | sort
/storage/Users/currentUser/tmp/test-install-fakesteak-0.2.4/storage/Users/currentUser/usr/local/bin/fakesteak

$ file .../fakesteak
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d .../fakesteak | grep NEEDED
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
```
✅ Staging 验证通过: 1个文件、ELF64 PIE、仅依赖 libc.so

### Step 9: 预编译包制作
```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py package fakesteak 0.2.4
✅ 质量门禁 ✅
✅ Step 1-9 全部完成
✅ fakesteak-0.2.4-ohos-aarch64.tar.gz: 81KB
```

打包产物内容:
```bash
$ tar tzf fakesteak-0.2.4-ohos-aarch64.tar.gz
bin/
bin/fakesteak
lib/
lib/external/
```

### Step 10: 本地安装（模拟用户部署）
```bash
$ rm -f /storage/Users/currentUser/usr/local/bin/fakesteak
$ make install CC=clang CFLAGS="-Wall -O3 -fPIC" LDLIBS="-lm" PREFIX=/storage/Users/currentUser/usr/local
mkdir -p /storage/Users/currentUser/usr/local/bin
cp bin/fakesteak /storage/Users/currentUser/usr/local/bin
chmod +x /storage/Users/currentUser/usr/local/bin/fakesteak
```

### Step 11: 用户验证
```bash
$ /storage/Users/currentUser/usr/local/bin/fakesteak -V
fakesteak 0.2.4
https://github.com/domsson/fakesteak

$ /storage/Users/currentUser/usr/local/bin/fakesteak -h
USAGE
	/storage/Users/currentUser/usr/local/bin/fakesteak [OPTIONS...]
OPTIONS
	-b	use black background color
	-d	drops ratio (1 .. 100, default: 10)
	-e	error ratio (1 .. 100, default: 2)
	-h	print this help text and exit
	-r	seed for the random number generator
	-s	speed factor (1 .. 100, default: 10)
	-V	print version information and exit
```
✅ 用户验证全部通过

### Step 12: 收尾
```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py finish fakesteak 0.2.4 published
✅ 补丁生成: 0001-Makefile.patch (+6/-5)
✅ 档案关闭: published
⚠️ G0 干净构建自动化失败（output-sync 平台限制），手动验证通过
✅ G1-G4 全通过
✅ 编译收尾完成
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 不支持 DESTDIR | 原始 Makefile install 目标使用 `$(PREFIX)/bin`，无 DESTDIR 变量 | 修改 Makefile: 新增 `DESTDIR :=`，路径改为 `$(DESTDIR)$(PREFIX)/bin`（R20 铁律） |
| 2 | CFLAGS 缺少 -fPIC | 原始 Makefile CFLAGS 仅 `-Wall -O3`，鸿蒙需要 PIE | 在 Makefile 中将 CFLAGS 改为 `-Wall -O3 -fPIC` |
| 3 | `cp: Operation not permitted` | HMDFS 文件系统限制: 不能 cp 覆盖已存在文件 | 安装前先 `rm -f` 旧文件再 `cp`（Gotchas E046） |
| 4 | 首次 verify-build G4 FAIL | manifest.yaml 缺少 `build_system` 顶层字段 | 在 manifest.yaml 中添加 `build_system: makefile` |
| 5 | G0 干净构建自动化失败 | Python subprocess 调用 make 使用 `--output-sync=target`，鸿蒙 make 不支持 | 平台限制，手动解压+应用补丁+make 验证通过 |

## 源码修改

- **0001-Makefile.patch**: 添加 DESTDIR 支持 + CFLAGS 添加 -fPIC
  - 新增 `DESTDIR :=` 变量（行4）
  - CFLAGS 从 `-Wall -O3` 改为 `-Wall -O3 -fPIC`（行3）
  - install 目标路径从 `$(PREFIX)/bin` 改为 `$(DESTDIR)$(PREFIX)/bin`（行14-17）
  - uninstall 目标路径同样修改（行20）
  - 补丁类型: platform_compat, 不需要 #ifdef __OHOS__ 守卫（修改的是 Makefile 构建规则，非 C 运行时代码，R8 不适用）

## 依赖版本

- 无外部依赖（仅 libc.so + libm）
- 编译器: clang 15.0.4
- 链接器: ld-musl-aarch64.so.1

## 验证结果

```bash
$ fakesteak -V → "fakesteak 0.2.4\nhttps://github.com/domsson/fakesteak"
$ fakesteak -h → 输出 USAGE + OPTIONS（7个选项）
$ file fakesteak → ELF shared object, 64-bit LSB arm64, dynamic (ld-musl-aarch64.so.1), not stripped
$ readelf -d fakesteak | grep NEEDED → libc.so
$ nm --defined-only fakesteak | wc -l → 25
$ ls -lh fakesteak → 26K
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fakesteak-0.2.4-ohos-aarch64.tar.gz | 81KB | 预编译包（已 strip + ELF 签名） |
| fakesteak-0.2.4-ohos-aarch64-debug.tar.gz | 26KB | 调试符号包（含 fakesteak.debug） |

## 注意事项

- 原始 Makefile 使用 `CC := cc`，鸿蒙系统无 cc 命令，需用 `CC=clang` 传递
- 原始 Makefile PREFIX 默认为 `/usr/local/`（带尾斜杠），需传递 `PREFIX=$DEFAULT_PREFIX`
- 无 configure 脚本，直接 make 编译
- 无 make check 目标（简单 demo 程序）
- 源码修改仅限 Makefile（R8: 无需 #ifdef __OHOS__ 守卫，C 文件无需任何修改）
- G0 干净构建自动化验证因 Python subprocess 平台限制（make --output-sync 不兼容）失败，手动验证通过
- fakesteak 是终端动画程序，完整功能测试需要交互式终端环境

---

**编译开始**: 2026-07-15

**编译结束**: 2026-07-15 15:46
**最终状态**: built
