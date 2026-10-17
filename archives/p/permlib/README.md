# permlib

PermLib 是一个**纯头文件 C++ 模板库**，用于置换群与组合搜索计算：BSGS（base and strong
generating set）数据结构、轨道/稳定化子/集合像计算、字典序最小集合代表、回溯搜索
（classic 与 partition 两套剪枝）。常用于多面体自同构群、图自同构、对称性约化等场景。

- **上游仓库**: https://github.com/tremlin/PermLib
- **License**: BSD-3-Clause
- **构建系统**: CMake（上游自带；本仓配方用 CMake 驱动上游测试）
- **类型**: Header-only 库（无 `.a`/`.so`，无命令行工具 ⇒ 不需要 `commands.json`）
- **公开头文件**: `include/permlib/**`（84 个），入口头 `permlib/permlib_api.h`
- **外部依赖**: Boost（公开头直接用 `boost::shared_ptr`/`dynamic_bitset`/`foreach`/
  `counting_iterator` 等；实测只需 Boost 头，链接期零 boost 符号）

## 可用版本

| 版本 | 状态 |
|------|------|
| 0.2.9 | built |

## OHOS 适配要点

1. **boost 必须按组件传递**：permlib 的公开头直接 `#include <boost/...>`，但 boost 配方
   声明了 components 之后，包级目标（`boost::boost`）的 include 目录为空。配方因此写
   `cpp_info.requires = ["boost::headers"]`，消费者才能拿到 boost 的 include 路径。
2. **新版 Boost 的间接包含变化**：Boost 1.90 起 `boost::next()` 不再由 `boost/utility.hpp`
   等头间接引入，4 个使用点补 `<boost/next_prior.hpp>`（补丁无平台宏，任意平台同一份）。
3. **上游一个潜在缺陷**：`abstract_bsgs.h` 的 `setStabilizer()` 调用了未声明的
   「已算好 support」构造重载，实例化即编译失败；配方补一个语义等价的重载。
4. **测试驱动自备**：上游 `test/CMakeLists.txt` 用 legacy 变量
   `${Boost_UNIT_TEST_FRAMEWORK_LIBRARY}` 链接 Boost.Test，而 Conan 生成的
   `BoostConfig.cmake` 只给 imported target。配方用 `files/CMakeLists.txt` 构建**同一批
   上游源文件**（13 个 `test/*.cpp` 一字未改）并由 ctest 真实执行。

## 用法（消费者）

```python
# conanfile.py
def requirements(self):
    self.requires("permlib/0.2.9")
```

```cmake
find_package(permlib CONFIG REQUIRED)
target_link_libraries(app PRIVATE permlib::permlib)   # boost 头随之传递
```

```cpp
#include <permlib/permlib_api.h>
```

## 参考资料

- 上游仓库 / 文档: https://github.com/tremlin/PermLib
- 版本级适配记录: `archives/p/permlib/0.2.9/notes.md`
