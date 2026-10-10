# openbabel 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists 声明 3.1，CI 实际 4.1.2）
- 编译日期: 2026-10-09
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，-fuse-ld=lld）
- 状态: built（verify 通过，未 upload）

## 上游身份判定
- 用户输入 libopenbabel；上游 = Open Babel（C++ 化学信息学工具箱），
  homepage https://openbabel.org，GitHub openbabel/openbabel，
  release tag `openbabel-3-1-1`，资产 openbabel-3.1.1-source.tar.bz2（27.7MB，
  sha256 a6ec8381…70e68，官方 GitHub releases）。库名形态即 libopenbabel。

## 依赖决策（W0 已核验制品仓）
- zlib/1.3.1（ohpcd 静态专用配方，libz.a）
- libxml2/2.15.3（ohpcd 配方硬编码 BUILD_SHARED_LIBS=ON，仅有共享二进制 → 按仓内
  消费先例（abiword 系）用共享；recipe 内对其 .so symlink 链做实体化以规避
  HMDFS symlink 间歇 EACCES）
- eigen/3.4.0（header-only）
- inchi/rapidjson：上游 bundled（WITH_STATIC_INCHI=ON / external/rapidjson）
- maeparser/coordgen（Maestro 格式）：显式 OFF——需 boost 且为可选格式插件，
  上游原生支持 graceful degrade

## 上游测试清点（R51 三步法第一步）
test/ 为单 test_runner + CTest：cpptests 29 模块 159 例 + align(Eigen3) 5 例 +
origtests 30 源 44 例 + cmlreadfile 1 例（静态+WITH_STATIC_LIBXML 下注册）+
inchiwrite 3 例 = **212 个 CTest 用例**（ctest -N 口径）。

## 编译步骤

由 conan create 全程驱动（archives/o/openbabel/3.1.1 配方）：
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同 --build=missing`
2. CMake 变量注入：CMAKE_SYSTEM_NAME=Linux（E092）、BUILD_SHARED=OFF、
   ENABLE_TESTS=ON、WITH_STATIC_INCHI/STATIC_LIBXML=ON、WITH_MAEPARSER/COORDGEN=OFF、
   ENABLE_OPENMP=OFF、ENABLE_VERSIONED_FORMATS=OFF
3. module-mode 变量注入（绝对路径锚定）：ZLIB_INCLUDE_DIR/ZLIB_LIBRARY、
   LIBXML2_INCLUDE_DIR/LIBXML2_LIBRARY/LIBXML2_LIBRARIES、EIGEN3_INCLUDE_DIR
4. OHOS 设备实跑：签名 test_runner 后跑 28 项代表性 CTest 子集 +
   签名 obabel（test_package 消费者测试 11 断言）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required/`CMP0042 OLD` 被 CMake 4 拒绝 | CMake 4 移除 <3.5 兼容；policy 变量须命令行传 | cli_args -DCMAKE_POLICY_VERSION_MINIMUM=3.5 + 补丁 OLD→NEW（E545） |
| 2 | qeq/qtpie 编进 Eigen2 分支、CML 被静默禁用 | CMakeToolchain 强制 CONFIG 优先后只有 Eigen3_FOUND/LibXml2_FOUND，上游判全大写变量 | 补丁接受两种大小写 + recipe 注入 module-mode 变量（E546） |
| 3 | 静态分支 FIND_LIBRARY_SUFFIXES=".a" 找不到 libxml2 | 制品仓 libxml2 仅共享 | 补丁放宽 ".a;.so"（E547） |
| 4 | test_runner/obabel 全静态链接拒绝动态 libxml2 | 上游 -static + LINK_SEARCH_END_STATIC | OHOS_BUILD_PARTIAL_STATIC 开关跳过，保留部分静态（E547） |
| 5 | CMakeDeps "Library 'xml2' not found in package" | HMDFS 上依赖包内 .so symlink 链间歇 EACCES | generate() 实体化依赖包 symlink（清单 #24 同源） |
| 6 | PTHREAD_LIBRARY NOTFOUND | musl pthread 在 libc，无独立 libpthread | 补丁 find 到才追加 |
| 7 | 签名后 ELF execve EACCES | 签名输出无执行位 + HMDFS 新 ELF 瞬时窗口 | chmod 755 + 重试（4×15s） |
| 8 | 27MB 源码下载 4KB/s | 设备网络慢 | 预置官方包进 core.sources:download_cache（按 sha256 命中） |

## 源码修改（patches/，均 patch_type=portability）
- 0001-CMakeLists.txt.patch：CMP0042 OLD→NEW；FIND_LIBRARY_SUFFIXES .a→.a;.so；
  EIGEN3_FOUND/LibXml2_FOUND 大小写兼容
- 0002-tools-CMakeLists.txt.patch：PTHREAD 找到才追加；obabel 全静态改 OHOS 开关
- 0003-src-CMakeLists.txt.patch：4 处 Eigen/LibXml2 大小写兼容（含空格变体）
- 0004-formats-cmake.patch：formats.cmake 同类兼容（XML/CML 格式组）
- 0005-test-CMakeLists.txt.patch：test 侧同类兼容 + test_runner 部分静态开关

## 依赖版本
zlib/1.3.1、libxml2/2.15.3（共享）、eigen/3.4.0、conan 2.29.1（OHOS 适配版）、
cmake 4.1.2、clang 15.0.4

## 验证结果

```bash
# conan create（含 W3 同源构建）
HMBS_UPSTREAM_TEST_RESULT: status=passed discovered=212 executed=28 passed=28 failed=0 skipped=184
# test_package 消费者端到端（真机）：
# SMILES 解析→规范化/分子式→MOL 往返→InChI 生成→MW 描述符，11/11 断言通过
# conan-verify：G0-G4 + L2/L4/L5 全 PASS
```

## 注意事项
- 下游消费者链接需 libopenbabel + libinchi（cpp_info.libs 已声明），头文件在
  include/openbabel3；运行期数据文件在 share/openbabel（BABEL_DATADIR 或默认路径）。
- 静态 libopenbabel.a 引用 libxml2.so 符号，cpp_info.requires 已带 libxml2 传递。
- 制品仓 libxml2 配方硬编码共享构建，静态变体不可得（如需静态 libxml2 需先改其配方）。
---

**编译结束**: 2026-10-09 22:17
**最终状态**: built
