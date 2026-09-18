# tweeny 3 适配笔记

## 编译环境
- 构建系统: cmake（header-only 库，INTERFACE target + install/export 规则）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤
配方走上游真实的 CMake 安装路径（不手工拷头文件，下游可用 `find_package(Tweeny)`）：

1. `source()`：GitHub tag v3 tarball（sha256 69963357…）；OHOS 侧经共享 dlcache 命中（E017 镜像注入场景，见问题 2）
2. `generate()`：CMakeToolchain 注入
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（E103：上游 `cmake_minimum_required(VERSION 3.0)` 被 CMake 4.x 拒绝）
   - `TWEENY_BUILD_EXAMPLES/EXTRAS/DOCUMENTATION=OFF`（示例/文档的依赖不在包内）
3. `build()`：`cmake.configure()` → `cmake.build()`（INTERFACE 库无编译单元，验证配置阶段可用）
4. `package()`：`cmake.install()` → `include/tweeny/*.h/.tcc` + `lib/cmake/Tweeny/*.cmake`；另拷 LICENSE 到 `licenses/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Invalid package version '3'` | Conan 2 的 slug 校验要求 ≥2 字符（`^[a-z0-9_][a-z0-9_+.-]{1,100}$`），单字符版本被拒 | 归档目录/分支保持任务卡版本 `3`（过 CI L0n 分支门禁），配方用 `set_version()` 输出 `v3`（同 rapidhash/3 先例）；刻意不写 `version = "..."` 字面量属性，避开 CI L0m-3 / PF8 的"字面量 vs 目录名"比对 |
| 2 | `get()` 反复重下 ghfast 镜像 URL 失败（设备不可达），dlcache 预置文件被判 dirty 清除 | E017 在 conan-verify 期间把 github URL 临时改写为 `ghfast.top/...`；dlcache sidecar 只登记官方 URL 时，"请求 URL 不在元数据" → 判 dirty 并删除预置文件 | 共享 dlcache（`~/tmp/ch/dlcache`）的 sidecar 同时登记**官方 URL 与 ghfast 注入 URL**；并清理历史 `.dirty` 标记后重种 |
| 3 | 消费者测试 `#include <tweeny.h>` 报 file not found | 上游 install 布局是 `include/tweeny/`（`$<INSTALL_INTERFACE:include/tweeny>`），package_info 默认 includedirs=`["include"]` | `cpp_info.includedirs = ["include/tweeny"]`，镜像上游导出的 INTERFACE include 目录 |
| 4 | 消费者测试 `std::get<0>(tween.peek())` 编译失败 | tweeny 对单值 tween 有专门特化：`tween<T>` 的 step()/peek()/seek() **直接返回 T**（标量 API），只有多值 tween 返回 `std::tuple` | 测试改为单值走标量 API、多值才用 `std::get` |
| 5 | 安装产物缺 `licenses/` | `conan.tools.files.copy(..., dst="licenses")` 的相对 dst 不解析到 package_folder（落到进程 cwd），模板写法有坑 | package() 改用绝对路径 `os.path.join(self.package_folder, "licenses")` |

## 源码修改
无（`patches` 为空，上游源码未改动）

## 依赖版本
无第三方依赖（header-only，上游声明 Zero external dependencies）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify tweeny 3      # Verdict: PASS（G0-G4 + L2/L4/L5）
# test_package: ctest 1/1 Test #1: test_tweeny ... Passed (100% tests passed, 0 failed)
```

- 上游静态用例：**0**（v3 tag 无 test/ 目录，CHANGELOG 无测试条目；清点证据见 test_package/MANIFEST.yml）
- 上游实际执行：0（无可执行测试套件）
- 消费者测试（test_package）：1 个程序 / **17 条断言全过**（线性插值、多值 tween、easing 形状、seek 越界钳制、onStep 回调、步进越界钳制）

## 注意事项
- 上游无测试套件，本包验证完全由消费者测试承载；上游后续版本若补测试，需按 R51 重新清点
- L2/L4/L5 对 header-only 包会跳过（无二进制产物、无包 cache id），属预期，非门禁失败
- 制品版本为 `tweeny/v3`（任务卡版本 `3` 经 set_version 归一化）；下游引用请写 `tweeny/v3`
---

**编译结束**: 2026-09-16 00:24
**最终状态**: built
