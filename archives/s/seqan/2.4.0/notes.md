# seqan 2.4.0 适配笔记

## Scope

- Conan reference: `seqan/2.4.0`
- 类型：**header-only** C++ 模板库（序列分析），无编译产物
- 交付：`include/seqan/**`（729 个头文件）+ 上游 cmake/pkgconfig 元数据 + LICENSE
- 第三方 Conan 依赖：无

## Source

官方 library-only 发行资产（GitHub Release，官方托管）：
`https://github.com/seqan/seqan/releases/download/seqan-v2.4.0/seqan-library-2.4.0.tar.xz`
（4868868 字节，sha256 `dd97b1514ab83acb7d7be911b157979e188e8ca72cc61c430c1e0fd03bcd41a5`）

选择 library-only 资产而不是 109MB 源码归档的原因：官方资产已是最终布局
（`include/` + `share/cmake/seqan/seqan-config.cmake` + `share/pkgconfig/seqan-2.pc`），
体积小、校验稳定，且 header-only 库没有需要交叉编译的产物。

## Build

配方不编译任何东西：

1. `source()` 下载并校验官方资产；
2. `package()` 归置 `include/`、`share/cmake/seqan/`、`share/pkgconfig/`、`licenses/`；
3. `package_info()` 暴露 `includedirs=["include"]`，并声明
   `cmake_file_name=seqan` / `cmake_target_name=seqan::seqan` / `pkg_config_name=seqan-2`，
   由 Conan 的 CMakeDeps 生成现代化 config（上游自带的是变量式 find-module：
   `SEQAN_INCLUDE_DIRS` / `SEQAN_LIBRARIES` / `SEQAN_DEFINITIONS`，两者并存）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游全量测试套件不在 release library 资产里 | SeqAn 的 CMake 只有 `SEQAN_BUILD_SYSTEM=DEVELOP` 才 `add_subdirectory(tests)`，而 library-only 资产是打包产物、不含 `tests/` | 配方按 header-only 归档；上游测试用**完整源码树**单独跑（见下"上游测试"），与 eigen 5.0.1 的处理方式一致 |
| 2 | 上游 find-module 只有变量、没有 imported target | `seqan-config.cmake` 是 2018 年的变量式模块 | 配方用 Conan 的 `cmake_target_name=seqan::seqan` 供消费方 `find_package(seqan)` + `target_link_libraries(seqan::seqan)` |

## 上游测试

完整源码树（`seqan/seqan` 的 `seqan-v2.4.0` 归档，含 `tests/`，51 个测试模块）单独配置
`SEQAN_BUILD_SYSTEM=DEVELOP`，用 OHOS SDK clang 15 交叉编译后经 qemu + OHOS musl
运行根执行（真机口径）：110 个测试可执行文件全部编译通过，**105/110 执行通过**；
5 个未通过项逐条定位为平台/环境能力差异（musl 无 POSIX AIO：`test_stream`/`test_sequence`
的 `Async` 路径；本地运行根缺 `pthread_cond_clockwait`：`test_arg_parse*`，OHOS `libc.so`
已导出该符号；musl/glibc `strtod` 语义差异：`test_blast` 35 子用例中 2 个）。
上游 ctest 条目合计 **403**（110 测试可执行文件 + 269 教学 demo + 18 app 脚本 + 6 顶层条目）。
header-only 库的消费方验证由 `test_package/` 承担（见下）。

## 验证结果

- `conan create . -pr:h=ohos-aarch64-run -pr:b=default`：EXIT=0，产出 `seqan/2.4.0` 包
- `test_package`（消费者端到端用例 `test_seqan_consumer`）：交叉编译链接通过
  （`seqan::seqan` 目标解析、头文件与 cmake 元数据齐全），并在 OHOS aarch64 运行根 + qemu
  下执行通过（exit=0，**7/7 校验点**）——完整消费者流程：序列准备 → Gotoh 全局比对 →
  Index/Finder 检索 → reverseComplement 变换，各阶段产物依次传递，非空壳断言
- 归档内容：729 个头文件 + `share/cmake/seqan/seqan-config.cmake` + `share/pkgconfig/seqan-2.pc` + LICENSE

## 注意事项

`seqan`（SeqAn 2.x，header-only）与 `seqan3`（SeqAn 3.x，C++20，可用作库）是两个不同的包；
本包对应 lambda-align2 2.0.1 等 SeqAn 2 系消费者。
