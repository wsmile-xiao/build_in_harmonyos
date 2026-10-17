# string_id 2.0-3 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built（已完成设备验证，尚未上传制品）

## 编译步骤

1. 在设备 `$HOME/tmp/string_id-2.0-3-src` 以 `v2.0-3` 检出上游源码，提交为
   `0a50fa4950752c48ae440d0724b110100039c451`。
2. 直接使用上游 CMakeLists.txt 配置时，CMake 4.1.2 因 `cmake_minimum_required(VERSION 2.8)` 拒绝配置。
3. 配方通过 `CMakeToolchain` 注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，并以
   `BUILD_SHARED_LIBS=OFF`、数据库和多线程数据库开启的配置完成 `conan create`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败：`Compatibility with CMake < 3.5 has been removed from CMake` | 设备 CMake 4.1.2 不再兼容上游声明的 CMake 2.8 policy 版本 | 在 Conan 的 `CMakeToolchain` 中设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；未修改上游源码 |
| 2 | shared 模式 example 找不到 `libfoonathan_string_id.so` | example 在 build 阶段运行，Conan 的 `conanrun` 尚未包含当前构建目录 | 仅为 shared example 进程前置 `LD_LIBRARY_PATH=$build_folder`，静态模式保持原有运行方式 |

## 源码修改

本次无上游源码补丁。

## 依赖版本

无 Conan 依赖；仅使用设备系统 C++ 标准库和工具链。

## 验证结果

```bash
# 上游探索验证（设备）
cmake -S "$HOME/tmp/string_id-2.0-3-src" \
  -B "$HOME/tmp/string_id-2.0-3-upstream-build-policy35" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DFOONATHAN_STRING_ID_DATABASE=ON \
  -DFOONATHAN_STRING_ID_MULTITHREADED=ON
cmake --build "$HOME/tmp/string_id-2.0-3-upstream-build-policy35" -- -j1
ctest --test-dir "$HOME/tmp/string_id-2.0-3-upstream-build-policy35" --output-on-failure
"$HOME/tmp/string_id-2.0-3-upstream-build-policy35/foonathan_string_id_example"

# Conan 配方验证（设备，分支同步到同一 SHA 后）
conan create archives/s/string_id/2.0-3 --user=ohpcd --channel=stable \
  -pr:h="$HOME/ws/wt-string_id-2.0-3/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/wt-string_id-2.0-3/ci/conan/profiles/ohos-aarch64" \
  --build=missing

# shared 选项补充验证（设备）
conan create archives/s/string_id/2.0-3 --user=ohpcd --channel=stable \
  -pr:h="$HOME/ws/wt-string_id-2.0-3/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/wt-string_id-2.0-3/ci/conan/profiles/ohos-aarch64" \
  -o "string_id/*:shared=True" --build="string_id/*"

# conan-verify（设备）
python3 scripts/ohc-run.py conan-verify string_id 2.0-3 \
  --profile "$HOME/ws/wt-string_id-2.0-3/ci/conan/profiles/ohos-aarch64" \
  --user ohpcd --channel stable
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/*.hpp` | string_id 公共头文件 |
| `include/config_impl.hpp` | CMake 生成的配置头文件 |
| `lib/libfoonathan_string_id.a` | 默认静态库 |

## 注意事项

上游未声明 `install()` 规则，也未注册任何 CTest 用例；因此 recipe 的 `package()` 显式复制构建产物，`build()` 直接运行 `ctest --output-on-failure` 并额外运行官方 example。设备上的 `ctest` 输出为 `No tests were found!!!` 且返回 0，不应在 PR 中虚报上游单元测试数量。使用设备默认 profile 会错误注入 `-stdlib=libstdc++`；验证统一使用仓库 `ci/conan/profiles/ohos-aarch64`（`libc++`、C++17 及设备编译器路径）。shared 模式另行验证通过，example 运行时使用构建目录的临时 `LD_LIBRARY_PATH`。
---

**编译结束**: 2026-09-03 02:32
**最终状态**: built
