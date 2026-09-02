# kpackage/6.18.0.2 consuming karchive/6.19.0 — CMake dependency discovery (find_dependency(ZLIB)) repair (recipe layer)

> Draft: DRAFT-KPACKAGE-KARCHIVE-619-ZLIB-DISCOVERY
> Stem: `kpackage-6.18.0.2-ohos-adaptation-patterns` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-KPACKAGE-KARCHIVE-619-ZLIB-DISCOVERY
- **严重度**: 2
- **类别**: conan-recipe-dependency-graph
- **触发工具**: conan|cmake|kpackage|karchive|FindZLIB|CMakeDeps|pkg-config
- **阶段**: dependency-resolution|packaging|testing

## 错误特征

```
Could NOT find ZLIB|missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR|find_dependency\(ZLIB\)|KF6ArchiveConfig\.cmake
```

## 可复现问题

kpackage/6.18.0.2 升级到依赖 `karchive/6.19.0` 后，configure 阶段稳定失败：
`Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)`，错误由
`KF6ArchiveConfig.cmake:39 (find_dependency)` 触发。

## 根因分析

发布的 karchive/6.19.0 二进制导出的 `KF6ArchiveConfig.cmake` 无条件执行：

- `find_dependency(ZLIB)`（`KArchive_HAVE_ZLIB TRUE`）
- `find_dependency(OpenSSL)`（`KArchive_HAVE_OPENSSL TRUE`）
- `pkg_check_modules(LibZstd IMPORTED_TARGET "libzstd")`

且 `KF6ArchiveTargets.cmake` 的 `INTERFACE_LINK_LIBRARIES` 携带
`$<LINK_ONLY:ZLIB::ZLIB>`、`$<LINK_ONLY:OpenSSL::Crypto>` 和
`$<LINK_ONLY:PkgConfig::LibZstd>`。消费者配方的手写
`conan_cmakedeps_paths.cmake` 路径层只暴露直接 KF 依赖
（karchive/kcoreaddons/ki18n），从不把传递的 `zlib/1.3.1.1`、openssl、
zstd 包 root/lib/include 置入 FindZLIB/FindOpenSSL/pkg-config 的查找路径，
因此 configure 失败。

## 解决方案

**主方案**: recipe-layer-transitive-dependency-path-injection（配方层传递
依赖路径注入，非源码/补丁改动）

在消费者 conanfile.py 的 `generate()` 中：

1. `requirements()` 持有直接依赖 `karchive/6.19.0` 并新增
   `openssl/3.5.6.1`（使导出 Config 的 `find_dependency(OpenSSL)` 可满足）；
2. 将传递 `zlib/1.3.1.1` 与 openssl 的 root/lib/cmake/include 前置注入生成
   的 `conan_cmakedeps_paths.cmake`（声明式依赖元数据，非硬编码缓存路径）；
3. 将传递 zstd 的 `lib/pkgconfig` 目录前置到 `ENV{PKG_CONFIG_PATH}`
   （`set(ENV{...} ...)` 前置；`list(PREPEND ENV{...})` 不会设置环境变量）；
4. 因 karchive/6.19.0 为静态库、以裸 `-lKF6Archive` 链接且其 LINK_ONLY
   传递库不会到达链接行，向 `CMAKE_SHARED_LINKER_FLAGS` 与
   `CMAKE_EXE_LINKER_FLAGS` 追加 `-L<zlib/zstd libdir> -lz -lzstd`；
5. 保持 R05/R07 可重定位性（DT_NEEDED/RPATH/RUNPATH 无 `.conan2`/`.cache`
   机器私有路径）。

**回退方案**: upgrade-to-cmakefiledeps-propagation（将手写路径层替换为对
KF 依赖的完整 CMakeDeps 生成，让 `find_dependency` 通过生成的 config 解析）。

**禁止**: 用 `--build=missing` 替换 karchive 图、用系统 ZLIB、用 lockfile/
版本覆盖作为证据、注入硬编码 producer 缓存路径、把 karchive 降到 6.19.0
以下（R36/R37 与 clean-graph 验证模式要求精确引用）。

## 验证证据

- 干净图（R12 重跑）: 解析图含 `karchive/6.19.0#d6233ee0`、
  `zlib/1.3.1.1#9a23e7d5`、`zstd/1.5.7#83364ff4`、`openssl/3.5.6.1#d871951a`；
  `conan graph info` rc=0。
- `conan create` rc=0（configure: Found ZLIB 1.3.1 / OpenSSL 3.5.6 /
  libzstd 1.5.7）；上游 CTest 8/8、test_package 2/2。
- `conan-verify` G0-G4 / L2/L4/L5 全 PASS。
- 可重定位审计: libKF6Package.so DT_NEEDED 无 `.conan2`/`.cache` 私有路径。
- 隔离真实消费者: kpackage/6.18.0.2 + karchive/6.19.0 构建/链接/运行通过
  （`PASS: kpackage consumer ... ZLIB/ZSTD OK`）。
- 实现落地: `archives/k/kpackage/6.18.0.2/conanfile.py`（recipe 层，不改
  上游源码、不新增补丁）。

## 适用边界

- 适用: KF6 conanfile 消费者在消费静态 karchive/6.19.0 导出、且依赖手写
  CMake 路径层（而非 CMakeDeps 传播）时的 ZLIB/OpenSSL/Zstd 发现失败；
  交付实例为 kpackage/6.18.0.2。
- 不适用: 这不是源码可移植性模式；不主张平台宏；不改动上游补丁；不绕过
  cache、`--build=missing`、系统 ZLIB、lockfile、版本号或远端制品仓策略。

## 关键词

kpackage, karchive, 6.19.0, 6.18.0.2, KF6ArchiveConfig, find_dependency,
ZLIB, zlib/1.3.1.1, OpenSSL, openssl/3.5.6.1, zstd, PKG_CONFIG_PATH,
conan_cmakedeps_paths.cmake
