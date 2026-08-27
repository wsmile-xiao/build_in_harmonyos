# alembic-graphics 1.8.9 适配笔记

## 编译环境

- 构建系统: CMake（`CMAKE_MINIMUM_REQUIRED(VERSION 3.13)`，C++14）
- 版本号来源: 顶层 `PROJECT(Alembic VERSION 1.8.9)` 硬编码（生成 `lib/Alembic/Util/Config.h`
  的 `ALEMBIC_LIBRARY_VERSION`），conanfile 按 code-style 规范硬编码 `version = "1.8.9"`
- 编译日期: 2026-08-26
- 编译器: clang 15 / clang++（Alpine musl clang 15.0.7）
- Conan 版本: 2.29.1（OHOS 适配版，os=OHOS 枚举）
- CMake 版本: 4.1.2
- Python 版本: 3.12
- Profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, libcxx=libc++, cppstd=17)
- 状态: built（CI 验证通过）

## 源码与校验

| 来源 | URL | sha256 |
|------|-----|--------|
| Alembic 1.8.9 | https://github.com/alembic/alembic/archive/refs/tags/1.8.9.tar.gz | 8c59c10813feee917d262c71af77d6fa3db1acaf7c5fecfd4104167077403955 |
| Imath 3.1.12 (vendor) | https://github.com/AcademySoftwareFoundation/Imath/archive/refs/tags/v3.1.12.tar.gz | 8a1bc258f3149b5729c2f4f8ffd337c0e57f09096e4ba9784329f40c4a9035da |

**版本选型（master ≠ release tarball）**：必须使用冻结的 1.8.9 release tarball（官方 URL）。
GitHub `1.8.9...master` 领先 28 commits，含 1.8.10/1.8.11/1.8.12 变更、Issue 477
（测试输出文件并行改名）、Issue 475（LICENSE 加 SPDX 简写）等。用 master 或后续 tag
会造成测试计数/源码与声明版本不一致。

**1.8.9 与 1.8.10 的差异（tarball diff 实测）**：顶层 CMakeLists（版本号 1.8.9 vs 1.8.10）、
LICENSE（1.8.9 **尚无** SPDX 简写行，1.8.10 的 Issue 475 才加）、NEWS、
`bin/*` 与 maya/arnold/prman/python 的 CMakeLists、3 个测试 .cpp（仅测试输出文件改名）。
核心库构建配置、64/57 ctest 用例、断言点数量（可运行模块 ≈2092）与 1.8.10 **逐一相同**。

## 关键决策 1：Imath 内嵌编译

Imath（Alembic 唯一硬依赖）在 OHOS 制品仓不可用（或为 shared 二进制，混合链接静态
Alembic + 共享 Imath 存在 RPATH/打包复杂度），沿用 1.8.10 实证的 **vendor 源码 + 独立
cmake 构建** 方案（单一 PR 自包含）：

1. conandata.yml 声明两个源（Alembic 1.8.9 + Imath v3.1.12），source() 把 Imath 解压到
   源码树 `imath/` 子目录。
2. `_build_imath()` 用同一 Conan 工具链（`generators/conan_toolchain.cmake`）把 Imath
   作为独立项目构建为静态库，安装到 `build/imath-prefix`
   （`-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`）。
3. Alembic 的 `generate()` 设 `CMAKE_PREFIX_PATH=imath-prefix`，其顶层 `FIND_PACKAGE(Imath)`
   即可解析到 Imath 的 cmake 配置与 `Imath::Imath` 目标，Alembic 在
   `lib/Alembic/CMakeLists.txt` 直接 `TARGET_LINK_LIBRARIES(Alembic LINK_PUBLIC Imath::Imath ...)`。
4. package() 把 `imath-prefix/lib/libImath-3_1.a`（规整为 `libImath.a`）与
   `imath-prefix/include/Imath/` 拷进包，并删除 `lib/cmake`（其引用重命名前库名与外部 Imath）。

`cpp_info.libs = ["Alembic", "Imath"]`（静态库不内嵌传递目标文件，故需同时声明两者）。

## 关键决策 2：绕开 target_compile_features（补丁 0001）

CMake 4.1.2 无法识别 hnp 的 Alpine musl clang（compiler id unknown、
`CMAKE_CXX_COMPILE_FEATURES` 为空），凡用 `target_compile_features(cxx_std_*)` 的上游库
都会报 `no known features for CXX compiler`。

- Alembic 自身用 `set(CMAKE_CXX_STANDARD 14)`（标志，不查 features），不受影响。
- vendored Imath 的 `config/LibraryDefine.cmake` 用 `target_compile_features`，需打补丁。

补丁 `patches/0001-imath-cxx-standard.patch`：把 Imath 的
`target_compile_features(${objlib} PRIVATE cxx_std_${IMATH_CXX_STANDARD} INTERFACE cxx_std_11)`
改为 `set_target_properties(${objlib} PROPERTIES CXX_STANDARD ${IMATH_CXX_STANDARD} CXX_STANDARD_REQUIRED ON INTERFACE_CXX_STANDARD 11)`。
属 portability 类补丁，仅改 C++ 标准的施加方式，不改 Imath 逻辑；`INTERFACE_CXX_STANDARD 11`
保留原 `INTERFACE cxx_std_11` 对消费者的 C++11 接口要求。该补丁在 `_build_imath()` 中以
`base_path=imath_src` 应用到 vendored 源码，与 Alembic 版本无相关性（作用于 Imath v3.1.12）。

> 关联：test_package 的 CMakeLists 也不用 target_compile_features，C++ 标准由
> Conan CMakeToolchain（profile cppstd=17）注入。

## 构建配置（conanfile.py generate）

```python
tc.variables["ALEMBIC_SHARED_LIBS"] = self.options.shared       # 默认 False
tc.variables["CMAKE_PREFIX_PATH"] = imath_prefix                # 解析 FIND_PACKAGE(Imath)
tc.variables["USE_HDF5"] = False
tc.variables["USE_ARNOLD"] = False
tc.variables["USE_PRMAN"] = False
tc.variables["USE_MAYA"] = False
tc.variables["USE_PYALEMBIC"] = False
tc.variables["USE_TESTS"] = True
tc.variables["USE_BINARIES"] = False
tc.variables["ALEMBIC_DEBUG_WARNINGS_AS_ERRORS"] = False
```

- 静态构建：Alembic 使用自有选项 `ALEMBIC_SHARED_LIBS`（注意不是 `BUILD_SHARED_LIBS`）。
- USE_BINARIES=OFF：仅产出库。AbcLs/AbcTree/abcconvert 等工具缺乏统一 `--version`，
  超出库适配范畴，故不构建（亦免去 commands.json 与 L2 冒烟）。

## 上游测试用例统计

Alembic 用 CTest 注册单元测试，分布在 `lib/Alembic/*/Tests/`。USE_TESTS=ON、
USE_HDF5=OFF 下实际编译运行的 ctest 用例计数（`ctest -N` / 实跑均为 57）：

| 模块 | 用例数 |
|------|--------|
| Abc/Tests | 16 |
| AbcGeom/Tests | 15 |
| AbcCoreOgawa/Tests | 8 |
| AbcMaterial/Tests | 6 |
| Util/Tests | 4 |
| AbcCoreAbstract/Tests | 3 |
| AbcCoreLayer/Tests | 2 |
| Ogawa/Tests | 2 |
| AbcCollection/Tests | 1 |
| **合计（运行）** | **57** |

上游源码 `ADD_TEST` 总条目 64；其中 AbcCoreHDF5/Tests 的 7 个用例在 `IF(USE_HDF5)` 内
（HDF5 为可选后端，本次 USE_HDF5=OFF、且 OHOS 未提供 HDF5），不参与编译/运行。故：

- 上游测试通过率 = 57/64（89.1%），分子=实跑且通过数 57，分母=上游 ADD_TEST 总数 64。
- 7 个未运行用例均为 HDF5 后端，需 HDF5 依赖。

**⚠️ 1.8.9 测试输出文件命名冲突（上游 Issue 477，1.8.10 才修复）**：多个 ctest 用例向
cwd 写同名 `.abc` 文件（如 Abc/Tests 的 `flatHierarchy.abc`、`archiveInfo.abc` 等）。
**ctest 必须串行执行（默认），禁止 `-j` 并行**——并行时多个测试进程同时写同名文件会
互相覆盖导致间歇性失败。1.8.10 已将冲突文件改名（如 `flatHierarchy.abc` →
`flatHierarchyObj.abc`）修复此问题，1.8.9 未修，故本配方 `cmake.test()` 使用默认串行。

`build()` 末尾 `cmake.test()` 实跑结果（节选）：

```
100% tests passed, 0 tests failed out of 57
Total Test time (real) = 6.84 sec
```

> 反向校验：ctest 输出非空，57 个用例逐条 Passed；测试程序读写真实 `.abc` 文件
> （如 test1.cpp 写出 slappyJim.abc 并读回比对），非空壳；退出码与通过计数一致。

## 许可证

BSD-3-Clause（LICENSE.txt，Copyright ILM & Sony Pictures Imageworks）。
注意 1.8.9 的 LICENSE.txt **尚无 SPDX 简写行**（1.8.10 的 Issue 475 才加），
SPDX 标识仍为 `BSD-3-Clause`，不影响包元数据。

## test_package

`test_package/test_alembic.cpp` 真实调用 Alembic + Imath API：用
`AbcCoreOgawa::WriteArchive` 写出含 `smoke_child` 对象、`OV3fProperty`（`Imath::V3f`）
属性的归档，再经 `AbcCoreFactory::IFactory::getArchive` 读回，校验
`getNumChildren()==1` 且子对象名为 `smoke_child`。链接 `alembic-graphics::alembic-graphics`
（=libAlembic + libImath）。通过：`alembic 1.8.9 smoke test OK`。
test() 调 `self.run()` 真实执行（L0d 门禁）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `FIND_PACKAGE(Imath)` 找不到 Imath | Imath 未发布到制品仓（或仅 shared 二进制），系统也无 | vendor Imath 源码，独立 cmake 构建安装，CMAKE_PREFIX_PATH 解析 |
| 2 | Imath 配置报 `target_compile_features no known features` | CMake 4.x 无法识别 OHOS clang（id unknown），CMAKE_CXX_COMPILE_FEATURES 空 | 补丁 0001 改用 CXX_STANDARD 属性 |
| 3 | 静态库 libImath-3_1 命名带 SOVERSION 后缀 | Imath 3.x 目标名约定 | package() 规整为 libImath.a，cpp_info.libs 声明 "Imath" |
| 4 | 下游只链 libAlembic.a 链接报未定义符号 | 静态库不内嵌传递目标文件 | cpp_info.libs 同时声明 Alembic 与 Imath |
| 5 | ctest 并行下测试输出文件互写（flatHierarchy.abc 等） | 上游 Issue 477（1.8.10 才修复） | ctest 必须串行，禁止 -j |

## 源码修改

### patches/0001-imath-cxx-standard.patch（作用于 vendored Imath 源码）

修改 Imath `config/LibraryDefine.cmake`：将
`target_compile_features(${objlib} PRIVATE cxx_std_${IMATH_CXX_STANDARD} INTERFACE cxx_std_11)`
替换为 `set_target_properties(${objlib} PROPERTIES CXX_STANDARD ${IMATH_CXX_STANDARD} CXX_STANDARD_REQUIRED ON INTERFACE_CXX_STANDARD 11)`。
仅改变 C++ 标准的施加方式（绕开本环境不可用的 target_compile_features），不改 Imath 逻辑；`INTERFACE_CXX_STANDARD 11` 保留原 INTERFACE cxx_std_11 对消费者的 C++11 要求。
Alembic 自身源码未修改。

## 实跑命令（真机鸿蒙 CI）

```bash
export PATH=<工具链前缀>/usr/local/bin:<系统bin>:$PATH  # 示例路径，随实际环境调整
export TMPDIR=$HOME/tmp
cd <worktree>  # 示例：设备端项目 worktree
CI_PACKAGES="archives/a/alembic-graphics/1.8.9" /usr/bin/zsh ci/conan/build_and_test.sh
```

> 设备 /tmp 只读，必须设 TMPDIR（可写目录，如 $HOME/tmp）；
> python3/conan 不在默认 PATH，必须前置 export PATH。
