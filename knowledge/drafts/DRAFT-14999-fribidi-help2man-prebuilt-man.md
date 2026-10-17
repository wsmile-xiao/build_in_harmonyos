# DRAFT-14999-fribidi-help2man-prebuilt-man：help2man 构建期缺失与 tarball 预生成 man page 保留方案

## 错误特征

构建 autotools 发行 tarball（fribidi 1.0.17 为例）在无 help2man 的环境（OHOS CI worker、最小化容器）下，make 阶段死于：

```
  GEN      fribidi.1
../missing[85]: help2man: inaccessible or not found
WARNING: 'help2man' is missing on your system.
         You should only need it if you modified a dependency of a man page.
         You may want to install the GNU Help2man package:
         <https://www.gnu.org/software/help2man/>
make[2]: *** [Makefile:839: fribidi.1] Error 127
```

机器可匹配签名（error_signature）：
- `help2man: inaccessible or not found`
- `missing --run help2man`
- `*** [Makefile:*: *.1] Error 127`
- `WARNING: 'help2man' is missing on your system`

## 根因（root_cause）

1. 上游在 `bin/Makefile.am` 新增（fribidi 1.0.17 起为代表）：
   ```makefile
   dist_man_MANS = $(bin_PROGRAMS:=.1)
   %.1: %
   	$(top_srcdir)/missing --run help2man ./$< --no-info \
   	--version-string=- -n "$(shell ./$< --help | head -n 2 | tail -n 1)" \
   	--output=$@
   ```
2. 发行 tarball 自带预生成 `bin/fribidi.1`（dist 分发），本可直接安装；
3. 但 make 链接出二进制后，二进制 mtime 晚于预生成 man page，automake 触发 `%.1: %` 重生成；
4. `missing --run` 包装器在工具缺失时透传 127 退出码 → make Error 127 中断。

影响面：一切采用"help2man 按需生成 man"的 GNU 风格 autotools 项目（fribidi ≥1.0.17、man-db、ed、sharutils 等）在受限构建环境下的交付。

## 解法（solution）

补丁删除 `bin/Makefile.in` 的 `%.1: %` 规则块，直接采用 tarball 预生成 man page：

```diff
--- a/bin/Makefile.in
+++ b/bin/Makefile.in
@@ -835,11 +835,6 @@
 $(top_builddir)/lib/libfribidi.la:
 	cd $(top_builddir)/lib && $(MAKE) $(AM_MAKEFLAGS) libfribidi.la

-%.1: %
-	$(top_srcdir)/missing --run help2man ./$< --no-info \
-	--version-string=- -n "$(shell ./$< --help | head -n 2 | tail -n 1)" \
-	--output=$@
-
 -include $(top_srcdir)/git.mk
```

- 补丁以 difflib（unified diff, n=3）对 tarball 内实际 Makefile.in 生成，登记在 conandata.yml（patch_type: portability）；
- 结果：`make install` 正常交付 `share/man/man1/fribidi.1`（预生成页随 dist 安装路径走），make check 全 PASS。

## 降级方案（fallback）

仅当源码修改导致必须重新生成 man page 时：
1. 构建环境安装 help2man（有包管理器时）；
2. 或手工从 `./progname --help` 输出构造 troff 源替换预生成页；
3. 或使用上游提供的 configure 开关跳过 man 交付。
纯版本升级适配（不修改 CLI 行为）一律走主方案。

## 验证（verify_builds）

- PR #14999（fribidi 1.0.17，HarmonyOS PC aarch64）：
  - 本地探索构建：configure/make/make check（4 目标全 PASS）/make install 全链 rc=0；
  - conan create -pr=ohos-aarch64 全绿：补丁应用成功、share/man/man1/fribidi.1 交付、test_package 4 断言 PASS；
  - 失败复现：不打该补丁时 make 死于 `make[2]: *** [Makefile:839: fribidi.1] Error 127`（探索构建首轮实锤）。

## 与已有条目的关系（查重）

- E289（`HELP2MAN, man_MANS, cannot stat, install-man`，install 期）：处理"安装清单与产物不一致"——修法是清空 automake man 列表**放弃 man 交付**；
- 本条（build 期 Error 127）：处理"构建期工具缺失"——修法是删重生成规则**保留预生成 man 交付**；
- 同域（help2man/man_MANS）不同阶段（install vs build）不同目标（放弃 vs 保留），互补解法，构成增量。

## 红线

- 禁止在 conanfile.py 里硬编码安装 help2man（worker 无 pip 权限场景会二次失败）；
- 补丁只删规则块，不动 `dist_man_MANS` 安装清单（动了会连带丢 man 交付，退化成 E289 场景）。
