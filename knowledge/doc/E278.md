# E215：CMake 条件排除内部目标后将目标名静默降级为 `-l` 库名

## 错误特征
项目配置阶段成功，直到链接消费者目标时才出现裸 `-l` 失败。该行本身只是初筛线索；
还必须从目标图和链接命令得到下面两个结构化诊断标记，才能匹配本条目：

```text
ld.lld: error: unable to find library -linternalTarget
CMAKE_INTERNAL_TARGET_MISSING:internalTarget
CMAKE_BARE_LINK_ITEM:-linternalTarget
```

生成的 Ninja/Make 链接行包含 `-linternalTarget`，但源码本应通过
`add_library(internalTarget ...)` 或项目 helper 定义同名内部目标。

## 触发条件
- 构建系统: CMake
- 阶段: configuration/linking
- 典型条件: 测试、示例或可选组件开关关闭了定义目标的 `add_subdirectory()`，
  但消费者的 `target_link_libraries()` 没有使用同一条件。

## 根因分析
CMake 对 `target_link_libraries(consumer PRIVATE internalTarget)` 有两种解释：如果
`internalTarget` 已定义，它建立目标级依赖并使用产物路径；如果目标未定义，该裸
名称会被当作外部库名，生成 `-linternalTarget`。因此配置阶段不一定报错，错误会
推迟到大型工程的最终链接阶段。

首先检查目标定义、`if(TARGET ...)`、条件 `add_subdirectory()` 和相关 option。
Cling 1.3 的具体案例中，驱动无条件链接 `clingUserInterface`，而该目标只在
`CLING_INCLUDE_TESTS=ON` 时定义；关闭测试后 Build #8327 到 94% 才失败。

## 解决方案

### 推荐方案
沿消费者的 `target_link_libraries()` 反查目标定义：

1. 用 `cmake --build build --target help` 确认目标是否存在。
2. 检查定义目标的 `add_subdirectory()` 是否被测试或可选开关排除。
3. 运行时必需组件移出仅测试条件；真正可选的组件则用同一条件同时守卫定义与链接。
4. 重新生成构建图，确认目标存在且链接行不再含裸 `-l<target>`。

### 禁止做法
- 不要仅凭 `unable to find library -l...` 就增加 Conan 依赖、`-L` 或同名空壳库。
- 不要把项目内部 CMake 目标误报为尚未发布的三方依赖。

## 验证
```bash
INTERNAL_TARGET=internalTarget
BUILD_DIR=build
cmake --build "$BUILD_DIR" --target help | grep -F "$INTERNAL_TARGET"
! grep -R -F -- "-l${INTERNAL_TARGET}" "$BUILD_DIR"
```

Cling 的具体回归把 `INTERNAL_TARGET` 设为 `clingUserInterface`；可复用命令不固定该名称。

## 关联条目
- 易混淆: E050（HMDFS 符号链接）、E191（libc++ 探测）、E208（Perl XS/libc）
- 来源: Cling 1.3 PR #2936 Build #8327；CMake `target_link_libraries` 官方语义
