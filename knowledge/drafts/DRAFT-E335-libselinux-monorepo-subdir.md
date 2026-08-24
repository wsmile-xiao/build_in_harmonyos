# DRAFT-E335: Monorepo Conan 适配：子目录隔离构建（libselinux 案例）

## 场景

SELinuxProject 是 monorepo（单仓库多项目），3.10 版本的官方归档
`selinux-3.10.tar.gz` 包含 libselinux、libsepol、libsemanage、checkpolicy、
secilc、policycoreutils 等多个子项目。适配 libselinux 时，Conan recipe
的 `source()` 使用 `strip_root=True` 提取全部子项目到 source_folder，
但 `build()` 必须只构建目标子项目。

## 问题

最初 recipe 的 `build()` 方法执行 `make -C {self.source_folder}`（monorepo 根）。
顶层 Makefile 的 `SUBDIRS` 循环构建所有子项目：

```
SUBDIRS=libsepol libselinux libsemanage checkpolicy secilc policycoreutils
```

其中 libsepol 既是 monorepo 的一部分，也是 libselinux 的 Conan 依赖
（通过 `self.requires("libsepol/3.10")` 声明）。构建 libsepol 子项目时，
它使用已缓存到本地的 libsepol.a（`-l:libsepol.a`）和同目录新编译的 .lo
对象同时链接，导致 `ld.lld: error: duplicate symbol` 错误。

## 修复

`build()` 改为只构建目标子目录：

```python
# 错误：会构建 monorepo 所有子项目包括依赖
make -C {self.source_folder} ...

# 正确：只构建目标子项目
make -C {self.source_folder}/libselinux ... 
```

conandata 仍指向 monorepo 归档 URL（`strip_root=True`），`source()`
提取完整源码到 source_folder。`build()` 只进入目标子目录构建，依赖
子项目（libsepol、pcre2、musl-fts）通过 `self.requires()` 声明为
Conan 依赖，由 Conan 从制品仓或本地缓存获取。

## 验证

`conan create libselinux/3.10 --profile=default`：
- 编译通过（libselinux.a + utils 构建成功）
- 消费者 test_package 编译链接运行通过（context_new/context_str 验证）
- 无 duplicate symbol 错误

## 可复用边界

- 适用于任何 monorepo 多项目归档的 Conan 适配
- 必须确认目标库的 build 系统可以独立于 monorepo 根构建
- 依赖子项目必须已发布为 Conan 包（或本地缓存/scratch 构建）
- 已验证：SELinuxProject 3.10（libselinux）

## 本次适配复用

- E091（`-D__MUSL__` sockaddr_storage 冲突修复）成功复用，来源：acpid
- musl-fts 1.2.7 用于 OHOS musl libc 的 fts.h 替代
- E074（make jobserver mkfifo 问题）已知，不影响 |j1| 构建