# E216 — CI L0p 门禁要求 conanfile settings 声明全部四项

## 错误特征
```
[fail] L0p: settings 缺少 'compiler' — OHOS profile 需要全部四项
[fail] L0p: settings 缺少 'build_type' — OHOS profile 需要全部四项
[fail] aladin/12.06 — L0 quality gate failed: missing_setting_compiler missing_setting_build_type
```
本地 conan-verify 通过，但 CI 本地模拟（W3 build_and_test.sh）L0p 门禁失败。

## 触发条件
- 构建系统: custom (JVM/Java 应用等无需编译器的场景)
- 阶段: CI L0 质量门禁 (L0p)
- 场景: conanfile.py 的 settings 仅声明 "os","arch"（JVM 应用惯例），
  未包含 compiler/build_type

## 根因分析
本仓库 CI 的 L0p 门禁要求 conanfile.py settings 声明全部四项
（os/compiler/build_type/arch），即使 JVM 应用实际不参与 C/C++ 编译。
只声明 os/arch 会被门禁以 missing_setting_compiler/missing_setting_build_type 拒绝，
导致 finish 的 W3 本地 CI 模拟阻塞（不可提 PR）。

## 解决方案

### 推荐方案
- conanfile.py 的 settings 声明全部四项：
  `settings = "os", "compiler", "build_type", "arch"`
- JVM 应用不受影响：conan create 时仍不实际使用编译器设置，只是满足门禁格式
- 参照已发布归档 gradle 8.12 的先例（同样声明四项）

### 禁止做法
- ❌ 只为绕过门禁而声明 settings 但 build() 中裸用未定义 shell 环境变量（R33）
- ❌ 删除或注释 build_and_test.sh 的 L0p 检查

## 验证
```bash
# 本地 CI 模拟应通过 L0p 门禁
bash ci/conan/build_and_test.sh aladin 12.06
# 或在 finish 的 W3 步骤看到 [ok] L0p 通过
```

## 关联条目
- 相关: R33, L0p (CI 门禁)
