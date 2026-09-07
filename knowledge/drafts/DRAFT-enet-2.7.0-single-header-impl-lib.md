# DRAFT-enet-2.7.0-single-header-impl-lib：stb-style 单头实现库的 Conan 配方形态（真实静态库，勿误用 header-only）

> Contributor: pc3-4 | Status: Draft | Updated: 2026-09-05
> Source: enet 2.7.0 适配（task enet-2.7.0-r01-pc3-4-20260904T191522Z）

## 背景

enet 2.7.0 为单头实现库：`include/enet.h` 内含完整实现体，消费者
`#define ENET_IMPLEMENTATION` + `#include "enet.h"` 实例化。上游 CMake
用 3 行 `test/library.c`（仅做上述两行）编译出真实的 `libenet.a`。
若按"单头实现 == header-only"误用 `package_type=header-library` / no-op
build()（E257 场景），会丢失真实库产物与链接目标。

## 形态判断（关键）

```text
grep add_library <source>/CMakeLists.txt
  -> add_library(enet_static STATIC test/library.c)   # STATIC = 真实库
  -> add_library(enet_test_interface INTERFACE)       # 仅测试用接口目标
```

判断依据：库目标为 STATIC/SHARED（真实产物）→ 普通 library 配方；
为 INTERFACE（无 .a）→ 走 E321/E322 header-only 配方。

## 修复（配方要点）

1. `package_type="library"`，`ENET_STATIC=ON`（R26 系统同名库静态）；
2. `ENET_TEST=OFF` 仅打包库，上游测试以 `ENET_TEST=ON` 单独构建运行
   （R51 双口径台账，不进配方 build()）；
3. `package_info()`：`libs=["enet"]`。

```python
# generate()
tc.variables["ENET_STATIC"] = "ON"
tc.variables["ENET_SHARED"] = "OFF"
tc.variables["ENET_TEST"] = "OFF"   # 打包不编测试；测试单独验证
# package_info()
self.cpp_info.libs = ["enet"]
```

上游无 CMake 时：自建实现 TU（`#define ENET_IMPLEMENTATION` +
`#include "enet.h"`）由 Conan 编译为静态库，重复同样形态。

## 验证

- `libenet.a` 正常产出（ar archive）；下游 find_package 链接成功
- conan-verify G0-G4 + L2/L4/L5 全 PASS；W3 100%
- test_package 消费者回环测试：enet_initialize / host_create / host_connect /
  peer_send / packet 校验 / peer_disconnect / host_destroy 7 项 API 全过

## 适用边界

- stb 风格单头实现库（stb_image/cglm/flecs/enet 等）
- 反例：纯 INTERFACE header-only 库仍走 E321/E322；
  ENET_TEST=OFF 不替代上游测试验证，MANIFEST.yml 如实记录

## 查重差异

- E257（header-only 无构建系统 no-op build）：不覆盖"实现体 TU 编译为真实 .a"
- E321/E322（header-only INTERFACE 配方）：边界为无真实库产物，与本场景不同
- 图谱 E102/E148/E213/E233/E244（UDP/mmsghdr/POLLRDHUP 网络平台问题）：
  与本场景（打包形态）无关
- 草稿目录无相关条目 → 未命中，新增差异成立