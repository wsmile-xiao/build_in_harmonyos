# E429 — Qt 应用优先选择已发布的功能变体

## 错误特征

Qt 应用 CMake 配置报告 `Qt6PrintSupportConfig.cmake` 缺失或 `Qt6::PrintSupport` 不存在。切换到具备该模块的 `qtbase` 版本后，Conan 又报：

```text
Conflict between qtbase/6.11.1 and qtbase/6.11.1.3
```

## 触发条件

- 构建系统：CMake + Conan 2
- 平台：HarmonyOS PC aarch64
- 阶段：CMake configure 或 Conan 依赖图解析
- 适配案例：官方 XaoS 4.3.4 要求 Qt Widgets、PrintSupport 和 LinguistTools。`qtbase/6.11.1` 将 PrintSupport 关闭；仓库已有 `qtbase/6.11.1.3` 启用 PrintSupport，但 `qttools/6.11.1.1` 的配方仍引用旧的 qtbase 版本。

## 根因分析

共享 Qt 基础包不同修订可能包含不同模块集合。首先要确认所需 CMake 模块是否已由另一个兼容的 HarmonyOS qtbase 配方提供。若只检查默认版本，会把“默认包裁剪了模块”误判成“平台没有模块”。选择带模块的版本后，Conan 仍会收敛所有传递依赖；旧版 Qt 工具配方的固定版本声明会造成版本冲突。使用 override 后，Qt 工具包的依赖包 ID 也可能变化，因此仓库中已有的工具包二进制不一定兼容。

## 解决方案

### 推荐方案

1. 在修改上游 CMake 或裁剪功能前，检查已发布的 HarmonyOS qtbase 配方及其包内 CMake 配置，确认是否存在启用所需模块的兼容版本。
2. 让应用的 Conan 配方用 `override=True` 把传递依赖收敛到该版本：

   ```python
   self.requires("qtbase/6.11.1.3", override=True)
   ```

3. 在 OHOS aarch64 profile 下解析完整依赖图，并检查所需模块的配置文件确实存在。用 Conan `--build=missing` 补建由新依赖图产生的工具包二进制，再执行应用构建和消费者测试。

### 回退方案

如果任何兼容的已发布 provider 都不包含该模块，才检查上游是否提供关闭开关，以及该功能是否确实可选。只有确认不会移除产品必需功能后，才裁剪构建组件并以测试覆盖降级路径。关联草稿 DRAFT-kuickshow-011 讨论了这种“无可用 provider 时”的功能裁剪方案。

### 禁止做法

- ❌ 未检查所有已发布 provider 就删除上游对必需 Qt 模块的依赖。
- ❌ 为单个应用私自改造共享 qtbase，造成 Qt 依赖闭包和包 ID 大范围变化。
- ❌ 在切换 provider 后忽略 Conan 报告的工具包二进制缺失。

## 验证

```bash
conan graph info archives/x/xaos/4.3.4 \
  --profile:host=ci/conan/profiles/ohos-aarch64
```

确认图中只有目标 `qtbase` 版本，并检查该包的 `lib/cmake/Qt6PrintSupport/Qt6PrintSupportConfig.cmake`。使用 `conan create ... --build=missing` 后，HarmonyOS aarch64 真机上的 XaoS 构建、Conan G2、W3 和 `test_package` Mandelbrot 渲染均通过。Qt 工具和安装后应用 ELF 的签名问题另记于 E479。

## 关联条目

- 相关：`DRAFT-kuickshow-011-qt-module-absence-trim-and-stub`；该条目覆盖没有已发布 provider 时的可选功能裁剪。
