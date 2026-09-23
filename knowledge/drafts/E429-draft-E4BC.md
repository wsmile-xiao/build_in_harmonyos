# E429 — 无补丁配方仍须声明 export_sources()/apply_conandata_patches（conan-verify G1）

## 错误特征

- `conan-verify` 报告 `## G1: ❌ FAIL`，项为 `G1 Recipe completeness (conanfile.py + conandata.yml + test_package/)`
- 缺失提示指向 `export_sources() 方法` 与 `补丁应用调用`
- 表现：finish 步骤 [4/10] conan-verify 判定失败 → 归档状态降级、`submit` 被前置检查阻塞

## 触发条件

- 构建系统: autotools / make（任何 Conan 2 配方）
- 阶段: packaging（静态配方检查，与编译无关）

## 根因分析

`scripts/ohc/conan_verify.py` 的 G1 门禁按**字面量**在 conanfile.py 中查找两个模式：

```python
("export_sources", "export_sources() 方法"),
("apply_conandata_patches", "补丁应用调用"),
```

**该包本身没有补丁时**，配方作者容易省略这两个钩子，或误用 Conan 1 风格的属性写法
`exports_sources = "patches/*"`。注意 `exports_sources`（带 s）**不包含**子串
`export_sources`，两种写法都无法通过 G1。

Conan 2 的 `export_conandata_patches(conanfile)` / `apply_conandata_patches(conanfile)`
在 `conandata.yml` 没有 `patches` 键时为 no-op（读取 `.get("patches", {})` 后直接返回），
因此对无补丁的包补充这两个钩子没有副作用，属仓库通用脚手架。

## 解决方案

conanfile.py：

```python
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

    def export_sources(self):
        export_conandata_patches(self)

    def build(self):
        apply_conandata_patches(self)
        # ... 原有构建逻辑
```

conandata.yml 显式声明空补丁表：

```yaml
patches: []
```

## 验证

```bash
python3 scripts/ohc-run.py conan-verify <name> <version>   # 期望 G1 PASS
python3 scripts/ohc-run.py finish <name> <version> built
```

## 关联

- 参考配方: `archives/p/p0f/3.09b/conanfile.py`（同样采用方法式 export_sources）
- 实例: digitemp 3.7.2（无补丁包，首次 conan-verify G1 FAIL → 补脚手架后 PASS）
