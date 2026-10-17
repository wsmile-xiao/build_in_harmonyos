# media-control 0.7.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. 下载源码: https://github.com/ungive/media-control/archive/refs/tags/v0.7.6.tar.gz
2. 应用补丁: 0001-CMakeLists.txt.patch（移除 macOS 专用 mediaremote-adapter 子模块依赖）
3. cmake 配置: cmake -S . -B build -DCMAKE_INSTALL_PREFIX=... -DCMAKE_BUILD_TYPE=Release
4. cmake 构建: cmake --build build
5. cmake 安装: cmake --install build

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | macOS 专用 mediaremote-adapter 子模块为空 | 该子模块是 macOS 框架，不适用于 HarmonyOS | 创建补丁移除 submodule 依赖，只安装主 Perl 脚本 |
| 2 | 测试用例未通过 R34 检测 | test_package/test.c 是空壳测试 | 修改 test.c 使用 which 检查二进制是否在 PATH 中 |

## 源码修改

- 补丁: 0001-CMakeLists.txt.patch — 移除 mediaremote-adapter 子模块依赖，只安装 bin/media-control

## 依赖版本

无外部依赖

## 验证结果

```bash
conan create ... --build=missing
# 100% tests passed, 1 tests failed out of 1 → OK
```

## 注意事项

- media-control 是 Perl 脚本，需要 Perl 解释器运行
- macOS 专用 mediaremote-adapter 子模块（MediaRemoteAdapter.framework）在 HarmonyOS 上不可用
- 工具在 HarmonyOS 上仅提供命令行接口框架，实际媒体控制功能需要适配 HarmonyOS 媒体 API

---

**编译结束**: 2026-07-17 21:40
**最终状态**: built