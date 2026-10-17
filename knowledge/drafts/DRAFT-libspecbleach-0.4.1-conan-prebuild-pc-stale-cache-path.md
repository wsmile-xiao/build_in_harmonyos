# DRAFT-libspecbleach-0.4.1-conan-prebuild-pc-stale-cache-path：conan 预编译依赖包 .pc 内嵌构建机缓存路径失效——sed 修复副本 + PKG_CONFIG_PATH 重定向恢复被跳过的上游测试入口

> Contributor: pc7-37 | Status: Draft | Updated: 2026-09-28
> Source: libspecbleach 0.4.1 适配（Path B 知识库扩展）；触发场景：上游测试双口径台账中
> 2 个 sndfile 门控入口首次未实例化，依赖实际已安装但 .pc 路径失效
> 对应：`knowledge/drafts/DRAFT-libspecbleach-0.4.1-conan-prebuild-pc-stale-cache-path.kv`

## 现象

`cmake -DENABLE_TESTS=ON` 配置阶段失败：

```text
-- Checking for module 'sndfile'
--   Found sndfile, version 1.2.2
CMake Error in CMakeLists.txt:
  Imported target "PkgConfig::SNDFILE" includes non-existent path
    "/storage/Users/currentUser/.cache/conan2/p/b/libsna…/p/include"
  in its INTERFACE_INCLUDE_DIRECTORIES.
```

pkg-config 报"找到"（Name/Version 正常），但解析出的 -I/-L 全部指向死路径，
错误推迟到 CMake Imported target 校验阶段；依赖门控的
`test_audio_file_regression` / `test_integration_realworld_quality`
从 `add_specbleach_test` 条件 `if(TARGET PkgConfig::SNDFILE)` 漏掉，
表现为"缺依赖未实例化"，实际是预编译包 .pc 路径失效。

## 根因

conan2 预编译包（libsndfile/1.2.2，package `21b17f8b…`，os=OHOS/6.0/armv8）
内 `lib/pkgconfig/sndfile.pc` 的 prefix 写死为原构建机缓存目录
`~/.cache/conan2/p/b/<hash>/p`。当前机器 conan 把包解包到内容寻址目录
`~/.conan2/p/<hash>/p`（哈希不同），.pc 内路径全部失效。
参考：DRAFT-ccfits-2.7-stale-pc-prefix-regen 记录了同族根因（预编译依赖自带
.pc 绝对 prefix 失效），其方案聚焦配方 generate() 阶段用 PkgConfigDeps 重新
生成；本条补充"无配方可改/仅需恢复上游测试入口"的验证阶段手法。

## 修复（本轮实测）

```bash
REALP="$(conan cache path 'libsndfile/1.2.2#cf6ded31…:21b17f8b…')"
FIXDIR="${TMPDIR:-/tmp}/pkgfix"
mkdir -p "$FIXDIR"
sed "s|/storage/Users/currentUser/.cache/conan2/p/b/[^/]*/p|$REALP|g" \
    "$REALP/lib/pkgconfig/sndfile.pc" > "$FIXDIR/sndfile.pc"
PKG_CONFIG_PATH="$FIXDIR" pkg-config --cflags --libs sndfile
# -I…/include -L…/lib -lsndfile  （均为实际存在路径）
PKG_CONFIG_PATH="$FIXDIR" cmake -DENABLE_TESTS=ON -DSPECBLEACH_BUILD_EXTRAS=ON …
cmake --build .
ctest --output-on-failure   # 41/41 PASS（含新恢复的 2 个入口）
```

## 验证

- `pkg-config --exists sndfile && pkg-config --cflags --libs sndfile` → 输出实际存在路径
- CMake 配置不再报 non-existent path
- `ctest -N`：Total Tests 39 → 41
- `ctest --output-on-failure -j1`：100% tests passed, 0 failed out of 41
- 相关日志 SHA-256：config=2672f30c…、build=22ea9ba5…、ctest=35636bd3…

## 适用边界与反例

- **适用**：conan2 预编译依赖包 .pc 失效；无配方改动权限/仅需恢复测试入口；
  依赖未实际缺失但路径指向原构建机缓存。
- **反例**：依赖确实未发布/未安装（应先 `conan list <dep>/* -r=ohpcd` 复查）；
  需在配方 generate() 阶段固化依赖注入时，应走 PkgConfigDeps 重新生成
  （参考 DRAFT-ccfits）而非 sed 修 .pc。
- **约束**：只生成"修复副本"到 $TMPDIR/pkgfix 并通过 PKG_CONFIG_PATH 优先指向，
  不改包内原始 .pc（改包内文件属越权）。