# json11

json11 is a tiny JSON library for C++11, providing JSON parsing and serialization.

- 官方上游: https://github.com/dropbox/json11
- 版本: 1.0.0 (tag v1.0.0, commit ec4e45219af1d7cde3d58b49ed762376fccf1ace)
- 许可: MIT
- 构建系统: CMake（上游同时提供 Makefile test 目标）
- HarmonyOS 适配: 见 `1.0.0/notes.md`

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.0 | built | 首轮适配（HarmonyOS aarch64） |

## 说明

json11 为 header + 单翻译单元库（json11.hpp + json11.cpp），无第三方运行时依赖（纯 C++ 标准库）。