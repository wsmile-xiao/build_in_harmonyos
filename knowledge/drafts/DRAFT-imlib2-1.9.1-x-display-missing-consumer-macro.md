# imlib2 1.9.1：无 X 图像库在 OHOS 的消费者编译宏注入（-DX_DISPLAY_MISSING）

## 场景

imlib2 1.9.1（Enlightenment 通用图像库，autotools）适配 HarmonyOS PC。
OHOS 无 X11，configure 传 `--without-x` 成功构建（PNG/ZLIB loader 正常），
但 **test_package / 下游消费者编译一律报 `'X11/Xlib.h' file not found`**。

## 现象

```text
In file included from test_package.c:7:
  .../Imlib2.h:45:10: fatal error: 'X11/Xlib.h' file not found
```

## 根因

`Imlib2.h`（公开头）用 `#ifndef X_DISPLAY_MISSING` 守卫 X11 头：

```c
#include <stddef.h>
#include <stdint.h>
#ifndef X_DISPLAY_MISSING
#include <X11/Xlib.h>          /* ← 消费者编译时命中 */
#endif
```

configure 已在 config.h 定义 `X_DISPLAY_MISSING 1`，但那是**构建期内部头**
（`#include "config.h"` 只存在于库源文件，消费者不包含它）。库配方若不把该宏
注入消费者编译环境，下游必然编译失败——即使库本身构建成功。

## 修复

conanfile.py 的 package_info()：

```python
def package_info(self):
    self.cpp_info.libs = ["Imlib2"]
    if str(self.settings.os) == "OHOS":
        self.cpp_info.cflags = ["-DX_DISPLAY_MISSING"]
```

## 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：test_package（仅公开头
  Imlib2.h + 公开 API create/fill/scale/像素断言）编译链接运行 **RC=0**。
- 未加宏前同一 test_package 编译报 X11/Xlib.h not found（first error 可复现）。

## 边界

- 适用：`--without-x` 构建、公开头以 `X_DISPLAY_MISSING`（或同类守卫）隔离 X11
  头的图像/渲染库（imlib2 系、gdk-pixbuf 类可选 X 依赖库）。
- 反例：真正需要 X11 运行时能力（X 客户端工具、drawable 抓屏）的库不可用宏绕过，
  应按 E530（无 X server 消费者契约/ABI 固定）或提供 X 依赖处理。
- 前置检查：先确认宏确实在 config.h 且公开头确实用该宏守卫，勿盲注入。

## 查重

| 既有条目 | 关系 |
|---|---|
| E530（X11 客户端库无 X server 消费者测试） | 相邻：E530 是"驱动不了真实接口时怎么办"，本条是"编译期宏让消费者能编译"；无条目讲消费者编译宏注入 |
| E527（broadway 后端 wrapper） | 弱相关 |

同 stem 草稿：DRAFT-imlib2-1.9.1-x-display-missing-consumer-macro.kv