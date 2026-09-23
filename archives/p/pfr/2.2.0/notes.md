# pfr 2.2.0 适配笔记

## 基本信息

- 上游：<https://github.com/boostorg/pfr>
- 版本：2.2.0
- 许可证：BSL-1.0
- 类型：header-only C++14 库
- 分支：`feat/pfr-2.2.0`

## 源码与打包

- 官方源码：`https://github.com/boostorg/pfr/archive/refs/tags/2.2.0.tar.gz`
- SHA-256：`6f490ec1383de5855dcf801c23f0a967f888eb6e1440b6ca0bf36c12d4ae7ac7`
- 上游 `CMakeLists.txt` 只定义 `boost_pfr` INTERFACE 目标，没有 install 规则；配方直接复制 `include/boost` 并安装 `LICENSE_1_0.txt`。
- Conan 包不声明第三方依赖，也不生成二进制库；消费者通过 CMakeDeps 使用 `boost::pfr`。

## 上游测试边界与修复

2.2.0 源码包含 `test/`、Boost.Build Jamfile 和 72 个 C++ 测试源，但独立发布压缩包不包含 Boost superproject 的根 Jamroot、Boost.Test 轻量测试头以及 `libs/config` 等测试依赖。上游 CI 的真实路径是把该目录复制进 Boost superproject 后运行 `b2 libs/pfr/test`。

最终清单使用设备上的 `./b2 --dump-tests -d0 libs/pfr/test toolset=clang cxxstd=20 variant=debug`，并以 Conan 安装包头目录作为第一个 pfr include 路径，发现 191 个 `boost-test` 行：`RUN=117`、`COMPILE_FAIL=73`、`RUN_PYD=1`。统计单位是 Boost.Build 测试目标定义，不是断言数或源文件数；清单摘要和原始输出保存在任务本地 handoff 的 r34 证据目录。

修复包含两部分：

1. `cast_to_layout_compatible.hpp` 直接包含 `<memory>`，为 `std::addressof` 提供正确声明。
2. `offset_based_getter.hpp` 的旧 GCC 对齐兼容分支排除 Clang。OHOS Clang 定义 GCC 兼容宏，原条件会在 aarch64 上错误地把 `double` 对齐按 4 字节处理，造成 PFR 偏移检查失败。

此外，Boost superproject 测试必须把 Conan 安装包的 pfr include 目录放在 `-I.` 之前，否则会误测 superproject 自带的另一份 `boost/pfr` 头文件。最终 b2 只通过测试命令传入四个已记录的诊断警告抑制项（`-Wno-unused-value`、`-Wno-unused-private-field`、`-Wno-unused-variable`、`-Wno-undefined-var-template`），配方本身不携带这些 flags。

设备最终执行命令为：

```text
./b2 -d0 -j1 -a libs/pfr/test toolset=clang cxxstd=14,17,20 variant=debug,release cxxflags="$PFR_OHOS_CXXFLAGS -I$PFR_PACKAGE_INCLUDE -Wno-unused-value -Wno-unused-private-field -Wno-unused-variable -Wno-undefined-var-template" linkflags="$PFR_OHOS_LINKFLAGS"
```

该轮返回码为 `0`，日志没有 `failed updating` 标记；完整原始日志和摘要保存在任务本地 r34 handoff。r29 的 62 个失败目标证据仍保留在任务本地 r29 handoff，但它使用了错误的头文件树，不能替代本轮最终包头验证。

## 当前状态

- 设备 Conan 验证 G0-G4/L2/L4/L5、W3 `conan create` 和两个消费者测试已通过；W3 日志记录了正式补丁的 `Apply patch`。
- 设备 Boost.Build 全量矩阵已通过：统计口径为 191 个 Boost.Build 测试目标定义，最终命令覆盖 C++14/C++17/C++20 与 debug/release，返回码 `0`，失败目标 `0`。
- W4、PR、CI 和 Review 将在最终本地 SHA 定稿后按统一工作流继续执行。
