# alembic 1.8.10 适配笔记

## 编译环境

- 构建系统: CMake (C++14)
- 编译日期: 2026-07-15
- 编译器: clang 15 / clang++ (Alpine musl clang 15.0.7)
- Conan 版本: 2.29.1（OHOS 适配版，os=OHOS 枚举）
- CMake 版本: 4.1.2
- Python 版本: 3.12
- Profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, libcxx=libc++, cppstd=17)
- 状态: built（验证通过；CI upload 待 PR 合入 main 后由发布流水线完成）

> 说明：上游测试在本机构建环境（Linux 内核 + Alpine musl clang 工具链）实测运行；
> CI 侧未将上游测试接入门禁，真机鸿蒙 worker 的结果以 CI 为准。

## 源码与校验

| 来源 | URL | sha256 |
|------|-----|--------|
| Alembic 1.8.10 | https://github.com/alembic/alembic/archive/refs/tags/1.8.10.tar.gz | 06c9172faf29e9fdebb7be99621ca18b32b474f8e481238a159c87d16b298553 |
| Imath 3.1.12 (vendor) | https://github.com/AcademySoftwareFoundation/Imath/archive/refs/tags/v3.1.12.tar.gz | 8a1bc258f3149b5729c2f4f8ffd337c0e57f09096e4ba9784329f40c4a9035da |

## 关键决策 1：Imath 内嵌编译

W0 依赖检查结论：Imath（Alembic 唯一硬依赖）**未发布**到 OHOS Conan 制品仓
（`conan download "imath/*" -r=ohpcd --only-recipe` 返回 0 个 recipe；`openexr`
同样未发布）。仓库内 `archives/i/imath/3.2.2/` 仅有 manifest/notes，无 conanfile.py。

因此采用 **vendor 源码 + 独立 cmake 构建** 方案（单一 PR 自包含，无需先发 imath）：

1. conandata.yml 声明两个源（Alembic + Imath），source() 把 Imath 解压到源码树 `imath/` 子目录。
2. `_build_imath()` 用同一 Conan 工具链（`generators/conan_toolchain.cmake`）把 Imath
   作为独立项目构建为静态库，安装到 `build/imath-prefix`（`-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`）。
3. Alembic 的 `generate()` 设 `CMAKE_PREFIX_PATH=imath-prefix`，其顶层 `FIND_PACKAGE(Imath)`
   即可解析到 Imath 的 cmake 配置与 `Imath::Imath` 目标，Alembic 在
   `lib/Alembic/CMakeLists.txt` 直接 `TARGET_LINK_LIBRARIES(Alembic LINK_PUBLIC Imath::Imath ...)`。
4. package() 把 `imath-prefix/lib/libImath-3_1.a`（规整为 `libImath.a`）与
   `imath-prefix/include/Imath/` 拷进包，并删除 `lib/cmake`（其引用重命名前库名与外部 Imath）。

`cpp_info.libs = ["Alembic", "Imath"]`（静态库不内嵌传递目标文件，故需同时声明两者）。

## 关键决策 2：绕开 target_compile_features（补丁 0001）

实测本机构建环境 CMake 4.1.2 **无法识别** hnp 的 Alpine musl clang：

```
-- The CXX compiler identification is unknown
CMAKE_CXX_COMPILER_ID=   (空)
CMAKE_CXX_COMPILE_FEATURES=   (空)
```

`__clang__`/`__GNUC__` 宏均存在，但 CMake 4.x 的识别机制仍判为 unknown，
导致 `CMAKE_CXX_COMPILE_FEATURES` 为空。于是凡用 `target_compile_features(cxx_std_*)`
的上游库都会报 `no known features for CXX compiler`。

- Alembic 自身用 `set(CMAKE_CXX_STANDARD 14)`（标志，不查 features），不受影响。
- vendored Imath 的 `config/LibraryDefine.cmake` 用 `target_compile_features`，需打补丁。

补丁 `patches/0001-imath-cxx-standard.patch`：把 Imath 的
`target_compile_features(${objlib} PRIVATE cxx_std_${IMATH_CXX_STANDARD} INTERFACE cxx_std_11)`
改为 `set_target_properties(${objlib} PROPERTIES CXX_STANDARD ${IMATH_CXX_STANDARD} CXX_STANDARD_REQUIRED ON INTERFACE_CXX_STANDARD 11)`。
属 portability 类补丁，仅改 C++ 标准的施加方式，不改 Imath 逻辑；`INTERFACE_CXX_STANDARD 11`
保留原 `INTERFACE cxx_std_11` 对消费者的 C++11 接口要求。该补丁在
`_build_imath()` 中以 `base_path=imath_src` 应用到 vendored 源码。

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

上游源码 `ADD_TEST` 总条目 64；其中 AbcCoreHDF5/Tests 的 7 个用例在
`IF(USE_HDF5)` 内（HDF5 为可选后端，本次 USE_HDF5=OFF、且 OHOS 未提供 HDF5），
不参与编译/运行。故：

- 上游测试通过率 = 57/64（89.1%），分子=实跑且通过数 57，分母=上游 ADD_TEST 总数 64。
- 7 个未运行用例均为 HDF5 后端（`AbcCoreHDF5_Test1/ArchiveTests/ArrayPropertyTests/
  ScalarPropertyTests/TimeSamplingTests/ObjectTests/ConstantPropsTest`），需 HDF5 依赖。

`build()` 末尾 `cmake.test()` 实跑结果（节选）：

```
100% tests passed, 0 tests failed out of 57
Total Test time (real) = 6.84 sec
```

> 反向校验：ctest 输出非空，57 个用例逐条 Passed；测试程序读写真实 `.abc` 文件
> （如 test1.cpp 写出 slappyJim.abc 并读回比对），非空壳；退出码与通过计数一致。

## 实跑命令（本机构建环境）

```bash
# 初始化（幂等）
docker exec -e CONAN_HOME=/var/conan/alembic-1.8.10 hmbs-builder hmbs-conan-init

# 编译验证（构建 + test_package）
docker exec -w "$PWD" -e CONAN_HOME=/var/conan/alembic-1.8.10 hmbs-builder \
  conan create archives/a/alembic/1.8.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 容器默认 PATH 缺 make/ar/coreutils，需 `PATH=/data/service/hnp/bin:/root/usr/local/bin:$PATH`。

## test_package

`test_package/test_alembic.cpp` 真实调用 Alembic + Imath API：用
`AbcCoreOgawa::WriteArchive` 写出含 `smoke_child` 对象、`OV3fProperty`（`Imath::V3f`）
属性的归档，再经 `AbcCoreFactory::IFactory::getArchive` 读回，校验
`getNumChildren()==1` 且子对象名为 `smoke_child`。链接 `alembic::alembic`
（=libAlembic + libImath）。通过：`alembic 1.8.10 smoke test OK`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `FIND_PACKAGE(Imath)` 找不到 Imath | Imath 未发布到制品仓，系统也无 | vendor Imath 源码，独立 cmake 构建安装，CMAKE_PREFIX_PATH 解析 |
| 2 | Imath 配置报 `target_compile_features no known features` | CMake 4.x 无法识别 OHOS clang（id unknown），CMAKE_CXX_COMPILE_FEATURES 空 | 补丁 0001 改用 CXX_STANDARD 属性 |
| 3 | 静态库 libImath-3_1 命名带 SOVERSION 后缀 | Imath 3.x 目标名约定 | package() 规整为 libImath.a，cpp_info.libs 声明 "Imath" |
| 4 | 下游只链 libAlembic.a 链接报未定义符号 | 静态库不内嵌传递目标文件 | cpp_info.libs 同时声明 Alembic 与 Imath |

## 源码修改

### patches/0001-imath-cxx-standard.patch（作用于 vendored Imath 源码）

修改 Imath `config/LibraryDefine.cmake`：将
`target_compile_features(${objlib} PRIVATE cxx_std_${IMATH_CXX_STANDARD} INTERFACE cxx_std_11)`
替换为 `set_target_properties(${objlib} PROPERTIES CXX_STANDARD ${IMATH_CXX_STANDARD} CXX_STANDARD_REQUIRED ON INTERFACE_CXX_STANDARD 11)`。
仅改变 C++ 标准的施加方式（绕开本环境不可用的 target_compile_features），不改 Imath 逻辑；`INTERFACE_CXX_STANDARD 11` 保留原 INTERFACE cxx_std_11 对消费者的 C++11 要求。
Alembic 自身源码未修改。

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
