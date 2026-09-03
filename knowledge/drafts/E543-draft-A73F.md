# E543 — Conan CMakeDeps 导出目标名必须以实际生成结果为准

## 错误特征
设备端 CMake 配置时报 `Target "test_minilua" links to: minilua::minilua, but the target was not found`；同时 Conan 输出 `Conan: Target declared 'minilua'`。

## 触发条件
- 构建系统: CMake + Conan CMakeDeps
- 阶段: CMake configure/generate

## 根因分析
test_package 按命名空间形式链接 `minilua::minilua`，但配方设置的 `cmake_target_name` 和设备端 Conan 2.29.1 的 CMakeDeps 实际生成未命名空间目标 `minilua`。这是消费者与生成配置之间的目标名契约不一致，不是上游 minilua API 或链接库缺失。

## 解决方案

### 推荐方案
从设备端 CMakeDeps 输出和生成的 targets 文件确认真实目标名，再将 `target_link_libraries` 改为该目标；保留真实包 API 调用，重新执行 Conan create 和 test_package。

### 禁止做法
- ❌ 未查看生成配置就假设所有 Conan 包都导出 `name::name`。
- ❌ 删除 `target_link_libraries` 或把测试改成只打印字符串。

## 验证
```bash
conan create archives/m/minilua/5.4.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 关联条目
- 相关: E307、E309、E321
