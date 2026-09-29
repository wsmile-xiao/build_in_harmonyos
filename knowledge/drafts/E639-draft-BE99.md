# E639 — conan 组图 zlib 版本冲突（boost 1.3.1 vs glib 1.3.1.1）

## 错误特征

`conan create` / `conan install` 在 **Computing dependency graph** 阶段即失败：

```
ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph.
Conflict originates from glib/2.84.0.1
```

## 触发条件

- 工具: conan 2.x（OHOS 适配版 2.29.1）
- 阶段: graph resolution（configure 之前，编译尚未开始）
- 场景: 同一个消费者的依赖图里**同时**出现
  - 一条经 `boost/1.84.0` 的路（`boost` 固定 `requires("zlib/1.3.1")`）
  - 一条经 `glib/2.84.0.1` 的路（glib 固定 `requires("zlib/1.3.1.1")`，常见于
    `gdk-pixbuf`、GTK 系）

  本文实例：`libopenraw-pixbuf-loader` 同时 requires
  `libopenraw/0.1.2`（→ boost → zlib/1.3.1）与 `gdk-pixbuf/2.44.6`
  （→ glib → zlib/1.3.1.1）。

## 根因分析

conan 中 `requires("zlib/1.3.1")` 的精确版本是一个**等式约束**，不是范围。
两个传递依赖各自钉死了不同的 zlib 精确版本时，组图无解，直接 `Version conflict`。
这跟 maven/npm 的“就近胜出”不同——conan 不会自动挑一个。

## 解决方案

### 推荐方案

在消费者配方的 `requirements()` 里显式声明并 `override=True`，把整图统一到一个版本：

```python
def requirements(self):
    self.requires("libopenraw/0.1.2", transitive_headers=True, transitive_libs=True)
    self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
    # 统一 zlib：boost/1.84.0 钉 1.3.1，glib/2.84.0.1 钉 1.3.1.1
    self.requires("zlib/1.3.1.1", override=True)
```

**override 的方向很重要**：override 到较新的那个版本（本例 1.3.1.1）只会让
*较旧一侧*（libopenraw）的 package-id 变化；反向 override 到 1.3.1 会牵动
glib/gdk-pixbuf/libpng/libtiff 整条链的 package-id，把这些已发布二进制全部变成
“需从源码重建”，构建时间与失败面都更大。选择依据：`conan install` 打印的
Graph 里看哪一侧的传递依赖更多。

### 禁止做法

- ❌ 为绕过冲突把 `requires` 去版本号或用 `[*]`
- ❌ 反向 override 前不核对依赖链（会触发整链重建）
- ❌ 用 `--build=missing` 掩盖冲突（冲突发生在组图阶段，`--build` 不生效）

## 验证

```bash
# 复现冲突
conan install --requires=libopenraw/0.1.2 --requires=gdk-pixbuf/2.44.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1

# 加 override 后通过（Graph 中出现 zlib/1.3.1: ['zlib/1.3.1.1']）
```

## 实测证据（2026-09-25, HarmonyOS aarch64 / clang 15.0.4）

- 复现：`conan install`（无 override）→ `Version conflict ... originates from glib/2.84.0.1`
- 修复：配方加 `self.requires("zlib/1.3.1.1", override=True)` → 组图通过、
  `conan create` 成功、`test_package` 14/14 通过。

## 关联条目

- 相关: 无（同族可用 `graph engine "Version conflict"` 检索）
