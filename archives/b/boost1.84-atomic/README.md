# boost1.84-atomic

Boost.Atomic 组件拆分包（Debian libboost-atomic1.84 模式）——从 Boost 1.84.0
官方发行版中单独构建 Boost.Atomic 组件，提供：

- `boost1.84-atomic/1.84.0`：libboost_atomic.a（lock_pool.cpp 编译）+ 完整
  Boost 头文件树
- CMake 组件目标：`boost1.84-atomic::atomic`
  （`find_package(boost1.84-atomic COMPONENTS atomic)`；组件包用独立
  CMake 包名以避免与元包 cmake_file_name "Boost" 的 CMakeDeps 冲突）
- Conan 组件：`boost1.84_atomic`

与 `boost/1.84.0` 元包的关系：元包聚合了 headers/filesystem/regex/
program_options/iostreams；本组件包是其 atomic 维度的拆分形态，
自包含（头文件独立携带），下游无需先安装元包。

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.84.0 | built | 首次适配（方案 A 独立裁剪编译，见 1.84.0/notes.md 选型章节） |

上游：https://github.com/boostorg/atomic（发行 tarball 见各版本 conandata.yml）
