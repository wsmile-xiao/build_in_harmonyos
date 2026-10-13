# DRAFT: pkg-config「发现 ≠ 消费」——上游 CMake 不接线 `*_INCLUDE_DIRS/*_LIBRARY_DIRS`

- **id**: `DRAFT-ohos-pkgconfig-consumption-gap-include-library-dirs`
- **软件事件源**: librepo 1.18.0 适配（任务 contrib-14940），同库 4 处实例
- **查重**（2026-10-08，`node tools/kb-check.mjs`）：`LIBRARY_DIRS` 0 / `zck.h` 0 /
  `unable to find` 0 → **真缺口**；四个邻居子族边界见 §4
- **状态**: draft（`draft: true`、`contributor_id: frj__`）

## 1. 一句话机理

`PKG_CHECK_MODULES(<P> <mod>)` 成功只是「发现」，它产出 `_INCLUDE_DIRS / _LIBRARY_DIRS /
_LIBRARIES` 三组变量；上游在 Linux 单前缀世界（一切都在 /usr）养成的习惯是只拿
`_LIBRARIES` 去链接、**从不接线另外两组**——conan 把依赖拆进各自 `package_folder`
后，头文件与 `-l` 名同时脱离默认搜索路径，编译/链接双炸，而 configure 阶段全绿。

## 2. 实测证据（librepo 1.18.0，OHOS 真机，2026-10-08，三轮 `conan create` 日志）

| 阶段 | 修复前（原文） | 修复后 |
|---|---|---|
| configure | `Checking for module 'zck>=0.9.11'` → 全部通过（glib/libxml-2.0/openssl/check/zck 都 FOUND） | 同样全过 |
| 编译 | `fatal error: 'zck.h' file not found`（zchunk 头）；`fatal error: 'check.h' file not found`（tests，上游此处本就只有一行被注释的 `#INCLUDE_DIRECTORIES(${CHECK_INCLUDE_DIR})`）；`fatal error: 'gpg-error.h' file not found`（gpgme.h 内嵌，include 需双前缀） | 全部编译通过 |
| 链接 | `ld.lld: error: unable to find library -lxml2 / -lcrypto / -lgio-2.0 / -lgobject-2.0 / -lgmodule-2.0 / -lglib-2.0 / -lzck / -lzstd / -lcurl / -lssl / -largp`（20 行全列表在构建日志） | `Linking C shared library librepo.so` 成功 |

修复 = 一个 portability patch 的 5 处接线（顶层 `INCLUDE_DIRECTORIES(${GPGME_INCLUDES})`、
`INCLUDE_DIRECTORIES(${ZCHUNKLIB_INCLUDE_DIRS})`、`LINK_DIRECTORIES(4 组 *_LIBRARY_DIRS)`、
tests 的 `INCLUDE_DIRECTORIES(${LIBCHECK_INCLUDE_DIRS})`）。

## 3. 通用性证据（一类，非单库）

**main 已合入、各自手搓同一补丁而图谱无条目的配方**（`git grep` 于 2026-10-08）：

| 配方 | 补丁 | 内容 |
|---|---|---|
| ciftilib 1.6.0 | `0003-pkgconfig-conan-libs.patch` | 同时补 `INCLUDE_DIRECTORIES(${PC_LIBXMLPP_CONAN_INCLUDE_DIRS})` + `LINK_DIRECTORIES(${PC_LIBXMLPP_CONAN_LIBRARY_DIRS})`（与本条修法逐字同构） |
| ayatana-common 0.9.11 | `0003-link-glib-libdirs.patch` | glib libdirs 接线 |
| ayatana-indicator-display 26.6.0 / -keyboard 26.6.2 / -messages 24.5.2 | `0002/0008/0004-link-deps-library-dirs` | 依赖 libdirs 接线 |
| avro-c 1.12.0 | `0001-lang-c-CMakeLists.txt.patch` | 同族 |
| jshn 2025.11.14 | notes 载 `TARGET_LINK_DIRECTORIES(blobmsg_json PRIVATE ${JSONC_LIBRARY_DIRS})` | 同族（target 级写法） |
| blur 1.1.3 / cassiopee 1.0.9 / rcon 0.6 / ustream-ssl 20260222-r0 | 各自 CMakeLists patch | 同族 |

加上 librepo 的同库 4 处实例，共 **≥9 个独立软件、10+ 处实例**——高发而无人入库，
正是本条要补的缺口。

## 4. 判别树与邻居边界（为何不是已覆盖）

```
pkg-config 相关故障四层定位：
1) 发现层：模块/pc 找不到（No package 'x' found）      → E468（PKG_CONFIG_PATH/generators）、E348（.pc 命名/转发）
2) 环境陷阱：--cflags 输出为空（-I 被过滤）            → E075（C_INCLUDE_PATH 陷阱；探针：pkg-config --cflags 为空）
3) 生成层（meson）：PkgConfigDeps 产物不够用            → DRAFT-13572-pangomm gap-trio（自定义 pc 变量/别名 pc/find_library，
                                                          修在配方 generate()，禁改上游）
4) 消费层（CMake，本条）：变量齐全、上游没接线           → 探针：--cflags 非空 + CMakeLists 只 grep 到 _LIBRARIES；修在上游源补丁
5) 记录层：链接用了绝对路径/SONAME 缺失                 → E537（探针：link 行/DT_NEEDED 里是绝对路径）
另：E480=头文件级依赖的 conan transitive_headers 消费法（conan 侧解法）、
    E384=手写 configure 的 pkg-config 探测（autotools 侧）——不同构建系统侧。
```

与 pangomm gap-trio 的分界要点：同为「库在 conan 前缀里链接不到」的表象，但
pangomm③（find_library）是 meson 探测 + **配方 generate() 注入 -L**（其 forbid_1
明确禁改上游）；本条是 CMake `TARGET_LINK_LIBRARIES(${P_LIBRARIES})` 裸 -l 名 +
**必须在上游 CMakeLists 补 LINK_DIRECTORIES/INCLUDE_DIRECTORIES**——生成物完整、
坏在上游消费习惯，配方侧无等价注入点（CMake 的 link_directories 必须出现在
add_library 之前的源码作用域里）。

本条与四邻居的**分流探针**：`pkg-config --cflags <mod>` 非空（排除 E075）、
`--exists` 成功（排除 E468/E348）、上游源里 `_LIBRARIES` 有消费而
`_INCLUDE_DIRS/_LIBRARY_DIRS` 零接线（本条特征）、链接命令行无绝对路径（排除 E537）。

## 5. 推荐修法

```cmake
# 上游 CMakeLists（或配方 patch）：
INCLUDE_DIRECTORIES(${<P>_INCLUDE_DIRS})
LINK_DIRECTORIES(${<P>_LIBRARY_DIRS})
# 或 target 级：TARGET_LINK_DIRECTORIES(<tgt> PRIVATE ${<P>_LIBRARY_DIRS})
```

禁用项：不要用 `C_INCLUDE_PATH`「修」头文件找不到（落入 E075）；不要事后
patchelf（本条链接根本没成功，与 E537 的记录层问题是两层）。

## 6. 关联

- 软件 PR：【知识库扩展】librepo 1.18.0 适配完成（补丁 `0001-ohos-build-adjustments.patch`
  即本条修法的完整实例）
- issue：【知识库扩展】librepo 1.18.0：pkg-config「发现≠消费」消费层缺口（本 PR 关联）
