# clutter-1.26.4-hmdfs-autotools-regen-guard（草稿）

## 问题形态（两个实测现场）

**形态一**：`make: *** [Makefile:586: aclocal.m4] Error 127`
```
aclocal-1.16: error: @am_AUTOM4TE@ failed with exit status: 127
sh: /usr/local/bin/autoconf: inaccessible or not found
```

**形态二**：`make: *** [Makefile:557: Makefile.in] Error 1`
```
automake-1.16: error: autoconf failed with exit status: 127
WARNING: 'automake-1.16' is missing on your system.
```

**形态三（反引号坑）**：stub 编译期
```
Package glib-2.0 was not found in the pkg-config search path.
fatal error: 'glib-object.h' file not found
```

## 根因链

1. tarball 自带 autotools 产物在 HMDFS 上表观 mtime 变化 → make 按
   `configure.ac+*.m4 → aclocal.m4 → configure`、`aclocal.m4+Makefile.am →
   Makefile.in` 依赖链判 stale → 触发重生成 → 本机无 aclocal-1.16/automake/
   autoconf 链（autom4te 127）。
2. **单趟 os.walk touch 的亚秒陷阱**：字母序让 aclocal.m4 先于 configure.ac
   落 mtime（实测差 27μs，HMDFS mtime_ns 精度可见），依赖项反超目标 → 仍判
   stale。分三趟顺序 touch 也不够：Makefile.in 层与 aclocal.m4 层的关系同样
   会被乱序破坏（形态二就是这么来的）。
3. **反引号与 env 前缀的时序**：`env PKG_CONFIG_PATH=x cmd \`pkg-config ...\``
   的命令替换由 shell 在 env 前缀生效**之前**展开——替换子 shell 看不到变量。

## 正解（四层固定递增 mtime）

```python
base_t = int(time.time()) - 3600
layers = (
    (1, ("configure.ac",), (".am", ".m4")),   # 源层（.m4 排除 aclocal.m4）
    (2, ("aclocal.m4",), ()),                  # 生成层一
    (3, ("Makefile.in", "config.h.in"), ()),   # 生成层二
    (4, ("configure",), ()),                   # 终产物
)
# 分层 os.utime(path, (base_t+offset, base_t+offset))
```

固定秒差彻底消除亚秒竞态；make 对全部重生成规则判 up-to-date。

```python
# 环境注入：export 让整个 shell（含命令替换子 shell）可见
self.run("export PKG_CONFIG_PATH=%s; clang ... `pkg-config --cflags ...`" % p,
         env="conanbuild")
```

## 配套 HMDFS 常规件（先例固化）

- confstat：`(umask 077 &&` → `(umask 000 &&`（0700 临时目录 HMDFS 不可写）
- `make -j1`：jobserver mkfifo Operation not permitted
- HMDFS 大目录遍历极慢：配方勿 os.walk 超大树，shell 勿 find ~/.conan2

## verify_builds

本 PR（clutter 1.26.4，修复后 conan create 全绿；同仓 catdoc/boa/ccze/cogl
为同族先例）。

## fallback

若四层 touch 仍触发重生成（autotools 版本差异）：改打 patch 删除 Makefile 中
的 aclocal.m4/Makefile.in/configure 重生成规则目标依赖，或 recipe 内提供
automake/autoconf 工具链（成本高，不推荐）。
