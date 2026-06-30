# lexbor

**描述**: Open source HTML Renderer library

lexbor 是一个快速、轻量级的 HTML/CSS 解析器库，支持完整的 DOM 操作。

## 项目信息

- **项目主页**: http://lexbor.com
- **许可证**: Apache-2.0
- **源码**: https://github.com/lexbor/lexbor

## 已编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.6.0 | built | 2026-05-29 |

## 功能特性

- HTML5 解析器（符合规范）
- CSS 解析器
- DOM API（完整支持）
- 高性能、低内存占用
- 纯 C 实现，无依赖

## 使用方法

安装预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lexbor 2.6.0
```

编译依赖（CMake 项目）：

```cmake
find_package(lexbor REQUIRED)
target_link_libraries(your_target liblexbor)
```

## 注意事项

- 无命令行工具（纯库）
- 需要处理 SSL 证书问题（访问 GitHub）
- CMake 构建系统