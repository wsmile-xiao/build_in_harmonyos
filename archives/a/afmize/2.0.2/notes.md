# afmize 2.0.2 适配笔记

## 状态
- 状态：`built`（设备构建、上游 CTest、Conan `test_package` 已通过；未标记 `published`）。
- 构建系统：CMake；上游源码为 C++14，OHOS profile 使用 clang 15/libc++/C++17；许可证：MIT。
- 上游 tag commit：`5b5e668b91bdd297f2c63abc3c7cc58c232c1494`。

## 源码与离线依赖
主源码 SHA256：`39445470cef65476e78ed0197c0f6e0fd077d61058a74c133768c1dadc9f729b`。
源码 tarball 不含 Git submodule 内容，`source()` 从 `conandata.yml` 注入固定 archives：mave `163cbf273003c3fb940338cf82b1fa154a3012c1`、pnm `2da9d7e1050fe4904fd9dcc88cc7517601ca8391`、toml11 `4d0ed847f99e6459b0f48280ffc17f5b805262cd`。构建阶段不执行 git 或联网下载。

## 补丁
`patches/0001-CMakeLists.txt.patch` 移除上游 `git submodule update` 和 Boost 网络下载，改用 Conan Boost，并将 CMake 最低版本提升到 3.5；补丁由源码差异重新生成且已在 Conan clean build 中应用。

## 依赖与 OHOS
- 精确依赖：`boost/1.84.0`；依赖 binary 由当前 OHOS profile 的缓存兼容包提供。
- CMake 通过 Conan toolchain 使用 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`，这是当前 CMake 没有 HarmonyOS platform module 时的实测兼容方式；目标编译器仍为 `/data/service/hnp/bin/clang++`。
- OHOS libc 不声明 Boost 1.84 `sp_thread_sleep.hpp` 使用的 pthread cancellation API，recipe 对 OHOS 定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE=1`，未删除测试或核心功能。

## 验证
最终设备命令使用 host/build profile `ci/conan/profiles/ohos-aarch64`，并显式覆盖 `compiler.cppstd=17`、`compiler.libcxx=libc++`、`os.version=6.0`：

```sh
conan create archives/a/afmize/2.0.2 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build='afmize/*' \
  -s:h=compiler.cppstd=17 -s:b=compiler.cppstd=17 \
  -s:h=compiler.libcxx=libc++ -s:b=compiler.libcxx=libc++ \
  -s:h=os.version=6.0 -s:b=os.version=6.0 \
  -c tools.build:jobs=1
```

原生 Conan 构建包含 3 个上游 CTest：`test_collision`、`test_read_as_angstrom`、`test_aabb`，最终为 3/3 PASS；`test_package` 真实执行 `afmize config.toml`，并验证 `afmize-test.ppm`、`.tsv`、`.json` 三个文件非空（3/3 assertions PASS）。`commands.json` 声明了 `afmize` application/tool 入口。
