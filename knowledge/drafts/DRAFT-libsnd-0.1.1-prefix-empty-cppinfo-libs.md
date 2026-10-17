# DRAFT-libsnd-0.1.1：上游 CMake 目标 PREFIX "" 时 cpp_info.libs 必须去 lib 前缀 —— CMakeDeps 库解析失败的正确修法

> Contributor: pc1-13 | Status: Draft | Updated: 2026-09-06
> Source: libsnd 0.1.1 适配任务（OHOS aarch64 设备单端验证，conan create G2）
> 关联先例: E221（CLI+公开库建模，触发层重叠）、E103/E187/DRAFT-E321（CMake 版本兼容，不同问题）

## 背景

libsnd 0.1.1 是 C++14 静态 DSP 库（CMake 构建，无依赖）。上游 CMakeLists.txt 对
`libsnd` 目标设置 `set_target_properties(libsnd PROPERTIES PREFIX "")`，导致
安装归档文件名为 `libsnd.a`（无平台默认的额外 `lib` 前缀——目标名本身已含 lib）。

## 错误特征

conan create 主库构建成功后，test_package 消费者 CMakeDeps 配置阶段失败：

```text
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'libsnd' not found in package.  If 'libsnd' is a system library,
  declare it with 'cpp_info.system_libs' property
Call Stack (most recent call first):
  .../libsnd-Target-release.cmake:23 (conan_package_library_targets)
  CMakeLists.txt:5 (find_package)
```

注意迷惑点：包目录里**确实存在** `lib/libsnd.a`（find 可证实），报错却说找不到
——CMakeDeps 按 `lib<name>.a` 模板找 `liblibsnd.a`，与真实文件名 `libsnd.a` 不匹配。

## 根因

Conan 配方 `package_info()` 照抄目标名 `cpp_info.libs = ["libsnd"]` 时，CMakeDeps
按平台库模板拼文件名：`lib + libsnd + .a` = `liblibsnd.a`，在包内不存在。
根因是**打包元数据（libs 名）与安装物（实际归档基名）不一致**，不是缺系统库，
因此按报错提示把库加进 `cpp_info.system_libs` 是错误方向。

## 方案

按包内实际归档基名填写 `cpp_info.libs`：PREFIX "" 产物为 `<name>.a`，则
`cpp_info.libs = ["snd"]`（CMakeDeps 自动补回 `lib` 前缀，解析到 `libsnd.a`）。

```python
def package_info(self):
    # 上游 PREFIX ""：打包产物是 libsnd.a（无额外 lib 前缀），
    # CMakeDeps 按 lib<name>.a 解析，故 libs 填 "snd"。
    self.cpp_info.libs = ["snd"]
```

修复后 conan create 全流程通过（G2：test_package 消费者 configure/compile/link/run
真实执行，`test_libsnd` 与鸿蒙专项 `test_ohos` 均 PASS）。

## 验证

1. `find <package>/lib -name "*.a"` → `libsnd.a`（与 libs 声明对照）
2. conan create 复验：CMakeDeps imported target 消费者全链路通过，无硬编码路径
3. 设备（aarch64 OHOS）上运行消费者二进制，退出码 0

## 适用边界

- 适用：上游 CMake 对库目标设 `PREFIX ""`（或 `CMAKE_STATIC_LIBRARY_PREFIX` 为空）
  的静态库；目标名以 lib 开头但仍显式设空前缀的工程。
- 不适用：动态库（.so 无前缀需求场景不同）；Meson/autotools 包（无 PREFIX 属性）；
  真缺系统库的包（应走 system_libs，但先核对安装物）。

## 反例/教训

- 按报错提示把 `libsnd` 加入 `cpp_info.system_libs`：掩盖命名问题，干净环境链接失败。
- test_package 硬编码 `.a` 路径：测试假通过，真实下游仍失败（同 E221 forbid 面）。
