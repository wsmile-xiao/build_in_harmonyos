# E104: verify_build.py 检查 build_system 字段不一致

## 问题描述

`verify_build.py` 在 G4 档案完整性检查中，查找版本级 `manifest.yaml` 的顶级字段 `build_system:`，但根据 ARCHIVE-SPEC v2.0 规范：

- **软件级** `manifest.yaml` 使用 `build_system`（顶级字段）
- **版本级** `manifest.yaml` 使用 `build.system`（嵌套结构）

这导致 verify-build G4 检查失败，报错 "manifest 缺少 build_system"。

## 受影响场景

所有首次编译的软件，特别是：
- 纯库项目（无可执行文件）
- 使用 CMake 构建的软件
- init-build 自动生成的版本级 manifest.yaml

## 根因分析

1. ARCHIVE-SPEC v2.0 规范定义了两个级别的 manifest.yaml
2. verify_build.py 的 `gate4_archive()` 方法只检查版本级 manifest.yaml
3. 检查逻辑硬编码查找顶级 `build_system:` 字段，不检查嵌套的 `build.system`

## 推荐解决方案

### 方案 A：添加兼容字段（临时方案）

在版本级 manifest.yaml 中添加顶级 `build_system:` 字段：

```yaml
version: "11.0.2"
status: published
build_system: cmake  # 添加兼容字段

build:
  system: cmake  # 规范字段
  configure_options:
    - "-DCMAKE_BUILD_TYPE=Release"
```

**优点**：快速解决，不影响现有流程
**缺点**：冗余字段，不符合规范

### 方案 B：修复 verify_build.py（长期方案）

修改 `verify_build.py` 的检查逻辑：

```python
# 方式 1：检查软件级 manifest
software_mf = self.archive_dir.parent / "manifest.yaml"
if software_mf.exists():
    content = software_mf.read_text()
    if "build_system:" in content:
        g.passed += 1
    else:
        g.failed += 1

# 方式 2：检查版本级 build.system
if "build:" in content and "system:" in content:
    g.passed += 1
else:
    g.failed += 1
```

**优点**：符合规范，一劳永逸
**缺点**：需要修改脚本，需要测试验证

## 验证方法

```bash
# 检查 manifest.yaml 字段
grep -n "build_system:" archives/f/fmt/11.0.2/manifest.yaml
grep -n "build:" archives/f/fmt/11.0.2/manifest.yaml

# 重新运行 verify-build
python3 scripts/ohc-run.py verify-build fmt 11.0.2
```

## 关联知识

- ARCHIVE-SPEC v2.0：软件级 vs 版本级 manifest.yaml 结构
- R15：历史信息纠正（manifest 字段不一致需要纠正）
- verify_build.py gate4_archive() 方法实现

## 建议

1. **短期**：所有新编译的软件添加兼容字段 `build_system:`
2. **长期**：修改 verify_build.py，检查 `build.system` 或软件级 `build_system`
3. **规范**：统一 ARCHIVE-SPEC 和 verify_build.py 的字段定义

---
**草稿状态**: 待审核
**创建时间**: 2026-05-20
**贡献者**: 5FC0