# DRAFT：`set(CMAKE_CXX_STANDARD ...)` 是普通变量，遮蔽 toolchain 的 cache 变量 —— 只在 `generate()` 抬 cppstd 无效

> 状态：草稿（待知识库主编 promote）
> 来源：osm2pgrouting 3.0.0 适配（libpqxx 8.x 需要 C++20），`archives/o/osm2pgrouting/3.0.0`
> 类别：conan / cmake / 语言标准 / toolchain
> 配套草稿：`DRAFT-osm2pgrouting-3.0.0-bundled-find-modules-probe-build-host`

## 错误特征

`conan install` 一路正常，profile 与 `generate()` 都写着 `cppstd=20`，编译到 libpqxx
的公共头时炸：

```
/libpqxx/include/pqxx/strconv.hxx: error: unknown type name 'std::span'
/libpqxx/include/pqxx/util.hxx: error: no member named 'starts_with' in 'std::string'
#error "libpqxx requires C++20"
```

或者更晚一步，链接期：

```
Target "pqxx" requires the language dialect "CXX20" (with compiler extensions),
but CMake does not know the compile flags to use to enable it.
```

**关键识别信号**：`profile 说 20、报错说 17`。第一反应往往是 libpqxx 或 libc++ 有问题 ——
这时去 `grep -n CMAKE_CXX_STANDARD <源树>/CMakeLists.txt`。

## 触发条件

上游 `CMakeLists.txt` 里有**自己**的标准设定：

```cmake
if (PQXX_VERSION VERSION_GREATER_EQUAL "7.0.0")
  set(CMAKE_CXX_STANDARD 17)
  ...
else()
  ...
endif()
```

而配方/profile 期望的是 20（因为依赖要求）。两件事同时成立即触发：

1. 上游 CMakeLists 在目录作用域里 `set()` 过 `CMAKE_CXX_STANDARD`；
2. 语言标准需要比它更高（典型是 C++17 → C++20）。

## 根因分析

### (1) 普通变量优先于同名 cache 变量

- `CMakeToolchain` 把 cppstd 写进 `conan_toolchain.cmake`，用的是
  `set(CMAKE_CXX_STANDARD 20 CACHE STRING "")` —— 这是 **cache** 变量；
- 上游 `CMakeLists.txt` 紧接着在同一目录作用域执行 `set(CMAKE_CXX_STANDARD 17)`
  —— 这是 **普通** 变量。

CMake 的变量查找顺序里 **普通变量优先**，于是此后 `add_executable` / `add_library`
出来的目标全部按 C++17 编译，libpqxx 8.x 的公共头（用 `std::span`、
`std::string::starts_with`、concepts）自然过不去。

陷阱在于 toolchain 文件看起来完全正确：`conan_toolchain.cmake` 里明明写着 20，
`conan install` 输出的 cppstd 也是 20。

### (2) 那段是版本条件分支，不能"微调"

`PQXX_VERSION` 来自 bundled `FindPQXX.cmake`。配套条目已把
`find_package(PQXX)` 换成 CMakeDeps 的 config 包，该变量不再按上游预期取值，
所以这段分支必须**整段替换**。

### (3) 四条"看起来应该管用"的路都走不通

| 做法 | 为什么无效 |
|------|-----------|
| profile 里把 `cppstd` 改成 20 | 写的是 cache 变量，被普通变量遮蔽 |
| `generate()` 里改 `toolchain.blocks["cppstd"]` | 同上 |
| `conf tools.build:cxxflags=["-std=c++20"]` | CMakeLists 的 `set(CMAKE_CXX_STANDARD 17)` 会生成 `-std=gnu++17`，排在自加 flag 之后 |
| 命令行 `-DCMAKE_CXX_STANDARD=20` | 同样只是 cache 变量 |

## 与相邻条目的关系

- **E096（cmake-cxx-standard-explicit）**：同属"语言标准必须显式、不能靠默认"家族；
  本条补上更隐蔽的一层 —— **显式写了也会被遮蔽**。
- **配套草稿 `DRAFT-osm2pgrouting-3.0.0-bundled-find-modules-probe-build-host`**：
  同一份补丁的另一半；那条改掉 `FindPQXX`，正好让本条 (2) 的版本分支失去输入，
  所以两条必须一起做。
- **E322（header-only INTERFACE 库关闭上游默认 tests 并消费 CONFIG target）**：
  同属"上游 CMake 选项由消费者接管"的家族。

## 修复清单（照抄即可）

```cmake
# patches/0001-CMakeLists.txt.patch 第三个 hunk：整段替换
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

```python
def generate(self):
    toolchain = CMakeToolchain(self)
    ...
    toolchain.blocks["cppstd"].values["cppstd"] = "20"
    toolchain.blocks["cppstd"].values["cppstd_extensions"] = "OFF"   # libpqxx/8.0.1 同款
    toolchain.generate()
```

要点：

1. **两边取值必须一致**。toolchain 的 cppstd 决定依赖包按什么标准构建、也决定 CMake
   缓存里没被 CMakeLists 覆盖到的那些值；补丁写 20 而 profile 留 17，换来的是
   **ABI/stdlib 层面的错配**（莫名其妙的链接或运行期错误），而不是干净的 configure 失败。
2. 若树里别的目标另加 `cxx_std_NN` 编译特性，CMake 取最大值，没问题；**反向**
   （CMakeLists 低于 toolchain）才是坏的。
3. 本工程 `package_type = "application"`，没有"从消费侧 override"的退路，补丁是唯一选项。
   （若是库、且仓库里已有更新的 adaptation revision，优先在下游 override。）

真正有效的只有三条路：

1. 打补丁**改** CMakeLists 里的标准（本条）；
2. 打补丁**删掉**那个 `set()`，让 toolchain 的值生效；
3. 在自己的补丁代码里 `target_compile_features(<tgt> PUBLIC cxx_std_20)`。

## 反例（不要做）

| 反例 | 后果 |
|------|------|
| 只改 profile 或只改 `generate()` 的 cppstd | 编译仍走 C++17，失败点离配置错误很远，容易误判为 libpqxx/libc++ 的问题 |
| `conf tools.build:cxxflags=["-std=c++20"]` | 被 CMakeLists 生成的 `-std=gnu++17` 后置覆盖；且依赖包仍按 17 构建 |
| 补丁写 20 而 profile 留 17（或反之） | 依赖与本工程语言标准不一致，CMake 不报错，问题推迟到链接/运行期 |
| 看到 `conan_toolchain.cmake` 里有 20 就认为配置正确 | cache 变量被同名的普通变量盖掉，读文件看不出任何异常 |
