# E663-dist-tarball-maintainer-rules-touch-t：make-dist 发行物在无 automake 的 worker 上被 maintainer 规则触发重生成失败

> Contributor: lnav-0.13.2 任务 | Status: Draft | Updated: 2026-09-22
> Source: lnav 0.13.2 适配（feat/lnav-0.13.2）
> 对应：`knowledge/drafts/E663-dist-tarball-maintainer-rules-touch-t.kv`

## 现象

包的 tarball 是 autotools `make dist` 发行物（自带 `configure`、`Makefile.in`、
`config.guess`/`config.sub`），本该"免自举直接 configure"。但在 OHOS worker/
设备上 `make` 开始后出现：

```console
WARNING: 'aclocal-1.16' is missing on your system.
cd . && /bin/sh ./missing aclocal-1.16 ...
aclocal: No such file or directory
make: *** [Makefile:...: aclocal.m4] Error 127
```

或 `automake-1.16 is missing` / `autoconf` 版本串同型。特征：**失败的不是编译，
而是 make 在编译前试图"重新生成构建系统"**。

## 根因

automake 生成的 `Makefile.in` 内嵌 maintainer 规则（`am--refresh` 族）：

```makefile
$(srcdir)/Makefile.in:  $(srcdir)/Makefile.am  $(srcdir)/configure.ac ...
	@case '$(am__configure_deps)' in ... $(ACLOCAL) ...
```

当 make 判定时间戳倒挂（`configure.ac` 比 `aclocal.m4`/`configure` 新、或
`configure` 比 `Makefile.in` 新）就自动重跑 aclocal/automake/autoconf。触发面
**不止手工改源码**：

- conan `source()` 解包的 mtime、HMDFS 落盘时间粒度、抽取顺序都可能倒挂；
- 即便 tarball 内时间戳有序，任何先于 configure 触摸过的文件（如补丁工具
  重写 `configure.ac`）都会把链条点着。

OHOS worker PATH 没有 automake（device-facts §一.4），规则必然失败——
**「自带 configure」不等于「不会重生成」**。

## 修法（推荐）

构建前按依赖序用**显式分钟级时间戳**归一（`touch -t`，规避同秒 mtime 竞态）：

```console
configure.ac(最旧) → *.m4 → aclocal.m4 → configure → config.h.in → Makefile.in(最新)
```

全部落后于生成物后，make 判定一切最新，maintainer 规则永不触发。五行配置内
循环，不改源码内容、无补丁、免 automake `tool_requires`。

```python
# conanfile.py build() 开头（src = source_folder）
seq = [("configure.ac", "202601010000.00"), ("**/*.m4", "202601010001.00"),
       ("aclocal.m4", "202601010002.00"), ("configure", "202601010003.00"),
       ("**/config.h.in", "202601010004.00"), ("**/Makefile.in", "202601010005.00")]
import glob, os
for pat, stamp in seq:
    for p in glob.glob(os.path.join(src, pat), recursive=True):
        os.system(f'touch -t {stamp} "{p}"')
```

## 兜底

`tool_requires("automake/1.18")` 让规则真跑成功——但发行物通常不带 m4 源，
真重生成会因缺输入而失败；且会引入 conan autoconf/perl 的 PERL5LIB 毒丸
（device-facts §一.23）。仅当确需改 `configure.ac` 并重打 configure 时使用。

## 禁止

- 不带时间戳的裸 `find -exec touch`（同秒粒度下顺序不保证，随机复现）；
- 补丁/手改 `Makefile.in`（生成物，R6；每个子目录一份，补丁面爆炸）。

## 复现/验证

```console
grep -n 'am--refresh\|\$(ACLOCAL)' <包>/Makefile.in | head -3   # 规则确实在
# 构建日志：不再出现 "is missing on your system"
```
