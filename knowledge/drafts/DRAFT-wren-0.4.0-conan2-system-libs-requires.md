# DRAFT-wren-0.4.0-conan2-system-libs-requires：Conan 2.x package_info 系统库误用 requires

> Contributor: pc2-11 (ohpc-executor) | Status: Draft | Updated: 2026-09-08
> Source: wren 0.4.0 适配（conan-verify G2 conan create 首轮失败 → 修复后 8 门禁全过）

## 问题

wren 0.4.0 为纯 C 库，链接系统 libm。conan-init 生成的配方在 `package_info()` 中写
`self.cpp_info.requires = ["m"]`，运行 `conan create` 时 G2 在 package_info() 阶段直接失败：

```text
ERROR: wren/0.4.0@ohpcd/stable: package_info(): There are '(cpp_info/components).requires'
to other internal components that are not defined: ['m']
```

## 根因

Conan 2.x 中 `cpp_info.requires` 的语义是**本包内部组件（components）之间的依赖引用**，
只接受已在 `self.cpp_info.components` 里定义的组件名。把系统库名（`m`）写入 requires，
conan 校验时发现该组件未定义即抛错。

三者的正确分工：

| 声明位置 | 用途 | 示例 |
|---|---|---|
| `requirements()` → `self.requires(...)` | 外部 Conan 包依赖（name/version） | `self.requires("zlib/1.3.1")` |
| `package_info()` → `cpp_info.components.<c>.requires` | 本包组件间引用 | `["core"]` |
| `package_info()` → `cpp_info.system_libs` | 系统库（链接期 -l） | `["m"]` |

## 方案

```python
def package_info(self):
    self.cpp_info.libs = ["wren"]
    # wren links against libm (system library, not a Conan component)
    self.cpp_info.system_libs = ["m"]
```

## 验证

- 修复前：`conan create` 在 package_info() 阶段抛 components not defined 错误（G2 FAIL）。
- 修复后：`conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全 PASS，test_package 消费者
  （真实调用 wrenNewVM/wrenInterpret/wrenFreeVM）通过。
- 反向验证：测试文件使用 `#include "wren.h"` + `wrenNewVM`，链接 libwren + 自动追加 -lm，
  运行打印 "wren 0.4.0 consumer test: OK"。

## 适用边界

- Conan 2.x 配方（Conan 1.x 的 cpp_info.requires 语义不同，不适用）。
- 仅适用于把系统库误写进 requires 的场景；若错误来自真正缺失的外部 Conan 依赖，
  应按 R36 检查依赖发布状态，而非改为 system_libs。

## 反例

```python
# ❌ 系统库误用 requires（触发 components not defined）
self.cpp_info.requires = ["m"]
```

## 限制

- 若 libm 实际来自 Conan 包（如 musl 工具链提供），应使用 self.requires 或确认
  工具链自带，不能一律当作系统库处理。
