# chipmunk-physics 7.0.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，minimum 3.7）
- 编译日期: 2026-09-08
- 编译器: clang/clang++（profile）
- 状态: built

## 编译步骤

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_DEMOS=OFF -DINSTALL_DEMOS=OFF \
    -DBUILD_SHARED=OFF -DBUILD_STATIC=ON -DINSTALL_STATIC=ON
cmake --build build
cmake --install build
```

demo/ 需要 GLUT，在 OHOS 上不适用，始终关闭（上游非 Apple 默认也是 OFF）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cpHastySpace.c:11: fatal error: 'sys/sysctl.h' file not found` | OHOS musl 无 sys/sysctl.h；该 include 对非 Windows 无条件生效，而 sysctl 调用实际只在 `#ifdef __APPLE__` 分支使用 | 补丁 0001-src-cpHastySpace.c.patch：include 加 `__APPLE__` 守卫（+2/-0），逻辑零改动 |

## 源码修改

- `patches/0001-src-cpHastySpace.c.patch`：仅将 `#include <sys/sysctl.h>` 用
  `#if defined(__APPLE__)` 包裹。见上表。

## 依赖版本

无外部依赖（仅 libc/libm）。

## 上游测试清点（R51）

- 上游无自动化测试套件：源码树无 tests/ 目录、无 check/test 目标；demo/ 为需要
  GLUT 的交互演示程序（非测试，且 OHOS 无 GL 桌面栈）；上游静态用例数 N_static = 0。
- 消费者测试（test_package）：真实物理模拟——1kg 半径 5 的小球从 50 单位高度落到
  摩擦 0.7/弹性 0.4 的地面线段，180 步（3 秒）后断言：静止于地面（y≈半径，误差 <2）、
  速度为 0、无水平漂移；覆盖 cpSpace/cpBody/cpShape/cpMomentForCircle 等 API。
  conan test() 1/1 passed（探索构建实测：position=(0.000, 4.979) speed=0.000）。

## 注意事项

- 上游 tag 归档（github archive）与 release tarball 内容一致，sha256 以
  conandata.yml 为准；GitHub release 资产名与 codeload tag 归档实测以 tag 归档可用。
- 库产物：静态 libchipmunk.a（默认 shared=False）；动态版可经 shared=True 开关构建。
- 本包（chipmunk-physics）与另一位参赛者的 chipmunk 7.0.3（PR #8764）为不同归档目录、
  不同任务号（6447 vs 6446），互不影响。

## 编译结束

- 最终状态: built（conan-verify 全过、W3 本地 CI 通过、W4 审计 P0=0 P1=0）
- 结束标记: 2026-09-09
---

**编译结束**: 2026-09-09 02:40
**最终状态**: built
