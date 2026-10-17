# DRAFT: dbus-1.pc 别名（PkgConfigDeps cmake_file_name vs configure PKG_CHECK 名）

- **草稿 ID**: `DRAFT-ohos-dbus1-pc-alias`
- **触发软件**: telepathy-glib 0.24.2
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: DRAFT-ohos-glib-test-framework-cmake-inject（pcre2.pc 别名同类机制）、DRAFT-ohos-public-header-transitive-dep（dbus 头透传）

## 问题

```
configure: error: Package requirements (dbus-1 >= 0.95, dbus-glib-1 >= 0.90) were not met:
No package 'dbus-1' found
```

**根因**：dbus 包（dbus/1.14.10）的 conanfile.py `package_info()` 声明了
`set_property("cmake_file_name", "dbus")`——于是 **PkgConfigDeps 生成的 .pc 名为
`dbus.pc`**（按 cmake_file_name），而不是传统的 `dbus-1.pc`。但依赖方
（telepathy-glib 0.24.2）的 configure.ac 用 `PKG_CHECK_MODULES(DBUS, [dbus-1 ...])`
**直接** pkg-config 查 `dbus-1`——pkg-config 找不到 `dbus-1.pc` → 报错。

> 同类对比：dbustest 只 PKG_CHECK `dbus-glib-1`（dbus-glib-1.pc 存在），不触发；
> telepathy-glib 直接查 `dbus-1` 才暴露。

## 方案（conanfile.py generate() 生成别名）

```python
# conanfile.py generate()
def _gen_dbus1_alias(self):
    src = os.path.join(self.generators_folder, "dbus.pc")
    if not os.path.isfile(src):
        return
    dst = os.path.join(self.generators_folder, "dbus-1.pc")
    data = open(src, encoding="utf-8", errors="replace").read()
    data = data.replace("Name: dbus\n", "Name: dbus-1\n")
    open(dst, "w", encoding="utf-8").write(data)
```

并在 `build()` 的 PKG_CONFIG_PATH 前置 `self.generators_folder`（既有方案），
configure 的 pkg-config 即可解析 `dbus-1`。

> **注意**：若依赖方公开头文件链还需 dbus 头（如 telepathy-glib.h → dbus-glib.h
> → `dbus/dbus-shared.h`），应同时把 dbus 声明为**直接依赖**
> （`self.requires("dbus/1.14.10", transitive_headers=True, ...)`）并在
> `cpp_info.requires` 引用 `dbus::dbus`——见姊妹条目
> DRAFT-ohos-public-header-transitive-dep。

## 验证

telepathy-glib 0.24.2：生成 dbus-1.pc 别名后，configure 的
`PKG_CHECK_MODULES(DBUS, dbus-1)` 通过；conan-verify 全门禁 PASS
（G0-G5/L2/L4/L5），test_package 编译链接成功。

## 推广价值

适用于任何「依赖包 PkgConfigDeps 按 cmake_file_name 生成 .pc 名 ≠ configure
直接 PKG_CHECK 名」的库——dbus-1/dbus.pc 这类命名差异、或任意
`set_property("cmake_file_name", ...)` 与上游 .pc 名不一致的场景。

## 相关条目

- DRAFT-ohos-glib-test-framework-cmake-inject：pcre2.pc 别名（同类 .pc 名机制）
- DRAFT-ohos-public-header-transitive-dep：dbus 头透传（直接依赖声明）
- DRAFT-ohos-la-libdir-hardcode：依赖包 .la/.pc 路径改写
