# Conan 2 package_info() 强制要求列全"可见且非 override"的直接依赖

## 场景

libnm 1.52.1 配方（meson + Conan 2.29）首次 `conan create`，在 `package_info()` 阶段失败。

## 症状

```
ERROR: libnm/1.52.1: Error in package_info() method, line 214
	self.cpp_info.requires = [...]
	ConanException: The direct dependency 'libudev-zero' is not used by any '(cpp_info/components).requires'
```

报错**一次只点一个依赖名**，补齐后重跑会继续点下一个。

## 根因

Conan 2 的 `cpp_info.check_component_requires()`（`conan/internal/model/cpp_info.py:813-850`）做一致性校验：

> 一旦配方**显式**设置了 `cpp_info.requires`，那么 `requires()` 里声明的每一个直接依赖，
> 只要它是 **`visible=True` 且不是 `override=True`**，就必须出现在 `cpp_info.requires`
> （或某个组件的 requires）里，否则抛 `ConanException`。

这是刻意的：强迫配方作者声明"包装之后的真实传递依赖"，避免 `cpp_info.requires` 写成残集，
让消费端漏链接。

### 为什么容易踩

libnm 的上游 `libnm.pc` 只写 `Requires: gio-2.0`，但 `libnm.so` 内部用 `--no-undefined` 链进了
libudev / libuuid / gnutls。照抄 .pc 写一个窄集合就会炸：

```python
# 天真写法（炸）
self.cpp_info.requires = ["glib::gio-2.0"]
```

### 豁免项

| 形态 | 是否需列入 cpp_info.requires |
|---|---|
| `visible=True`, 非 override | **必须列入** |
| `visible=False`（纯配置期依赖，如 dbus / libndp / libpsl） | 豁免 |
| `override=True`（冲突仲裁，如 zlib 版本对齐） | 豁免 |

## 修复

补齐所有"可见且非 override"的直接依赖。组件名先核验依赖包是否真的定义了
`cpp_info.components`，没有则用 `pkgname::pkgname`：

```python
self.cpp_info.requires = [
    "glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0",
    "libudev-zero::libudev-zero", "uuid::uuid", "gnutls::gnutls",
]
```

核验命令：

```bash
conan cache path libudev-zero/1.0.4
grep -n "components" <pkgdir>/conanfile.py    # 无输出 = 无组件 = 用 pkg::pkg
```

## 验证

补齐后 `conan create` 顺利通过 `package_info()`，后续在 `build()` 阶段继续推进
（下一轮暴露出的是完全不同的运行时问题）。

## 关键词

`check_component_requires`, `cpp_info.requires`, direct dependency, not used by any,
components, `package_info`, visible, override, ConanException

## 相关条目

- **E221** —— 同属"Conan 依赖元数据声明不全导致消费端失败"家族
