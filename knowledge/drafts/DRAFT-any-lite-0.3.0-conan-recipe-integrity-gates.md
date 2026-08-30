# DRAFT-any-lite-0.3.0-conan-recipe-integrity-gates：Conan 2 配方完整性三要素（export_sources/补丁应用链/MANIFEST.yml）

> Contributor: any-lite 0.3.0 R03 Path B 草稿（pc3-31） | Status: Draft | Updated: 2026-08-29
> Source: archives/a/any-lite/0.3.0（R02 本地适配闭环）

## 现象

any-lite 0.3.0（header-only，上游自带 Conan 1.x 配方）迁移到 Conan 2.x 后，
`conan-verify` 在 **G1 配方完整性门禁** 失败：

```text
❌ G1 失败，请先生成完整配方: ohc-run.py conan-init <软件> <版本>
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ❌ conanfile.py 缺少: export_sources() 方法
  ❌ conanfile.py 缺少: 补丁应用调用
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ❌ test_package/MANIFEST.yml 缺失 (CI L0e 门禁要求)
```

## 根因

Conan 1.x 配方（`from conans import ConanFile, CMake`）迁移到 Conan 2.x 时，
若按"最小骨架"手写 `conanfile.py`（仅 source/build/package/package_info + `get()`），
会漏掉 Conan 2 官方配方的三类完整性要素：

1. **`export_sources()` 方法**（通常为 `export_conandata_patches(self)`）：用于导出
   conandata.yml `patches:` 段引用的补丁文件；缺失则补丁链无法随配方导出。
2. **补丁应用调用**（`apply_conandata_patches(self)`）：在 `source()`/`build()` 中
   实际应用补丁；缺失则补丁永不生效。
3. **`test_package/MANIFEST.yml`**：CI L0e 门禁要求的上游测试声明文件；缺失则
   无法追溯测试入口与断言数。

G1 是 G2（conan create 干净构建）、G3/G4/L2/L4/L5 的**前置门禁**，配方被判定
"不完整"时整条验证链在最前面短路，后续 G2-G5 即使配方实际可构建也不会执行。

## 最小修复

```python
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class AnyLiteConan(ConanFile):
    ...
    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)   # conandata.patches 为空时安全 no-op
```

并新增 `test_package/MANIFEST.yml`（package/homepage/upstream_check_command/
upstream_test_in_build/upstream_tests/test_package_tests/assertion_count）。

## 验证证据（any-lite 0.3.0，R02 实测）

| 门禁 | 修复前 | 修复后 |
|---|---|---|
| G1 配方完整性 | FAIL（缺三要素） | PASS |
| G2 conan create（干净构建） | 未执行（G1 短路） | PASS（上游 CTest 4/4：cpp98/11/14/17；test_package `PASS`） |
| G3 系统同名库隔离 (R26) | — | PASS（header-only，无需静态配置） |
| G4 产物完整性 | — | PASS |
| L2/L4/L5 | — | PASS |
| 结论 | — | 可标记 status: published |

## 适用边界

- 所有 **Conan 2.x** 配方（`conan create` / `conan-verify` 门禁链），尤其：
  - 从 Conan 1.x 迁移的配方（上游自带旧版 `from conans import` 配方）；
  - 手写最小骨架、未走 `ohc-run.py conan-init` 的配方；
  - header-only 库与编译库均适用（三要素与构建类型无关）。
- 不适用于非 Conan 配方场景。

## 恢复条件

补齐以上三要素后重跑 `python3 ohc-run.py conan-verify <软件> <版本>` 即恢复；
无外部依赖、无需远端操作、不改变已验证的构建/测试结果。

## 跨库复用判断

**高**。任意新库 R01/R02 阶段若手写配方骨架，都可能踩中同一 G1 失败；本草稿的
"配方完整性三要素"可作为新库配方自检模板跨库复用。复用前需按各自库的 CMake 选项
与测试入口更新 MANIFEST.yml。

## 查重差异

查重范围：`knowledge/graph/index.tsv` + `knowledge/doc/` + `knowledge/drafts/`
中全部 conan/recipe/test_package 相关条目（E239/E241/E253/E281/E282/E308、
DRAFT-conan-copy-keep-path-nesting、E2153、E321 等）。最近邻条目均不同主题：

- E308（test_package 模板后缀不被 CI L0c 识别）：L0c 测试源后缀门禁，非 G1 三要素。
- E282（多源码补丁必须声明独立 base_path）：补丁应用路径语义，非配方完整性。
- E239（多 case 消费者测试诊断保留）：test_package 输出聚合，非 G1。
- DRAFT-conan-copy-keep-path-nesting：copy() 路径嵌套，非完整性门禁。

无既有条目覆盖"G1 完整性三要素（export_sources/补丁应用链/MANIFEST.yml）"，
本草稿为新增价值。