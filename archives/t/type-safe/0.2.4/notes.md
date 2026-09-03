# type-safe 0.2.4 适配笔记

## 编译环境

- 构建系统：CMake
- 编译器：clang/clang++ 15.0.4
- 目标：HarmonyOS PC arm64
- 状态：built

## 源码与依赖

- 官方源码：`https://github.com/foonathan/type_safe/archive/refs/tags/v0.2.4.tar.gz`
- SHA256：`a631d03c18c65726b3d1b7d41ac5806e9121367afe10dd2f408a2d75e144b734`
- type-safe 是 header-only；源码内嵌 `external/debug_assert/debug_assert.hpp`。
- Conan 制品仓未发现已发布的 `debug_assert/1.3.0`，因此配方将该上游单头文件随 type-safe 一起安装，保证消费者自包含。

## 关键适配

上游和内嵌 debug_assert 的 CMake 最低版本声明较旧。设备上的 CMake 4 默认拒绝该声明，配置时加入官方兼容缓存变量：

```text
-DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

未修改上游源码，也未生成补丁。

## 验证结果

原生 CMake 探索构建执行了：

```text
cmake -S <source> -B <build> -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DTYPE_SAFE_BUILD_TEST_EXAMPLE=ON -DTYPE_SAFE_BUILD_DOC=OFF
cmake --build <build> --parallel 1
ctest --test-dir <build> --output-on-failure
cmake --install <build>
```

- 上游测试：49 个 test case、2788 个断言，全部通过。
- CTest：1/1 测试目标通过。
- 安装产物：type_safe 头文件及其必需的 debug_assert.hpp。
---

**编译结束**: 2026-09-02 12:35
**最终状态**: built
