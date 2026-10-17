# E429 — vvenc 1.14.0 OHOS 构建工程约定：C++ 运行时解析、源码树输出开关、上游测试入口

## 错误特征

三条**与单库绑定**的工程事实，均不会表现为编译报错，而是表现为「构建成功但产物/测试不符合预期」：

- C++ 消费者运行期找不到 `libc++_shared.so`（若误以为需要自行注入 `LD_LIBRARY_PATH`）
- 构建完成后**源码树内出现 `lib/` 与 `bin/`**，且带 `release-shared` / `release-static` 后缀，污染源码导出并干扰补丁生成
- `ctest` 用例数少于预期（shared 构建应为 39 项）

## 触发条件

- 构建系统: cmake
- 阶段: configuration / installation / testing
- 平台: OHOS (HarmonyOS/OpenHarmony PC aarch64, musl libc)

## 根因分析

1. **C++ 运行时解析**：OHOS 设备默认搜索路径已含 `/system/lib64/libc++_shared.so`（实测存在），因此 C++ 共享库的消费者**无需**额外 `LD_LIBRARY_PATH`。误加反而会掩盖真实的链接期问题。
2. **源码树输出开关**：上游 `VVENC_TOPLEVEL_OUTPUT_DIRS` 默认 `ON`，会把 `lib/` 与 `bin/` 直接写进 `CMAKE_SOURCE_DIR` 并追加 `release-<shared|static>` 后缀。Conan 构建（`build()` 内 configure/build/install）必须置 `OFF`。
3. **上游测试入口**：测试由 `cmake/modules/vvencTests.cmake` 的 `add_test` 注册。shared 构建为 **39 项**（vvencinterfacetest 1 + vvenclibtest 6 + 工具/比对 31 + cleanup 1）；static 构建额外含 `Test_vvenc_unit_test`。

## 解决方案

### 推荐方案

在 Conan recipe 中显式固定三项约定：

```python
tc.cache_variables["VVENC_TOPLEVEL_OUTPUT_DIRS"] = "OFF"
tc.cache_variables["VVENC_ENABLE_INSTALL"] = "ON"
tc.cache_variables["VVENC_INSTALL_FULLFEATURE_APP"] = "ON"
```

不以 shared 构建的 39 项 ctest 作为上游测试基线，并**不**为 `libc++_shared.so` 注入 `LD_LIBRARY_PATH`。

### 禁止做法

- ❌ 用 `LD_LIBRARY_PATH` 注入设备上已默认可见的 `libc++_shared.so`（掩盖真实链接问题，且破坏 R36 依赖可消费性判据）
- ❌ 保留 `VVENC_TOPLEVEL_OUTPUT_DIRS=ON` 后靠事后清理源码树（会让补丁生成把产物当变更）
- ❌ 以 static 构建的用例数（含 `Test_vvenc_unit_test`）冒充 shared 构建的上游测试统计

## 验证

```bash
# 源码树应干净（无 lib/ 与 bin/）
ls vvenc-1.14.0/lib vvenc-1.14.0/bin 2>/dev/null || echo "源码树干净"
# 上游测试计数（shared 构建期望 39 项）
ctest --test-dir build -N | tail -3
```

## 关联条目

- 相关: E050（HMDFS 软链）、E092（CMake 无 Platform/HarmonyOS）、E504（install 期 RPATH 改写破坏签名）
