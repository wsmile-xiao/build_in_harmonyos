# E429 — KF5 依赖链 Qt5 基线分裂触发 Version conflict，且 cmake_find_mode=none 依赖的 config 目录必须手动注入

## 错误特征

配方 `conan create` 在图求解或 CMake 配置阶段中断，典型日志：

```
ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2 and qt5-qtbase/5.15.2.2 in the graph.
Conflict originates from kcoreaddons5/5.116.0
```

修好版本冲突后，接着在 CMake 配置阶段报缺包配置：

```
  By not providing "FindKF5CoreAddons.cmake" in CMAKE_MODULE_PATH this
  project has asked CMake to find a package configuration file provided by
  "KF5CoreAddons", but CMake did not find one.

  Could not find a package configuration file provided by "KF5CoreAddons"
  (requested version 5.116.0) with any of the following names:

    KF5CoreAddonsConfig.cmake
    kf5coreaddons-config.cmake
```

test_package 阶段还会以 `find_dependency` 的调用栈形式复现同一错误：

```
Call Stack (most recent call first):
  <pkg>/lib/cmake/KF5JobWidgets/KF5JobWidgetsConfig.cmake:31 (find_dependency)
  CMakeLists.txt:13 (find_package)
```

## 触发条件

- 构建系统: cmake（KDE ECM / KF5 骨架）
- 阶段: 图求解（graph）与 configure
- 前置条件: 配方同时依赖
  1. 至少一个**精确 pin 了无 Widgets 桩 Qt5 的 KF5 包**（制品仓实测：`kcoreaddons5/5.116.0`、`kglobalaccel5/5.116.0`、`attica-kf5/5.116.0` 均 `requires("qt5-qtbase/5.15.2")`），以及
  2. 自身或另一依赖需要的 **Widgets/DBus 能力 Qt5 变体** `qt5-qtbase/5.15.2.2`（该变体 configure 带 `-dbus`，且组件声明含 `Qt5Widgets`/`Qt5DBus`/`Qt5Test`/`Qt5Xml`；而 `5.15.2` 用 `-no-widgets -no-dbus -no-feature-xml` 构建，连 `lib/cmake/Qt5Widgets` 都不存在）。

## 根因分析

两个相互独立、但常在 KF5 链上叠加的机制：

### 1. 制品仓 KF5 基线分裂 → Conan 图无法消解

同一条 KF5 5.116.0 链的包不是在同一次批量任务里适配的，各自 pin 的 Qt5 变体不同：

| 包 | 制品仓 5.116.0 | pin 的 Qt5 |
|----|---------------|-----------|
| `kcoreaddons5` / `kglobalaccel5` / `attica-kf5` | 已发布 | `qt5-qtbase/5.15.2`（无 Widgets 桩） |
| `kwidgetsaddons5` / `kitemviews5` / `kitemmodels5` | 已发布 | `qt5-qtbase/5.15.2.2` |

Conan 2 不允许同一包名出现两个版本的精确 requirement，且**默认不会**用"更高版本自动胜出"来消解 version range 语义的精确 pin，于是报
`Version conflict ... Conflict originates from kcoreaddons5/5.116.0`。

### 2. `cmake_find_mode=none` 的依赖不进 CMAKE_PREFIX_PATH

KF5 包（以及本仓 `qt5-qtbase`）在 `package_info()` 里写了：

```python
self.cpp_info.set_property("cmake_find_mode", "none")
self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
```

用意是让消费者使用**包内自带**的 `KF5*Config.cmake`（带正确的 `find_dependency` 追踪）。但副作用是 CMakeDeps 不再为它生成 config，也不把它的 `lib/cmake` 写进 `CMAKE_PREFIX_PATH`，因此下游 `find_package(KF5CoreAddons 5.116.0)` 与已安装 config 内部的 `find_dependency(KF5CoreAddons)` 都会找不到配置文件——**报错点在依赖方，根因在依赖包的 find-mode 声明**，容易误判。

## 解决方案

### 推荐方案

**① 用 `force=True` 统一 Qt5 基线**（不是 `override=True`）：

```python
def requirements(self):
    self.requires("kcoreaddons5/5.116.0")
    self.requires("kwidgetsaddons5/5.116.0")
    self.requires("qt5-qtbase/5.15.2.2", force=True)
```

- `force=True` 消解版本冲突，同时**保留消费语义**，`generate()` 中 `self.dependencies["qt5-qtbase"].package_folder` 仍可取到路径；
- `override=True` 会把它降级为非消费型依赖，`package_folder` 返回 `None`，后续拼 Qt5 路径直接失败（本仓 karchive5 处理 `zlib/1.3.1` vs `zlib/1.3.1.1` 已有同款结论）。

**② 遍历依赖注入 config 目录**（generate() 与 test_package 都要做）：

```python
for dep in self.dependencies.values():
    if not dep or not dep.package_folder:
        continue
    lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(dep.package_folder))
    lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(dep.package_folder))
    lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(dep.package_folder))
```

写入 `conan_cmakedeps_paths.cmake`（用 `"w"` 覆写而非 `"a"` 追加，避免多次 generate 叠加旧内容）。这一步同时覆盖了 KF5 config 内部 `find_dependency()` 的传递链。

> 参考实现：`archives/k/kjobwidgets5/5.116.0/conanfile.py`（主配方）+
> `archives/k/kjobwidgets5/5.116.0/test_package/conanfile.py`（消费者侧）；
> `archives/k/karchive5/5.116.0/conanfile.py`（force=True 先例）；
> `archives/k/ktextwidgets/6.14.0/conanfile.py`（遍历依赖注入先例）。

### 回退方案

若上游允许整条链改用单一的 Widgets 基线，可让所有 KF5 包统一到
`qt5-qtbase/5.15.2.2` 并从源码重建（无需 force=True）。代价是失去制品仓
KF5 二进制的复用，构建时间显著上升；在本仓"单 PR 单包"约束下不现实。

### 禁止做法

- ❌ `self.requires("qt5-qtbase/5.15.2.2", override=True)` —— `package_folder` 变 `None`，`generate()` 拼路径失败。
- ❌ 消费 `cmake_find_mode=none` 的依赖却不注入其 `lib/cmake` —— `find_package`/`find_dependency` 必然失败，且报错位置在依赖方、易误判为依赖包损坏。
- ❌ 为了让版本冲突消失而**降级**到 `qt5-qtbase/5.15.2`（无 Widgets 桩）—— 上游 `find_package(Qt5 REQUIRED Widgets)` 仍会失败，属于把配置错误推迟到下一阶段。
- ❌ 用 `override=True` + 手写 `self.dependencies.get("qt5-qtbase") or ...` 之类兜底掩盖语义错误。

## 验证

```bash
# 图求解：不应再有 Version conflict
conan create archives/k/kjobwidgets5/5.116.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# 确认依赖的 config 已可被发现（应打印 Qt5/KF5 的 config 路径而非报错）
grep -n "conan_cmakedeps_paths" \
  archives/k/kjobwidgets5/5.116.0/test_package/build/*/generators/conan_toolchain.cmake

# 图层面确认 override 生效处
# 期望输出 Overrides 段包含：qt5-qtbase/5.15.2: ['qt5-qtbase/5.15.2.2']
```

实测结果（kjobwidgets5/5.116.0）：`conan create` **EXIT=0**，
`Overrides` 段输出 `qt5-qtbase/5.15.2: ['qt5-qtbase/5.15.2.2']`，
test_package 完成链接级 R34 校验
（`kjobwidgets5 consumer links libKF5JobWidgets.so (9 KF5JobWidgets API symbols resolved)`）。

## 关联条目

- 相关: E537（OHOS CMake 无 soname 平台标志，同一 KF5 链）
- 相关: E541 / E533（同一 `force=True` 消解版本冲突的手法来源，zlib 场景）
- 相关: E540（沙箱 PATH/执行限制，同链 test() 兜底校验背景）
