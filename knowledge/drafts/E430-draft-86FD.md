# E430（草稿）：消费 gobject-introspection 必须对齐 glib2/2.88.0，混用 glib/2.84.x 触发 zlib 版本冲突

## 症状与稳定错误签名

```
ERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph.
Conflict originates from glib2/2.88.0
```

正则：`Version conflict: Conflict between zlib|Conflict originates from glib2`

## 根因

制品仓同时存在两个 glib 包名：`glib/2.84.0.1`（链 `zlib/1.3.1.1`）与
`glib2/2.88.0`（链 `zlib/1.3.1`）。`gobject-introspection/1.78.1` 自身
requires `glib2/2.88.0`。配方若再 requires `glib/2.84.0.1`，同一依赖图出现
两个 zlib 版本，Conan 直接拒绝构图。

## 最小复现

template-glib 3.36.2 配方初版：
`self.requires("glib/2.84.0.1") + self.requires("gobject-introspection/1.78.1")`
→ `conan create` 报 Version conflict。

## 已尝试方案与结果

| 方案 | 结果 |
|---|---|
| 保持 glib/2.84.0.1 | Version conflict，构图失败 |
| 改用 gobject-introspection/1.78.1.1 | 制品仓无 OHOS 二进制 → --build=missing 触发 python/3.12.9 源码构建 → 设备 HMDFS `working directory cannot be determined` 失败 |
| **对齐 glib2/2.88.0（采纳）** | pygobject/3.58.0 同款组合，构图与构建全绿 |

## 最终方案

```python
self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
self.requires("gobject-introspection/1.78.1", transitive_headers=True, transitive_libs=True)
```

静态交付的消费者必须拿到 glib/GI 的头与库，两个 transitive 开关都要带。

## 适用范围与反例

- 适用：所有需要 gobject-introspection（或任何依赖 glib2 的包）的配方。
- 反例：确需 glib/2.84.x 主版本时，用 `force=True` 强制单一 zlib 版本
  （pygobject 处理非 PIC zlib 的先例），仅限别无他法时。
- 注意：`gobject-introspection/1.78.1.1` 无 OHOS 二进制，会级联触发
  python 源码构建（设备 HMDFS 必挂 getcwd，CI 则浪费大量时间）。

## 查重

knowledge/graph/index.tsv 全量 grep `zlib.*conflict|版本冲突|glib2.*glib/`
无命中（2026-09-15，GLM-29）。

## 关联

- 触发实例：template-glib 3.36.2（PR 待回填）
