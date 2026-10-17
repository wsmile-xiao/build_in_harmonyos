# E999 — glib 2.88 组件化 conan 配方 PkgConfigDeps/CMakeDeps 消费三坑

> 草稿（draft）· contributor_id: BF96 · source_event: libcloudproviders 0.4.0 HarmonyOS PC 适配（meson + glib/2.88.3.1）

## 错误特征

构建依赖 conan `glib/2.88.x` 的 meson/CMake 库时，出现以下任一症状：

```
ld.lld: error: unable to find library -lintl
ld.lld: error: unable to find library -lintl          # 链接期（meson + PkgConfigDeps）

Error in generator 'CMakeDeps': error generating context for '...':
Component 'glib::glib-2.0' not found in 'glib' package requirement   # CMakeDeps 生成期

Run-time dependency gio-unix-2.0 found: NO
  No package 'gio-unix-2.0' found                                    # meson configure 期
```

## 触发条件

- 构建系统: meson（PkgConfigDeps）或 CMake（CMakeDeps）
- 依赖: conan `glib/2.88.0+`（组件化配方：`components["glib"]`/`["gio"]`，pkg_config_name 才是 `glib-2.0`/`gio-2.0`）
- 阶段: configuration（component/dependency 解析）或 linking（-lintl）

## 根因分析

glib≥2.88 的 conan 配方（`archives/g/glib/2.88.x`）从旧的 flat cpp_info 改为**多组件声明**：
组件 key 是 `glib`/`gobject`/`gio`（**无 `-2.0` 后缀**），`pkg_config_name` 才是
`glib-2.0`/`goobject-2.0`/`gio-2.0`。相较 2.84 及更早（flat cpp_info 或组件名≡pc 名），
消费方踩三个独立坑：

1. **组件名引用错误**：`package_info().cpp_info.requires` 必须写组件名
   `glib::glib`、`glib::gio`（无 `-2.0` 后缀）；写成 `glib::glib-2.0` 时
   CMakeDeps 生成阶段报 `Component 'glib::glib-2.0' not found`。
   test_package 侧 `find_package` 用 glib 配方的 `cmake_file_name`（`glib2`），
   不是组件名。

2. **内联 `-lintl` 缺 `-L`（proxy-libintl 传递依赖不可见）**：glib 组件
   `requires` 内联了 `proxy-libintl::proxy-libintl`，PkgConfigDeps 生成
   `glib-2.0.pc`/`gio-2.0.pc` 时把 proxy-libintl 的库直接拼成裸 `-lintl`。
   但 proxy-libintl 是 **glib 的传递依赖**，在消费方 `self.dependencies.host`
   中**不可见**，PkgConfigDeps 不会为它生成 `.pc`、也不会附加 `-L` 路径 →
   链接期 `unable to find library -lintl`（OHOS 无系统 libintl，无法侥幸命中）。
   实测 `visible=False` 更糟：依赖被彻底移出可见列表，附加 `-L` 全部失效。

3. **gio-unix-2.0.pc 组件未声明**：glib 包内 `lib/pkgconfig/` 实际含
   `gio-unix-2.0.pc`，但配方 components 中没有 `gio-unix-2.0`，
   PkgConfigDeps 不生成它 → meson `dependency('gio-unix-2.0')` 失败。

## 解决方案

### 推荐方案

**① cpp_info.requires 使用组件名（无 -2.0 后缀）**

```python
def package_info(self):
    self.cpp_info.libs = ["cloudproviders"]
    self.cpp_info.requires = [
        "glib::glib",
        "glib::gio",
        "proxy-libintl::proxy-libintl",
    ]
```

**② 显式声明 proxy-libintl 直接依赖 + pkg::pkg 引用**

```python
def requirements(self):
    self.requires("glib/2.88.3.1", transitive_headers=True, transitive_libs=True)
    # glib pkg-config 内联 -lintl（proxy-libintl），链接必须能解析；
    # 传递依赖在 dependencies.host 不可见 → 显式声明为直接依赖
    self.requires("proxy-libintl/0.5", options={"shared": False})
```

注意 proxy-libintl 配方**没有 components**（`self.cpp_info.libs = ["intl"]`），
`cpp_info.requires` 引用必须用 `pkg::pkg` 形式（`proxy-libintl::proxy-libintl`），
裸写 `proxy-libintl` 会被当成"本包内部组件未定义"报错。

**③ gio-unix-2.0.pc 从 glib 包复制并重写 prefix**

```python
# generate() 内（E348 复制改名式别名同款）
target = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
# 从 glib package_folder 的 lib/pkgconfig/gio-unix-2.0.pc 复制，
# 把 "prefix=/" 重写为 glib package_folder（实际包路径）
```

只把 glib 的 `lib/pkgconfig` 加入 `pkg_config_path` **不够**：包内 .pc 的
`prefix=/` 是构建期 --prefix=/ 安装的 broken 值，必须复制副本并重写 prefix。

### 禁止做法

- ❌ `cpp_info.requires` 写 `glib::glib-2.0`（组件名带后缀）→ CMakeDeps 直接 Component not found
- ❌ `find_package(glib)` → cmake_file_name 是 `glib2`，应 `find_package(glib2)`
- ❌ `requires("proxy-libintl/0.5", visible=False)` → 依赖移出可见列表后 -L 丢失，链接必失败
- ❌ `cpp_info.requires` 裸写 `"proxy-libintl"` → 无组件包必须 `pkg::pkg` 形式

## 验证

```bash
cd archives/l/libcloudproviders/0.4.0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
# 期望: Package '...' built，test_package 编译链接通过，无 unable to find -lintl
# 实测（libcloudproviders 0.4.0, 2026-09-18）:
#   conan-verify G1-G4 + L2/L4/L5 全 PASS；12 断言测试全过
```

## 关联条目

- 相关: [E348]（glib2 单 pkg_config_name 转发 .pc 补丁，未覆盖组件命名与 -lintl）
- 相关: [E216]（glib 2.84 flat cpp_info 的 CMakeDeps include 传播坑）
- 相关: [E508]（glib g_libintl_* 符号缺失的 intl-wrapper，符号层 vs 本文链接层）