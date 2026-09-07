# boost1.84-iostreams

Boost.Iostreams 组件拆分包（Debian libboost-iostreams1.84 模式）——从
Boost 1.84.0 官方发行版中单独构建 Boost.Iostreams 组件，提供：

- `boost1.84-iostreams/1.84.0`：libboost_iostreams.a（5 TU：
  file_descriptor/mapped_file/zlib/gzip/bzip2，带上游 Jamfile 要求的
  BOOST_IOSTREAMS_USE_DEPRECATED 宏）+ 完整 Boost 头文件树
- 压缩后端：zlib/1.3.1 + bzip2/1.0.8（Conan 传递依赖自动链接）
- CMake 组件目标：`boost1.84-iostreams::iostreams`
  （`find_package(boost1.84-iostreams COMPONENTS iostreams)`；组件包用
  独立 CMake 包名以避免与元包 cmake_file_name "Boost" 的 CMakeDeps 冲突）
- Conan 组件：`boost1.84_iostreams`

与 `boost/1.84.0` 元包的关系：元包的 iostreams 段只编了 4 TU 且未带
上游要求的 BOOST_IOSTREAMS_USE_DEPRECATED 宏（deprecated 重载符号缺失）、
无 bzip2 后端；本组件包补齐两者，自包含（头文件独立携带），下游无需先
安装元包。

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.84.0 | built | 首次适配（方案 A 独立裁剪编译，zlib+bzip2 双后端，见 1.84.0/notes.md 选型章节） |

上游：https://github.com/boostorg/iostreams（发行 tarball 见各版本 conandata.yml）
