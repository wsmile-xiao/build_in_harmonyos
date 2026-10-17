# poster 20050907 — 适配笔记

## 基本信息
- 软件: poster — PostScript 海报缩放/分块打印工具（单页 PS 放大到大幅面并平铺多页打印）
- 版本: 20050907（Debian 版本号 = 上游最后更新日期 2005-09-08）
- 上游源: https://ftp.debian.org/debian/pool/main/p/poster/poster_20050907.orig.tar.gz
- sha256: 796c70554a7b00db0421ac87b77e1fcb414d547609df5c8a87399ca5e095a2e0（实测校验一致）
- License: GPL-2.0；作者 Jos van Eijndhoven (Eindhoven University of Technology, 1995)
- 源码构成: poster.c (1058 行) + getopt.c (Linux 下多余，Makefile 只编 poster.c 单文件，不参与链接) + Makefile + poster.1 (man) + README/COPYING/ChangeLog/manual.ps
- 依赖: 零 conan 依赖（仅 libc + libm，musl 自带）— 与 polyglot 同档

## 构建系统（plain 自制 Makefile，非 autotools 非 CMake）
```make
CFLAGS = -g -Wall
poster: poster.c
	gcc $(CFLAGS) -o poster poster.c -lm
install: poster
	strip poster
	cp poster /usr/local/bin
	cp poster.1 /usr/local/man/man1
```
- **坑 1（Makefile gcc 硬编码）**: 规则行写死 `gcc` 字面量而非 `$(CC)`，`make poster CC=clang` **无效**（Error 127: gcc: No such file or directory，OHOS 环境无 gcc）。实测验证。解法：build() 中 `sed -i 's/^\tgcc /\t$(CC) /' Makefile` 改写规则 + `autotools.make(target="poster", args=["-e"])` 让 Toolchain 环境（conanbuild 的 CC/CFLAGS，R33 合规）驱动构建。（初版曾用 `self.run('"${CC}" ${CFLAGS} ...')` 直编，被 W3 本地 CI 的 L0h 门禁 `shell_env_var_in_run` 拦截——CI 静态扫描禁止 self.run 里出现 ${CC}/${CFLAGS} 花括号形式，改 sed+make -e 方案后通过）
- **坑 2（install 目标不可用）**: `make install` 硬编码 strip + cp /usr/local/bin（绝对路径 + strip 会剥掉符号）。解法：package() 手动布局 staging（cp 到 $(package_folder)/bin 与 share/man/man1），不用其 install 目标。
- 无 configure；无 -Werror。

## 探索编译结果（2026-09-03）
- `clang -fPIC -O2 -Wall -o poster poster.c -lm` → **零告警零错误**，产物 aarch64 musl 动态链接 ELF（arm64, /lib/ld-musl-aarch64.so.1）
- 2005 年 K&R 风格代码在 clang 15 下无 error 级问题，无需任何补丁。getopt.c 不编译（Makefile 本来也只编 poster.c），无 getopt 冲突（poster.c 用 unistd.h 的 getopt 全局符号，musl 同样提供）。

## 运行时行为实测（关键：供 test_package 断言设计）
- **坑 3（TEMP 环境变量 / E002）**: `tmpinfile()` 使用 **`TEMP`** 环境变量（非 TMPDIR！）定位临时目录，未设置时用 `/tmp`（OHOS 只读）→ "Cannot create temporary file." exit 1。解法：运行时设置 `TEMP=$TMPDIR`（管道模式 stdin 输入会先落临时文件）。test_package 必须注入。
- 默认（无选项，stdin 输入 PS）→ rc=0，输出 PS 含：
  - `%%Creator: <myname>`
  - `%%Pages: 1`、`%%DocumentMedia: A4 595 842 0 white ()`、`%%BoundingBox: 0 0 595 842`
  - 注释行 `% Print poster ... in 1x1 tiles with 1 magnification`
  - tile 标记 `%%Page: (1,1) 1`（(row,col) 递增编号）
- `-p2x2A4` → rc=0，`%%Pages: 4` + 4 个 `%%Page: (1,1)..(1,4)` 标记 + "in 2x2 tiles with 1.8 magnification"
  - **注意 `-p` 语法**: `-p<box>` 需完整介质名（如 2x2A4）；裸 `-p2x2` 报 "Your box spec '' is not unique! (give more chars)" exit 1
- `-s2 -mA4` → rc=0，`%%Pages: 8` + "in 4x2 tiles with 2 magnification"
- `-mA2` → rc=0，`%%DocumentMedia: A2 1190 1684 0 white ()`、`%%BoundingBox: 0 0 1190 1684`
- `-v` verbose 模式输出 stderr "Using default media of A4"
- 无参 + stdin（EOF）→ rc=0（默认行为，不挂起）
- `-h` 不被识别（打印 usage，因为 usage 也是默认分支）

## 适配方案
- conanfile: package_type="application"（单二进制 CLI，polyglot 同款），requirements 空
- build(): `sed -i 's/^\tgcc /\t$(CC) /' Makefile` 改写规则 + `autotools.make(target="poster", args=["-e", "-j1"])`（chdir 到 source folder 执行；-e 让 Toolchain 环境 CC/CFLAGS 覆盖 Makefile 内置 CFLAGS；-j1 避开 HMDFS jobserver mkfifo 限制）
- package(): 手动布局 bin/poster + share/man/man1/poster.1 + share/doc/poster（README COPYING）
- package_info(): cpp_info.bindirs=["bin"]，无 libs
- commands.json（软件级，R38 CLI 应用）：-p/-m/-c/-w/-i/-s/-P/-o/-v/-f 用法
- test_package（R34 实质）：test_poster.py 断言见下
  1. 管道默认运行 rc=0 + PS 头结构（%!PS-Adobe + %%Pages: 1 + %%BoundingBox: 0 0 595 842）
  2. -p2x2A4 → %%Pages: 4 + 4 个 %%Page: tile 标记 + 2x2 tiles 注释
  3. -mA2 → DocumentMedia/BoundingBox 变为 A2 1190 1684
  4. -s2 → 4x2 tiles with 2 magnification（%%Pages: 8）
  5. 全部经 stdin→stdout 管道 + TEMP 注入

## 补丁
- 预计零补丁（编译零告警，运行时 TEMP 属环境配置非源码缺陷）
---

**编译结束**: 2026-09-03 17:43
**最终状态**: built

## PR CI 阶段记录（2026-09-03）
- PR #7945 首次 CI（build #42997, CI-019）失败，根因为 **CI worker 环境缺陷**：SDK 26.0.0.18 的 `llvm/bin/lld` 运行时加载 `libxml2.so.16` 失败（18 个 xmlXxx 符号重定位错误），clang 驱动在链接阶段即崩溃——早于任何 poster 代码链接逻辑。本机同版本 SDK lld 可正常运行（libxml2.so.16 位于 SDK `llvm/lib/`），同 conanfile 本地 conan create 全绿 + test 18/18。
- 定性依据：报错符号全属 libxml2 而非 poster；CI 墙同期多 worker 大面积环境性失败；失败点在编译已过、链接器启动瞬间。
- 处置：PR 讨论串回复根因分析 + `trigger-ci`（/rebuild）+ push 空提交 6ef4b58d75 触发重跑，期望调度到 SDK 部署完整的 worker。此坑属 CI 环境非配方问题，如重跑仍遇同 worker 同错需联系 CI 管理员。
