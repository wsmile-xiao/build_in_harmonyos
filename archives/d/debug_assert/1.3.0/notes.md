# debug_assert 1.3.0 适配笔记（R02 bootstrap）

## 官方来源核验（2026-08-30）

- 官方仓库: https://github.com/foonathan/debug_assert
  （描述: "Simple, flexible and modular assertion macro."，非 fork）
- 正式版本: 1.3.0 对应官方 tag `v1.3`
  - tag 指向 commit: `5b1142e84a2c585ed2648ba9b4f22ff7594479f9`
  - 上游同时存在 v1.3.1~v1.3.4 修复版本；任务版本固定为 1.3.0，以 `v1.3` 为准
- 官方源码 tarball: https://github.com/foonathan/debug_assert/archive/refs/tags/v1.3.tar.gz
  - SHA-256: `c1a4c049385551b137d8441aa4e25f0b1d2eeeec294a80a3416b1dd06802e279`
  - 内容核验: 含 `debug_assert.hpp`（单头）、`LICENSE`、`CMakeLists.txt`、
    `conanfile.py`（上游自带为 Conan 1.x 旧式，需重写为 Conan 2.x）、`test_package/`
- 许可证: Zlib（"as-is" + 3 条限制）
- 形态: header-only 单头文件库，无编译期产物

## 配方要点

- `package_type = "header-library"`，`no_copy_source = True`；
  `package()` 将 `debug_assert.hpp` 复制到 `include/` 与 `include/debug_assert/`
  （兼容 `#include "debug_assert.hpp"` 与 `#include <debug_assert/debug_assert.hpp>`）
- test_package 使用 CMakeDeps/CMakeToolchain，`find_package(debug_assert CONFIG)`，
  目标 `debug_assert::debug_assert`
- 上游 example.cpp 含必失败断言 `DEBUG_ASSERT(1 == 0, ...)`，test_package 改用
  全部通过的断言 + 自定义 handler 模块验证 API 实质可用

## 状态

- bootstrap 完成；未进入 finish/submit/Push/PR（任务边界：禁止 commit/push/远端操作）
---

**编译结束**: 2026-08-31 10:40
**最终状态**: built
