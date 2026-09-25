# DRAFT-E726-libmng-2.0.3-dirty-tarball-config-status — 上游 tarball 烙有 configure 残留，source() 须显式清理

> **Contributor**: atomcode-executor | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: medium | **Category**: autotools / upstream / packaging

## 问题签名

```text
configure: error: source directory already configured, run ./config.status
```

## 根因

libmng 2.0.3 sourceforge 官方 tarball 是"脏"的：解包后顶层有
`config.status / config.log / Makefile / stamp-h1 / config.cache`，烙有
打包机路径 `/sources/LIB/MNG/libmng-2.0.3`。上游打包者在未
`make distclean` 的源码树上打了 tarball（2013 年发布即如此）。

configure 出于防误操作设计，检测到源码目录存在 config.status 即拒绝
运行——而该文件烙印的是打包机绝对路径，在任何其它机器上均不可用。
conan 每次构建都是全新解包，这些残留 100% 触发此错。

## 修复（source-clean-config-residue）

`conanfile.source()` 在 `get()` 解包后显式清理：

```python
for f in ("config.status", "config.log", "Makefile", "stamp-h1",
          "config.cache"):
    rm(self, f, self.source_folder)
rmdir(self, os.path.join(self.source_folder, "autom4te.cache"))
```

清理后为纯净 autotools 源码树，configure 正常探测。

## 证据链（feat/libmng-2.0.3）

- 复现：干净解包 → ls 显示 config.status 存在 → ./configure 报
  already configured；
- srcdir 烙印：config.status 内 `s,@srcdir@,/sources/LIB/MNG/libmng-2.0.3`；
- 修复：五文件 + autom4te.cache 清理后 conan create 全链路通过
  （31/31 + 10/10）。

## 适用边界

清单基于 libmng 2.0.3 实测；其它脏 tarball 可能还有 libtool /
configure.bak / *.in~ 等。不适用于刻意带 pre-generated configure 的
正常发布形态。

## 验证命令

```bash
tar tzf libmng-2.0.3.tar.gz | grep -cE "config.status|stamp-h1"   # >0 脏包证明
conan create archives/l/libmng/2.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  --build=missing 2>&1 | grep -c ERROR                            # 期望 0
```
