# DRAFT-celero-2.10.0-conandata-patches-export-sources-hook：补丁导出钩子必须用 export_sources()

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: celero 2.10.0 HarmonyOS PC 适配（真机 shadow CI 第 4/5 轮 L1 失败）
> 对应：knowledge/drafts/DRAFT-celero-2.10.0-conandata-patches-export-sources-hook.kv

## 现象

配方按仓库主流模式给 conandata.yml 加 patches 后，`conan create` 在**最早的 export
阶段**即失败，连续两轮、两种报错：

```text
# 第 4 轮（def exports(self): 写法）
ERROR: conanfile 'exports' shouldn't be a method, use 'export()' instead

# 第 5 轮（改成 def export(self): 后）
celero/2.10.0: Calling export()
ERROR: celero/2.10.0: Error in export() method, line 37
	export_conandata_patches(self)
	TypeError: expected str, bytes or os.PathLike object, not NoneType
```

## 根因

补丁导出钩子的"自然演进链"两步全错：

1. `def exports(self):` —— Conan 2 中 `exports` **只能是类属性**（文件匹配器），
   定义为方法在配方加载时即被拒绝；
2. `def export(self):` —— 该钩子调用时 `conanfile.export_folder` **尚未绑定**（None），
   `export_conandata_patches` 内部 `os.path.join(export_folder, patch_file)` 直接
   TypeError。

正确钩子是 **`export_sources()`**：此时导出目录已就绪，补丁作为"导出源"复制进
配方缓存。仓库内 rocksdb7 等在库配方是现成先例。

## 方案

标准三件套：

```python
from conan.tools.files import apply_conandata_patches, export_conandata_patches

def export_sources(self):
    export_conandata_patches(self)

def source(self):
    get(self, **self.conan_data["sources"][self.version], strip_root=True)
    apply_conandata_patches(self)
```

改完先本地 `conan export <dir>` 验证（秒级、无工具链依赖），成功指纹是输出
`Copied N '.patch' file(s)`，再上真机/CI——避免烧一整轮 shadow CI 才发现钩子错。

## 验证（真实证据）

- 第 4 轮（commit 2d514f3e03，run 20260908T010737Z）："exports shouldn't be a
  method" L1 fail
- 第 5 轮（commit e4d0bc430c，run 20260908T013110Z）："Error in export() method
  ... TypeError ... NoneType" L1 fail
- 第 6 轮改 `export_sources()` 后导出与应用正常；第 7 轮
  （run 20260908T022643Z-2a0be6cd82-9099）G0/L0/L1/L4/L5 全 pass（L4 patches
  clean），上游 67/67、test_package 6 断言全 PASS

## 适用边界

- 触发面：Conan 2.x + conandata patches 生命周期（本仓库带补丁配方主流模式）；
  错误发生在 export 阶段，早于一切编译配置
- 相邻错误面：补丁未在 conandata 声明导致不导出/不应用见
  DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle（与其 similar_to 互补）；
  补丁应用冲突/多源 base_path 见 E254/E282
- Conan 1.x 用 `exports_sources` 类属性，语法不同，本条不适用

## 查重

knowledge/graph 与 knowledge/drafts 按 `export_conandata_patches` 检索命中
E254（toybox patch dry-run）、E282（多源码 base_path）、E321 及
DRAFT-libstatgrab（补丁未声明）；四者错误面均非"钩子用错"（exports 方法拒绝 /
export() NoneType），签名不重叠，本条为新增补充。
