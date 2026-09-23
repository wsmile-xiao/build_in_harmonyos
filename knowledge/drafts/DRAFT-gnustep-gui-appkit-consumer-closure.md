# DRAFT-gnustep-gui-appkit-consumer-closure - AppKit 消费者必须继承 gnustep-base 传播和 GNUstep 运行时标志

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-29
> **Source event**: gnustep-gui 0.32.0 HarmonyOS PC adaptation, PR #7095

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

GNUstep GUI 的 `test_package` 不是普通 C smoke test，而是一个真实的 Objective-C AppKit
消费者。它包含 `AppKit/AppKit.h`，并构造 `NSImage`、`NSBezierPath` 和 `NSColor`。

如果消费者没有继承被测包导出的 `gnustep-base` 头文件/库传播，或者没有补上 GNUstep
运行时标志，就会出现：

- `AppKit/AppKit.h` 找不到；
- `NSImage` / `NSBezierPath` / `NSColor` 类型不可见；
- 链接阶段缺少 Objective-C runtime 符号；
- consumer 只验证了“能编译一个 C 程序”，但没有验证真正的 AppKit ABI。

## 根因

GNUstep GUI 的 ABI 不是“只要有 `libgnustep-gui.so` 就行”：

1. 头文件会向下游暴露 `gnustep-base`；
2. 运行时假设与 GNUstep Objective-C ABI 一致；
3. 测试消费者必须和 recipe 使用同一组 Objective-C 选项。

因此，`transitive_headers=True`、`transitive_libs=True`、`-fobjc-runtime=gcc`、
`-fblocks` 和 `-fconstant-string-class=NSConstantString` 都是这个消费者闭环的一部分。

## 推荐方法

把 `test_package` 写成一个真实的 AppKit Probe：

```objc
#import <AppKit/AppKit.h>
NSImage *image = [NSImage new];
NSBezierPath *path = [NSBezierPath bezierPath];
NSColor *color = [NSColor blackColor];
```

并在 CMake 里显式保留 GNUstep 运行时标志：

```cmake
target_link_options(test_gnustep_gui PRIVATE -fobjc-runtime=gcc -fblocks)
target_link_libraries(test_gnustep_gui PRIVATE gnustep-gui::gnustep-gui)
```

如果 recipe 的 package_info 已经导出这些 flag，就让消费者自动继承；如果没有，
也必须在消费者侧显式补齐，不能退化成纯 C 连接测试。

## 与已有知识的差异

- 本草稿不是“static library 传递头文件”的通用问题，而是 GNUstep AppKit 的
  Objective-C ABI 闭环。
- 重点不是是否能找到一个库，而是消费者是否真的按 AppKit 语义运行。

## 禁止做法

- 不要把 `test_package` 降级成普通 C 程序。
- 不要去掉 `-fobjc-runtime=gcc`、`-fblocks` 或 `-fconstant-string-class=NSConstantString`。
- 不要把 `transitive_headers` / `transitive_libs` 关掉后再声称 AppKit 兼容。

## 证据来源

- `archives/g/gnustep-gui/0.32.0/test_package/CMakeLists.txt`
- `archives/g/gnustep-gui/0.32.0/test_package/test_gnustep_gui.m`
- `archives/g/gnustep-gui/0.32.0/conanfile.py`
