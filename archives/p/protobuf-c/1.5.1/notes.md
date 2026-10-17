# protobuf-c 1.5.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 `build-cmake/` 子目录，与已合入的 1.5.2 一致）
- 上游源码: `https://codeload.github.com/protobuf-c/protobuf-c/tar.gz/refs/tags/v1.5.1`
  sha256 `f3046f94ef6f85cf4311f6c4c51e2095c381ce7bb7fd4f90ea8d9cd99fca3c04`
- 真机: HarmonyOS PC / aarch64，clang（harmonybrew SDK），Conan 2.29.1
- 依赖: `protobuf/3.17.3`、`zlib/1.3.1` —— **两者只作 `tool_requires`（build context）**，
  发布的 libprotobuf-c 不链接 protobuf/zlib，消费者不需要它们
- 状态: built

## 编译步骤

1. `conan create archives/p/protobuf-c/1.5.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
2. `generate()` 生成 CMakeToolchain，显式把 `protobuf_DIR` / `ZLIB_ROOT` 指到 build-context
   依赖的包目录（上游 `find_package(Protobuf CONFIG)` 会经 `find_dependency(ZLIB)` 找 zlib）
3. `build()`：`cmake.configure(build_script_folder="build-cmake")`
   → 先 `--target protoc-gen-c`、`--target cxx-generate-packed-data`
   → 由 `cxx-generate-packed-data` 生成 `t/generated-code2/test-full-cxx-output.inc`
   → 全量 `cmake.build()`（`generate_test_sources()` 用 protoc + 自编 protoc-gen-c
   现场生成 11 个 `.pb-c.[ch]` 夹具）
   → `ctest --output-on-failure --timeout 120`
4. `package()`：`cmake.install()` 后删除 `bin/`（`protoc-gen-c` 是构建期代码生成器，
   不是本库交付物；库包里混 `bin/` 会触发 L0k「CLI 必须有 commands.json」）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools 路径 `config.status` 报 `Permission denied` | 鸿蒙 HMDFS 上 `umask 077 && mktemp -d` 建出的目录不可写（同 1.5.2 实录） | 走 CMake 构建系统，不用 `configure` |
| 2 | `make -j20` 打印 `gmake: jobserver mkfifo: .../GMfifoNNNNN: Operation not permitted` | 鸿蒙策略禁止用户进程创建 FIFO（图谱条目 E074/E345），GNU make 的 jobserver 建不了管道 | GNU make 自身回退为无 jobserver 模式，构建与测试结果不受影响；无需改配方（`-j` 并行度由 conan 注入，退化只影响速度） |
| 3 | `find_package(Protobuf CONFIG)` 后链接 `protobuf::libprotobuf` 报 `zlib::zlib` 目标不存在 | 制品仓 `protobuf/3.17.3` 的 CMake 包里，接口链接名记的是 Conan `CMakeDeps` 默认生成的 `zlib::zlib`；本项目用的是上游 `ProtobufConfig.cmake` 而非 Conan 生成的 config，那个 target 从没被创建 | 补丁 0001 第一个 hunk：在 `NOT TARGET zlib::zlib` 时用 `ZLIB_ROOT` 造一个 `UNKNOWN IMPORTED` 的 `zlib::zlib`，仅供构建期解析 protobuf 的接口链接 |
| 4 | 上游 11 个测试程序的 `.pb-c.[ch]` 夹具在 release tarball 与 git tag 里都不存在 | 顶层 `Makefile.am:366` 的 `dist-hook` 显式 `rm -f \`find ... -name '*.pb-c.[ch]'\``，夹具只能由 protoc + protoc-gen-c 现生成 | `protobuf` 进 `tool_requires`，`build()` 里先编 `protoc-gen-c`，再让 `generate_test_sources()` 现场生成夹具 |
| 5 | 上游 CMake 只把 11 个 TESTS 程序中的 6 个注册进 ctest | 上游 `build-cmake/CMakeLists.txt` 漏了 `issue204/330/375/440/745`（只有 automake 的 `Makefile.am` 认识它们） | 补丁 0001 按 `Makefile.am` 的同名规则补齐这 5 个 target 与 `add_test`；配方在跑 ctest 前用 `CTestTestfile.cmake` 的 `add_test(` 条数做门禁（`registered < 11` 直接失败，防止悄悄少跑） |
| 6 | `test-generated-code2` 编不过：`test-full-cxx-output.inc` 缺文件 | 上游 CMake 的 `add_custom_command` 把 `">t/generated-code2/xxx.inc"` 当**参数**传给 `cxx-generate-packed-data`，不是 shell 重定向，文件永远不生成（`Makefile.am` 写对了，CMake 这侧是上游 bug） | `build()` 里按 `Makefile.am` 的做法自己跑一次 `cxx-generate-packed-data > 文件`，并校验非空 |
| 7 | CMake Release 编译出的测试程序里 `assert()` 全被编掉 | CMake 的 Release flags 自带 `-DNDEBUG`，而 `t/` 下所有上游测试都是 assert 驱动——不修就等于 11 个测试全部空跑 | toolchain 里覆盖 `CMAKE_C_FLAGS_RELEASE=-O2`、`CMAKE_CXX_FLAGS_RELEASE=-O2`；日志核对 `NDEBUG_HITS=0` |
| 8 | 下载源码时 `BadZipFile` | codeload URL 末段是 tag 名（`.../refs/tags/v1.5.1`），没有 `.tar.gz` 后缀，conan 的 `get()` 按扩展名猜格式 | `conandata.yml` 的 `sources` 显式给 `filename: "protobuf-c-1.5.1.tar.gz"` |

## 源码修改

- `patches/0001-build-cmake-add-upstream-tests.patch`（改 `build-cmake/CMakeLists.txt`，
  两类改动：`zlib::zlib` 导入目标兜底 + 补齐 5 个上游测试程序）
- **未改动任何上游测试源代码**（`t/**/*.c`、`t/**/*.proto` 与官方 tag 逐字节一致），
  只在 CMake 侧把它们登记进构建与 ctest。

## 依赖版本

无运行时依赖。构建期：`protobuf/3.17.3`（提供 `protoc`，其 `ProtobufConfig.cmake`
再经 `find_dependency(ZLIB)` 需要 `zlib/1.3.1`）。制品仓已发布，满足 R36。

## 验证结果（真机 pc7185，`CONAN_HOME=~/work/psj/ch-protobuf-c`，日志 `work/psj/pc7185-ch1.log`）

```
protobuf-c/1.5.1: upstream_test_fixture: 41917 bytes
protobuf-c/1.5.1: upstream_test_audit: 11 ctest programs registered (upstream Makefile.am TESTS = 11)
protobuf-c/1.5.1: upstream_test_summary: 11/11 upstream ctest programs passed
100% tests passed out of 11        # ctest，Total Test time (real) = 0.47 sec
NDEBUG_HITS=0                      # 全日志无 -DNDEBUG，上游 assert() 未被编掉
test_protobuf_c: 14/14 checks passed
CREATE_EXIT:0
Full package reference: protobuf-c/1.5.1#c50ea39936e598f949fe7f6ecbd5f8cf:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#eb1b8c2ea9352fb78feb11f63badc8f3
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libprotobuf-c.a` | 静态库（本配方默认 `shared=False`） |
| `include/protobuf-c.h`、`include/protobuf-c/protobuf-c.h`、`include/protobuf-c/protobuf-c.proto` | 公共头 |
| `lib/pkgconfig/libprotobuf-c.pc` | pkg-config（`cmake_file_name=protobuf-c`、`cmake_target_name=protobuf-c::protobuf-c`、`pkg_config_name=libprotobuf-c`） |
| `lib/cmake/protobuf-c/*.cmake` | CMake 配置文件（8 个） |
| ~~`bin/protoc-gen-c`~~ | `package()` 主动删除：构建期代码生成器，不进交付物 |

## 注意事项

- 本包与已合入的 `1.5.2` 不通用：1.5.2 走 `BUILD_PROTOC=OFF + BUILD_TESTS=OFF`，
  上游测试一个都没跑（其实跑不了，protoc 不可用）。1.5.1 这次把 protobuf 引入 build
  context 后，11 个官方测试程序得以全部实跑。
- `package_type="library"` + `shared` option；若将来要出 `.so`，需同时检查
  `test_package` 的消费者运行环境（静态链时 `test()` 用 `conanrun` 没有额外 so 要加载）。
- 上游 `t/` 的测试程序名与 `Makefile.am` 的 `TESTS` 一一对应，声明口径为
  **11 个测试程序（ctest 注册条目）**，不是各程序内部 `assert()` 的条数。
