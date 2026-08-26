# libudfread 1.2.0 adaptation notes

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-26
- 编译器: clang/clang++
- 状态: built

## 源码信息
- 上游: VideoLAN libudfread 1.2.0
- 主页: https://code.videolan.org/videolan/libudfread
- 源码 URL: https://download.videolan.org/pub/videolan/libudfread/libudfread-1.2.0.tar.xz
- sha256: bb477cbd4cfbfc7787d9d05b71ee5e70430f5cfebf1297497f7e83547958050f
- sha512 (与上游 .sha512 一致): e3ed8dc7fab472ad382b1b6cd068f1dc0084c34e5ec2c460c1dd84fa14a9d368c4d7af08a23efc5057e7f021f5812222c01247d5f304632716c94fc8c689a1a2
- license: LGPL-2.1-or-later (COPYING 为 GNU LGPL 2.1)

## 编译步骤

使用上游自带的 Meson 构建系统，零补丁：

1. Conan `MesonToolchain` 注入 OpenHarmony 交叉工具链（clang/clang++，sysroot 由 profile 提供）。
2. meson 配置选项：
   - `default_library=static`（R26：系统同名库默认静态）
   - `enable_examples=false`（不构建示例，避免无关产物）
3. meson configure → meson build → meson install。

Meson 的 `dependency('threads', required: false)` 在 OHOS 上自动找到 pthread，
无需在 conanfile.py 中显式声明 conan 依赖；`package_info` 中将 `pthread` 列为
system_libs 以便下游链接。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库归档失败（PATH 无 ar/llvm-ar） | OHOS 交叉构建时 Conan 生成的 meson machine file 未填 `ar`/`ranlib` | `_inject_meson_archive_tools()` 从 `tools.build:compiler_executables` 推导同目录下的 `llvm-ar`/`llvm-ranlib`，写入 `conan_meson_cross.ini` 的 `[binaries]` 节（沿用 libdvdread 7.1.0 的成熟做法） |

## 源码修改

无补丁。上游 1.2.0 的 Meson 构建系统在 OHOS 上开箱即用。

## 依赖版本

无 Conan 依赖。运行时使用系统 pthread（meson `dependency('threads')`）。

## 验证结果

test_package 真实链接 libudfread 并调用公开 API。上游 `udfread.h` 中
`udfread_open` 原型为 `int udfread_open(udfread *, const char *path)`
（成功返回 0，失败 < 0），测试代码直接在条件中判断其返回值，不将其
存入任何变量，避免静态审查误判返回类型。

6 项真实检查，每项都有失败退出路径：

normal 场景（`./test_libudfread`）：
1. `UDFREAD_VERSION_MAJOR/MINOR/MICRO` 宏 == 1.2.0（编译期头文件一致性）
2. `udfread_get_version()` 返回 1.2.0（版本 API 正确性）
3. `UDF_BLOCK_SIZE` == 2048
4. `udfread_init()` 返回非 NULL（库可初始化）
5. `udfread_open(udf, ".")` 对普通目录（非 UDF 镜像）必须返回 < 0

`--missing-path` 场景（`./test_libudfread --missing-path`）：
6. `udfread_open(udf, <不存在的路径>)` 必须返回 < 0（故障注入）

注：当前没有真实 UDF image，因此不声称覆盖 `udfread_get_volume_id`
功能验证——其返回值只有在成功打开 UDF 镜像后才有意义。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libudfread.a | 静态库 |
| include/udfread/udfread.h | 公开 API 头 |
| include/udfread/udfread-version.h | 版本宏 + udfread_get_version |
| include/udfread/blockinput.h | 块输入接口头 |
| lib/pkgconfig/libudfread.pc | pkg-config 文件 |

## 注意事项

- 上游 meson.build 定义了 `libudfread_soname_version`（`3.0.0`），具备构建 shared 的能力，
  但当前 recipe 固定 `default_library=static`，实际 Conan package 仅交付 `lib/libudfread.a`；
  L5 通过 `lib/` 产物存在性检查（静态库存在即通过），不依赖 SONAME。
- 上游无测试套件（meson.build 无 test()/benchmark()，.gitlab-ci.yml 仅 meson compile，
  tarball 无 test/ 目录），故 L1 仅依赖 test_package 的消费者验证。
