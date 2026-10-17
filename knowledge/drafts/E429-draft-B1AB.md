# E429（草稿）：OHOS 制品生态无 .typelib，GIRepository 运行时依赖的上游测试必须逐项申报

## 症状与稳定错误签名

```
not ok /Tmpl/Expr/test1 - ERROR:../tests/test-expr.c:53:test1: assertion failed
(error == NULL): Typelib file for namespace 'GLib' (any version) not found
(g-irepository-error-quark, 0)
```

正则：`Typelib file for namespace .* not found|g-irepository-error-quark`

## 根因

- 制品仓 `glib2/2.88.0` 以 `introspection=disabled` 构建，不生成 GLib/GObject/Gio 的 `.typelib`；
- `gobject-introspection` 包本身与 OHOS `/system` 系统镜像中同样没有任何 `.typelib` 文件
  （`find /system /data/service/hnp -name '*.typelib'` 返回空；conan 依赖包目录 find 为空）；
- 任何运行时调用 `gi_repository_require()` 加载命名空间的程序（template-glib 的
  test-expr 表达式求值、pygobject 类绑定等）在 OHOS 上必然失败。

## 最小复现

template-glib 3.36.2 的 `meson test test-expr`（构建成功、运行期 abort）。

## 已尝试方案

| 方案 | 结果 |
|---|---|
| GI_TYPELIB_PATH 指向 glib2/GI 包 | 无效——两包均无 .typelib |
| 指向 OHOS 系统目录 | 无效——/system 无 .typelib |
| 自建 g-ir-scanner 生成 | 未采用——需 python 工具链 + 对 glib 全量 introspection 构建，CI 稳定性差 |

## 最终方案

上游测试**真实执行**（不得跳过整个套件），用例级采集失败证据
（`meson-logs/testlog.txt`），对命中本模式的用例**逐项申报 test_skipped**
（技术原因=平台无 typelib 数据）。执行数/通过数/跳过数如实分开申报。
template-glib 3.36.2 实测：test-template 通过、test-expr 按本条申报。

## 适用范围与反例

- 适用：所有运行时依赖 GIRepository 的包的上游测试（GNOME 系常见）。
- 反例：仅构建期使用 g-ir-scanner 的包（`-Dintrospection=disabled` 即可绕开，
  不影响运行期）。
- 解除条件：制品仓发布带 introspection 数据的 glib2 变体，或 CI 提供 typelib。

## 查重

knowledge/graph/index.tsv 全量 grep `typelib|g-ir-scanner|GIRepository|girepository`
无命中（2026-09-15，GLM-29）。

## 关联

- 触发实例：template-glib 3.36.2（PR 待回填）
