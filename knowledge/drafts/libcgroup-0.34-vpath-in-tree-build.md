# DRAFT: 老式 autotools 项目无 VPATH 支持——conan basic_layout 分离构建断链

## 现象

libcgroup 0.34 conan create（basic_layout 默认 build_folder="build-release"）：

1. 链接 libcgroup.la 时 `ld.lld: error: cannot find version script libcgroup.map`
2. 构建 daemon 时 `No rule to make target '.../b/src/.libs/libcgroup.la', needed by 'cgrulesengd'`

## 根因

上游 2008 年代的 Makefile.am 假设构建发生在源码树内：

- `src/Makefile.am`：`libcgroup_la_LDFLAGS = -Wl,--version-script,libcgroup.map ...`（相对路径）
- `src/daemon/Makefile.am`、`tests/Makefile.am`：`LDADD = $(top_srcdir)/src/.libs/libcgroup.la`

conan basic_layout 默认分离构建目录（`build-release/`），VPATH 复制规则只覆盖
被 Makefile 引用为依赖/源的文件，不覆盖 LDFLAGS 里的裸文件名，也不把
`.libs` 产物路径重写。

## 修复

```python
def layout(self):
    basic_layout(self, build_folder=".")   # 强制 in-tree
```

## 通用性

任何"版本脚本/裸文件名 LDFLAGS + top_srcdir/.libs LDADD"组合的老式
autotools 项目（2005-2012 年代常见）在 conan 分离构建下都会命中。
症状链：`cannot find version script X` → 修了后又 `No rule to make
target .../.libs/X.la` → 根因都是 VPATH 不支持。
