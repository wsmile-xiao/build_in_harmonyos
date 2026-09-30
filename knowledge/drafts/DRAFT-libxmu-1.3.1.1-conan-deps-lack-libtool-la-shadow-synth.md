# DRAFT — Conan 依赖不带 libtool `.la`：合成 shadow 目录 + 从 `.so` 反推补缺

- **来源**: libxmu 1.3.1.1（X.Org libXmu，autotools，OHOS aarch64），source_pr 13894，2026-09-30
- **同 stem 草稿**: `DRAFT-libxmu-1.3.1.1-conan-deps-lack-libtool-la-shadow-synth.kv`

## 问题

autotools + libtool 的包用 Conan 构建时，libtool 在链接阶段报：

```
libtool: error: cannot find the library '/.../libxcb.la' or unhandled argument
expected one installed libX11.la, found 0
```

触发条件很具体：**conan 从源码构建本包、而某个依赖也走源码构建**（或依赖用了会删
`.la` 的 revisions）。此时 libtool 顺着依赖的 `.la` 里的 `dependency_libs=` 递归解析
传递依赖，但 Conan 制品目录里根本没有 `.la`。

更坑的是**同一个依赖名、换一个 revisions 行为就相反**：

| 依赖 | `package()` 行为 | 结果 |
|------|-----------------|------|
| `libx11/6.4.0` | `rm("*.la")` | 制品里没有 `libX11.la` |
| `libx11/1.8.13` | 保留 `.la` | 制品里有 `libX11.la` |

于是「本地能过、CI 换 worker 就挂」，或者反过来。

## 根因

libtool 链接时不是直接找 `-lX11`，而是先找 `libX11.la`，再照它里面的
`libdir=` / `dependency_libs=` 去递归定位真实的 `.so`/`.a` 与**传递依赖**。
Conan 打包只保证 `.so`/`.a` + 头文件，不保证 `.la`；而 autotools 上游按
「依赖都有 `.la`」的传统假设写 Makefile。两边假设不一致。

## 方案（推荐，已实测）

在配方 `generate()` 里做两件事：

### 1. 合成 `libtool-shadow` 目录

对每个直接 host 依赖的 `libdir` 收集 `*.la`，复制到统一的 shadow 目录，并**改写**
里面的 `libdir=` 与 `dependency_libs=` 为 shadow 目录下的绝对路径；然后把该目录
**前置**到 `LDFLAGS`：

```python
shadow_dir = Path(self.build_folder, "libtool-shadow")
environment.prepend("LDFLAGS", f"-L{shadow_dir}", separator=" ")
```

关键点：目录里必须只剩**这一份自洽的副本**——原始 `.la` 的 `libdir=` 指向 Conan
缓存路径，直接 `-L` 加进去等于没修（会报成 `library '...\.la' was moved`）。

### 2. 缺失的 `.la` 从 `.so` 反推补出来

若某个必需 `.la` 在依赖制品里根本不存在（对方 `package()` 删过），从同名 `.so`
合成一个最小可用副本：

```text
# libX11.la - synthesized
dlname='libX11.so.6'                    # 读真实 .so 的 DT_SONAME
library_names='libX11.so.6 libX11.so'
old_library=''                          # shared-only
dependency_libs=''                      # 依赖都已进 shadow
installed=yes
libdir='<shadow_dir>'
```

两条路径都要能走通，否则依赖 revisions 一变就失败。

### 3. 必须容忍的脏 token：home 前缀的 `/usr/local/lib`

合成 shadow 时对方 `.la` 的 `dependency_libs` 里可能带一个**裸的**系统路径，
libX11 家族尤其常见：

```text
# libX11-xcb.la / libXau.la
dependency_libs=' -L/storage/Users/currentUser/usr/local/lib'
```

这是依赖包构建时一次 `make install` 落到家目录留下的 stray 路径（不带任何
`-l`）。shadow 构建器如果只**精确匹配** `/usr/local/lib` 这类系统目录，就会在
带家目录前缀的形式上判断失败并 `raise`：

```text
ConanException: libX11-xcb.la references a missing non-Conan libdir:
                /storage/Users/currentUser/usr/local/lib
```

更隐蔽的是它**跨 worker 抖动**：若该 stray 目录恰好存在于某台 worker，
「目录存在」分支会先把 token 留下而不报错；换一台没有该目录的 worker 就挂。
处置：把系统目录判定从精确匹配放宽为**后缀匹配** `*/usr/local/lib`、
`*/usr/local/lib64`（`/opt/foo/lib` 这类多段结尾不会误伤），命中后改写为
shadow `-L`。

## 验证

```bash
$ conan graph info archives/l/libxmu/1.3.1.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
# libxt/1.3.1, libx11/1.8.13, xorgproto/2025.1, libxau/1.0.11, libxcb/1.17.0,
# libxdmcp/1.1.5, libsm/1.2.6, libice/1.1.2 全部解析成功
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 产出 libXmu.so.6 (NEEDED: libXt.so.6, libXext.so.6, libX11.so.6)
#      libXmuu.so.1 (NEEDED: libX11.so.6)
```

配合 `self.requires("libx11/1.8.13", force=True)` 把整张图钉在保留 `.la` 的
revisions 上，可以让绝大多数情况直接走第 1 条路径。

## 适用边界与反例

- **适用**：autotools/libtool 项目；依赖由 Conan 提供或由 Conan 源码重建；报错指向
  某个 `.la` 找不到或被移动过。
- **不适用/反例**：CMake/Meson 项目（不走 libtool，无 `.la` 概念）；或依赖制品本身
  完整带 `.la` 且路径正确（此时不需要 shadow，加了反而多一层间接）。

## 与既有知识的关系

- `similar_to DRAFT-libtool-la-cross-package-and-private-header-deps`：那条的
  error_signature 是 `library '.*\.la' was moved`（跨包复用 `.la`），处置是改用只含
  `.a` 的干净 `-L` 目录；本条的对象是「依赖制品**压根没有** `.la`」，处置是
  **合成 shadow + 从 `.so` 反推补缺**。两者互补，触发条件与方案均不同。
- `prerequisite_of` 同批草稿 `DRAFT-libxmu-1.3.1.1-merged-but-unpublished-needs-recut`：
  那条说「为什么要重出修订号」，本条说「重出的版本怎么才能真的构建成功」。

## 查重表（四范围）

| 范围 | 结果 |
|---|---|
| 正式知识 knowledge/graph | 未命中（无 libtool shadow 合成条目） |
| 图谱 index.tsv | 未命中 |
| 草稿 knowledge/drafts/ | 命中 `DRAFT-libtool-la-cross-package-and-private-header-deps`（不同签名/方案，见上） |
| recipes catalog | libxmu 无既有制品记录 |
