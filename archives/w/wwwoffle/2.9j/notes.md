# wwwoffle 2.9j — 适配笔记

## 软件信息
- WWW Offline Explorer：一个带缓存的 HTTP/FTP/finger 代理服务器，用于拨号/离线浏览。
- 官网：http://www.gedanken.org.uk/software/wwwoffle/
- 许可证：GPL-2.0-or-later
- 构建系统：Autotools（C 项目）

## 本阶段（创建归档，fixing_verification）
本轮目标是修复真机预检的 evidence 阶段失败（“无法读取当前 archive 代码树”）。
根因：工作树为空，`archives/w/wwwoffle/` 尚未建立，preflight 找不到归档代码树。

本轮创建了完整归档：
- `archives/w/wwwoffle/{manifest.yaml,README.md,commands.json}`
- `archives/w/wwwoffle/2.9j/{conanfile.py,conandata.yml,manifest.yaml,notes.md}`
- `archives/w/wwwoffle/2.9j/test_package/{conanfile.py,test.sh,MANIFEST.yml}`
- `archives/w/wwwoffle/2.9j/patches/0001-config.guess.patch,0002-config.sub.patch`

## 源码
- 官方 URL：http://www.gedanken.org.uk/software/wwwoffle/download/wwwoffle-2.9j.tgz
- sha256：b16dd2549dd47834805343025638c06a0d67f8ea7022101c0ce2b6847ba011c6

## OHOS 适配要点
1. **config.guess/config.sub 过旧**（2010 年版）：
   - 不认识 `aarch64` CPU，也不认识 HarmonyOS/OHOS 系统。
   - 采用 addrwatch/bash 同款思路：替换为现代版本（autoconf 1.16 / automake 2022 版，识别 aarch64）。
   - 在 modern config.guess 中插入 `aarch64:OHOS:*:* | aarch64:HarmonyOS:*:*` 分支，uname 报 OHOS 时产出 `aarch64-unknown-linux-ohos`。
   - 在 modern config.sub 中接受 `ohos*` OS 与 `linux-ohos*` 内核组合。
   - 已在本机验证：`sh -n` 语法 OK；`config.sub aarch64-unknown-linux-ohos` 返回原值；模拟 uname(aarch64/OHOS) 时 config.guess 输出 `aarch64-unknown-linux-ohos`。
2. **可选依赖关闭**：`--with-zlib=no --with-gnutls=no --with-gcrypt=no`，减少 OHOS 外部依赖面。ipv6 保持默认开启（OHOS 提供 getaddrinfo/getnameinfo）。
3. **链接方式**：wwwoffle 为独立工具（非系统同名库），不强制 `-static`（R26 仅针对系统同名库），避免 OHOS 静态 libc 缺失导致链接失败。
4. **package()**：`make install` 会装到 /etc、/var 并跑 fixup-install.sh，不适合打包；改为直接复制 wwwoffle、wwwoffle-tools 到 bin/，wwwoffled 到 sbin/，并建 wwwoffle-tools 的 9 个多调用软链。
5. **HMDFS getcwd 失败**：真机 configure 报 `configure: error: working directory cannot be determined`（大量 `getcwd: cannot access parent directories`）。这是 HMDFS 下 out-of-source VPATH 构建目录 getcwd 系统调用失败（viennarna 同款经验）。修复：
   - build() 开头 `os.chdir(self.build_folder)`（失败不阻断）+ `os.environ["PWD"] = self.build_folder` 预置逻辑路径。
   - 补丁 `0003-configure-pwd.patch`：configure 的 `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"`，让 `pwd` 失败时回退到逻辑 $PWD。

## 上游测试
- 上游**没有 `make check` 目标**。`src/testprogs/` 下随 `make` 编译了 5 个诊断测试程序：
  `test-doc`、`test-msg`、`test-modify`、`test-gif`、`test-io`（见 src/testprogs/README）。
- 这些程序是手动诊断工具（非断言框架）：按传入输入做解析/IO 并返回 0；出错时 Fatal→`exit(2)`。
- 接入方式：conanfile.py `build()` 末尾逐个运行 5 个程序并打印确定性
  `HMBS_UPSTREAM_TESTS <name>: PASS/FAIL (exit=rc)` 行。
  - test-io：先写入 file.txt 作为输入（自包含 IO 回环）。
  - test-msg：`./test-msg PageNotFound` 渲染错误页模板。
  - test-doc/test-modify：喂一段 HTML 到 stdin + http://localhost/ URL（依赖同目录 wwwoffle.conf，来自源码包）。
  - test-gif：喂一个 1x1 透明 GIF 到 stdin。
- 计数字段以真机预检实际运行为准；本机不做字符串数数补丁。

## 验证状态
- 本机：config 补丁应用/语法/三元组实测通过；conanfile.py `py_compile` 通过；0003-configure-pwd.patch `patch -p1 --dry-run` 对官方 configure 干净应用。
- 真机编译、test_package 与上游测试：待 HMBS 本轮结束后的真机预检复跑验证。

## 本轮（真机 compile 失败：0003 补丁应用失败修复）
- 复现证据：真机 `apply_conandata_patches(self)`（build() 第 69 行）报 `ConanException: Failed to apply patch: .../0003-configure-pwd.patch`；日志只打印 `--- b'wwwoffle-2.9j/configure' +++ b'...configure.new'` 两个文件头即失败（说明 Conan 内部 Python patcher 在解析该 diff 头时失败）。
- 根因：0003 补丁由 `diff -u` 生成，diff 头带真实时间戳（`--- wwwoffle-2.9j/configure\t2016-... +0000`、`+++ wwwoffle-2.9j/configure.new\t2026-... +0000`），与 0001/0002 使用的 `diff -ruN` 无时间戳头（`--- a/config.guess` / `+++ b/config.guess`）格式不一致。`apply_conandata_patches` 按顺序应用，0001/0002（config.guess/config.sub）成功，0003（configure）因 Conan 内部 patcher 不兼容该时间戳 diff 头而失败。GNU `patch -p1` 兼容两者，故本地 dry-run 通过但 Conan 内建应用失败。
- 方案（复用 0001/0002 已验证可被 Conan 应用的格式）：
  1. 将 `0003-configure-pwd.patch` 重写为与 0001/0002 相同的 `diff -ruN a/x b/x` 无时间戳头格式（`--- a/configure` / `+++ b/configure`），正文 hunk（第 1200 行 `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"`）不变；
  2. 本机 3 个补丁对官方源码 `patch -p1 --dry-run` 全部干净应用验证通过。
- 聚合经验 #1（conan init tools.env:defines）reject：该经验是 conan global.conf 启动期 conf 污染（tools.env:defines 非法 conf），与本轮 configure 补丁的 diff 头格式不兼容导致的 apply 失败完全不同，签名不匹配。

## 本轮（真机 compile 失败：config.status mktemp 临时目录写失败修复）
- 复现证据：configure 成功生成 `config.status`，但 `./config.status` 执行时 `./config.status: line 609: ./confADENPo/subs1.awk: Permission denied`，随后 `config.status: error: could not setup config files machinery`，`autotools.configure()` 退出 1（build() 第 72 行）。
- 根因（E206/E112 同源）：HarmonyOS HMFS 上，`config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，因 setgid 目录继承了父目录的 owner uid，但当前 uid 非该 owner；目录权限仅 0700，当前用户写好 `subs1.awk` 被拒。configure 脚本自带 `|| { tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp"); }` 回退分支——若 mktemp 返回失败，会用普通 `mkdir` 建当前用户拥有的目录，写入即可成功。
- 方案尝试一（PATH shim，失败，已废弃）：新增 `_configure_with_mktemp_fallback(autotools)`，在 `HMBS_AUTOCONF_MKTEMP_FALLBACK==1` 时前置一个 `exit 1` 的 mktemp shim 到 PATH 再调 configure。真机复跑仍失败：config.status 仍用真实 mktemp（临时目录名 `confAnOJAi` 为 mktemp 随机名，非 mkdir 回退的 `conf$-$RANDOM`），说明 Conan `run()` 的 buildenv/runenv 管理未沿用我前置的 PATH shim——运行时环境注入不可靠。
- 方案二（最终，configure 脚本级绕过 mktemp，采用不同策略）：改为**补丁 configure 脚本本身**，删除对运行时 env 的依赖——
  1. 新增 `0004-configure-mktemp-fallback.patch`：把 configure 中建 config.status 临时目录的首分支 `tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`` && `test -d "$tmp"` 改为 `tmp=` / `false`，强制进入 `|| { tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp"); }` mkdir 回退（建当前用户拥有、可写的目录）；
  2. 关键点：该块位于 configure 的 `cat >>$CONFIG_STATUS <<\_ACEOF ... _ACEOF` heredoc 内，是 config.status 运行时真实执行的代码，打补丁 configure 即可同时修复 configure 与生成后的 config.status，无需运行时 env；
  3. conandata.yml patches 增加 0004 条目；build() 恢复为普通 `autotools.configure()`，移除已失败的 shim 方法；
  4. 本机 4 个补丁对官方源码依序 `patch -p1` 全部干净应用，configure `sh -n` 通过（pwd 修复在 1203，mktemp 修复在 5724）。
- 聚合经验 #1（conan init tools.env:defines）reject：本失败是 configure/config.status 运行时 HMFS 临时目录权限问题，非 conan global.conf 启动期 conf 污染，签名不同。


- flex/lex 是构建硬依赖（configure `AC_PROG_LEX`），若真机 CI 缺 flex，需补充/内置。
- 后续可选：开启 zlib/gnutls 以提供压缩/HTTPS 能力（需相应依赖已发布）。

## 本轮（真机 compile 失败：0004 补丁应用失败 修复）
- 复现证据：真机 `apply_conandata_patches` 报 `0004-configure-mktemp-fallback.patch: actual : b''` / `source file is different - b'configure'`，build() 第 69 行 `ConanException: Failed to apply patch`。0001/0002/0003 均成功，仅 0004 失败。
- 根因：`0004` 补丁的 hunk 头 `@@ -5724,4 +5724,4 @@` 起始行号 **差 1**。官方 configure 在目标代码块前实际有**一个空行**：`# Create a (secure) tmp...`(5723) → 空行(5724) → `{`(5725) → `tmp=`(5726)…。hunk 头声明 startsrc=5724 期望该处为 `{`，但实际 5724 是空行、`{` 在 5725。Conan 使用的 Python `patch` 库**严格按 hunk 头行号定位、不做上下文搜索**，因此逐行比对行 5724（空 `b''`）与期望首上下文 `{` 不匹配，输出 `actual: b''`。此前 GNU `patch -p1 --dry-run` 通过是因为 GNU patch 会按上下文搜索，掩盖了这一行号偏差。
- 方案：把 `0004` 的 hunk 头从 `@@ -5724,4 +5724,4 @@` 改为 `@@ -5725,4 +5725,4 @@`，正文不变。验证：本机用与 Conan 同源的 Python `patch` 库按 0001→0002→0003→0004 顺序全部应用成功（此前 0004 返回 False），重打后 configure 含 `{ tmp= / false }` 强制 mkdir 回退块，`bash -n configure` 通过，GNU `patch -p1` 也干净应用。
- 经验：给 configure 这类大文件写补丁时，锚点行号必须对照真实文件（注意空行），并务必用 Conan 同源 Python `patch` 库验证，不能只信 GNU patch 的 dry-run。

## 本轮（真机 compile 失败：No rule to make target 'wwwoffled.c' 修复）
- 复现证据：真机 build() 第 73 行 `autotools.make()` 失败：`make[1]: *** No rule to make target 'wwwoffled.c', needed by 'wwwoffled.o'.  Stop.`，发生于 `.../build-release/src`（out-of-source 单独 build 目录）。
- 根因：wwwoffle 的 Makefile（Makefile.in / src/Makefile.in）为**手写、无 VPATH**（全树 `grep VPATH` 为空），不支持 out-of-source 构建。而 conanfile 使用 `basic_layout`（生成独立 `build-release` 目录）+ `Autotools` 做 out-of-source 构建：`make` 在 build-release/src 下找不到任何源文件（`wwwoffled.c` 为首个被编译项），报 No rule to make target。本机复现：out-of-source `configure` 后 `make` 精确复现同一错误；in-source `./configure`+`make` 则完整编译出 wwwoffle/wwwoffled/wwwoffle-tools 与 5 个 testprogs（make rc=0）。
- 方案：
  1. `layout()` 改用 in-source（复用仓库 `at` 同款已验证模式）：`basic_layout(self, src_folder=".")` + `self.folders.build = "."`，configure/make 直接在源码目录执行；
  2. `package()` 的二进制路径从 `self.build_folder` 改为 `self.build_folder/src`（in-source 下 make 在 src/ 生成 wwwoffle 等）；
  3. 保留 0003/0004 补丁（in-source 下仍防御性有效：HKDFS getcwd 与 config.status 临时目录权限）。
- 补齐真机门禁必需的两个 JSON 证据标记（此前缺失）：
  1. `test_package/test.sh` 结束时输出 `HMBS_TEST_PACKAGE_RESULT={...}`（discovered=1/passedCount=1，为真实 wwwoffle --version 用例）；
  2. `_run_upstream_tests` 聚合 5 个 testprogs 真实退出码，输出 `HMBS_UPSTREAM_TEST_RESULT={...}`；计数唯一来源为各测试程序实际 exit code（passed+failed==executed==5 恒等自检）。
- 上游测试诚实口径：test-io/test-modify/test-gif 为自包含测试（本机实测均 PASS）；test-msg/test-doc 直接调 HTMLMessageBody/Document 自身不加载配置，未配置 /etc/wwwoffle/wwwoffle.conf（定义 Protocol）时 configfunc.c `GetLocalURL()` 的 `strlen(localproto=NULL)` 段错误（本机 gdb 实测 bt：`#1 GetLocalURL configfunc.c:228 → #2 html_message_body messages.l:381`），为上游诊断工具固有运行环境限制，按 environment 缺口计入 gaps，不伪装通过。

## 本轮（真机 evidence：test_package 失败 wwwoffle: inaccessible or not found 修复）
- 复现证据（真机 preflight stdout）：
  ```
  === wwwoffle --version ===
  test.sh[17]: wwwoffle: inaccessible or not found
  FAIL: wwwoffle --version exited non-zero
  HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,...,"discovered":1,"passedCount":0}
  ERROR: wwwoffle/2.9j (test package): Error in test() method, line 17
  ```
- 同时上游测试（build 内）4/5 通过、test-msg 按 environment 缺口如实计入 gaps（configfunc.c GetLocalURL()
  strlen(localproto=NULL)，诊断工具不加载配置固有段错误）——该部分已诚实、无需改动。
- 根因：test_package 原实现 `self.run("sh test.sh")` 依赖 `sh`（PATH 上的 mksh/toybox）+ VirtualRunEnv PATH
  查找打包后的 ELF `wwwoffle`。在 OHOS 上对打包 ELF 用该方式执行会报 "wwwoffle: inaccessible or not found"
  （打包二进制在 pakage_folder/bin 下存在且 copy() 用 shutil.copy2 保留了可执行位，问题出在调用方式）。
- 方案（复用仓库已验证的可执行配方范式 templates/test_package-executable 与 archives/k/keychain）：
  1. test_package/conanfile.py test()：用 `self.dependencies["wwwoffle"].package_folder` 取打包二进制绝对路径，
     再用 bash（CONFIG_SHELL，默认 /data/service/hnp/bin/bash）执行 test.sh，并把二进制绝对路径作为参数传入；
  2. test_package/test.sh：改为 `test.sh <wwwoffle-binary> [<wwwoffle-tools-binary>]`，对 `"$1" --version`
     做真实执行（wwwoffle --version 独立打印 "wwwoffle version 2.9j"，exit 0，无需配置）；计数唯一来源为该真实执行。
  3. 更新 notes/MANIFEST/pr-body 审计口径。
