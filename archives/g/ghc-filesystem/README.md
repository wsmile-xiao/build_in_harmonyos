# ghc-filesystem

ghc::filesystem 是 C++17 `std::filesystem` 的可移植兼容实现（header-only，C++11/14/17 可用），
由 Steffen Schümann (gulrak) 维护，MIT 许可证。本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

https://github.com/gulrak/filesystem

## 许可证

MIT

## 特性

- header-only：仅 `include/ghc/*.hpp`，无编译产物、无链接库
- 提供 `ghc::filesystem` 命名空间，API 与 C++17 `std::filesystem` 对齐
- 支持 filesystem / fs_std 转发头与单文件头两种使用方式
- OHOS 无额外依赖，直接 include 使用

## 编译信息

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 1.5.14 | bootstrap | 2026-08-30 | header-only |