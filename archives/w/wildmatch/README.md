# wildmatch

wildmatch 是一个 BSD 许可的 C/C++ 库，提供 git/rsync 风格的通配符模式匹配功能。

## 上游信息
- **仓库**: https://github.com/davvid/wildmatch
- **许可证**: BSD-2-Clause
- **语言**: C/C++

## 功能特性
- Git 风格的通配符匹配（支持 `*`、`?`、`**`、`[...]` 等）
- 提供 C 和 C++ API
- 兼容 rsync 和 git 的模式匹配语义
- 轻量级，无外部依赖

## HarmonyOS 适配说明
wildmatch 是一个纯 C/C++ 库，使用 CMake 构建系统，适配到 HarmonyOS PC（arm64）平台无架构特定问题。

### 适配版本
- 0.9: 首次适配

### 依赖项
无运行时依赖。

### 构建系统
CMake（最低版本 3.5.0）

## 使用示例
```c
#include <wildmatch/wildmatch.h>

// 基本匹配
wildmatch("*.txt", "file.txt", 0);  // 返回 WM_MATCH

// Git 风格匹配
wildmatch("foo/**/*.c", "foo/bar/baz.c", WM_PATHNAME);  // 返回 WM_MATCH
```

## 相关链接
- [官方文档](https://github.com/davvid/wildmatch)
- [测试套件](https://github.com/davvid/wildmatch/tree/main/tests)
