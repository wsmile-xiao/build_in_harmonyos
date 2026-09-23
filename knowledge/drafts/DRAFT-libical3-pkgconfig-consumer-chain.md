# DRAFT: CMake 包消费 conan glib/libxml2 的 pkg-config 依赖链修正（pc-fix 三通道注入）

## 错误特征

CMake 构建的包（用 pkg_check_modules 找 glib-2.0/gobject-2.0/libxml-2.0）
在 conan 2 OHOS 环境下 configure 失败，错误形态：

```
-- Checking for modules 'glib-2.0>=2.32;gobject-2.0>=2.32'
--   No package 'glib-2.0' found
CMake Error: You requested to build libical-glib, but the necessary
development packages are missing...
```

修正 prefix 后进一步暴露：

```
Package 'proxy-libintl', required by 'glib-2.0', not found
Empty package name in Requires or Conflicts in file '.../gobject-2.0.pc'
Package 'libpcre2-8', required by 'glib-2.0', not found
Package 'libffi', required by 'gobject-2.0', not found
```

链接期（即便 configure 过了）：

```
ld.lld: error: unable to find library -lxml2
```

构建期工具（生成器类 target，构建后立即运行）：

```
Error loading shared library libgobject-2.0.so.0: (needed by ../../bin/ical-glib-src-generator)
Error relocating ...: g_strdup: symbol not found
```

## 根因

1. **conan glib/libxml2 共享库包的 .pc prefix=/**——构建期以 --prefix=/
   安装，.pc 里 libdir=/lib、includedir=/include 全部 broken。
2. **glib-2.0.pc 的 `Requires: proxy-libintl`**——proxy-libintl/0.5 包
   只装 libintl.a 没装 .pc，pkg-config 解析 Requires 时存在性校验失败
   → 整个 pkg_check_modules 失败（即使版本要求满足）。
3. **Requires.private 的传递依赖不可达**——pkg-config 对 private 行也做
   存在性校验（非 static 模式不展开但校验）；而 conan 2.29 的
   `self.dependencies.values()` 里传递依赖（pcre2/zlib/libffi）的
   `package_folder=None`（只对直接依赖填充），无法把它们的 pkgconfig
   目录加进 PKG_CONFIG_PATH。
4. **`--libs-only-l` 不含 -L**——上游老式 FindLibXML 只取
   `LIBXML_LIBRARIES`（-l 部分）传 target_link_libraries，链接器无
   搜索路径。
5. **构建期工具就地运行**——OHOS-on-OHOS（构建机=目标机）时生成器
   工具链接 shared 依赖，运行时靠 LD_LIBRARY_PATH 解析。

## 解法（pc-fix 三通道）

**通道 1：PKG_CONFIG_PATH（解析期）**——generate() 里复制直接依赖的
.pc 到 `generators/pc-fix/`：prefix 行改写为真实包目录；Requires 行按
逗号拆分剔除 proxy-libintl 词条；Requires.private 整行置空（非 static
模式只取 CFLAGS/LDFLAGS，private 不参与展开）。

**通道 2：LIBRARY_PATH（链接期）**——`--libs-only-l` 只有 -l 条目时，
环境变量 LIBRARY_PATH 补搜索路径（clang/lld 认可，等效 -L）。

**通道 3：LD_LIBRARY_PATH（构建期工具运行期）**——构建期立即执行的
工具（生成器）需要加载 shared 依赖。

三通道都必须在 `Environment().vars(self).apply()` 上下文里包裹
`cmake.configure()`/`cmake.build()`——CMake helper 直接拼 -D 参数调
cmake（不读 preset 的 environment 字段），配方自身 buildenv_info 也不
进 preset 生效路径。

presets 补充通道（可选）：`tc.presets_build_environment = env`（基于
`VirtualBuildEnv.environment()` 再 prepend）可把环境写进
CMakePresets.json，供用 `--preset` 的下游使用。

## 红线

- 不要用 conan list/search 判断 binary（R35）；直接依赖的 package_folder
  从 `self.dependencies` 拿
- Requires.private 置空仅对"非 --static 消费"安全；下游若要静态链接需
  另配完整 private 链
- 剥 proxy-libintl 后链接期需确认 conan 依赖图会把 libintl.a 带上
  （glib 的 cpp_info.libs 已含 intl）

## 验证

- PR #9870（libical3 3.0.20）：CI #46335 passed
- 本地 conan create：上游 CTest 48/48 + test_package 1/1 +
  C API/GLib 绑定双通道 PASS

## 关联

- E348（forwarding-pc，meson 场景 glib pc 问题）——机制不同：本条是
  prefix 修正+剥离+置空组合，CMake pkg_check_modules 场景
- E247（Libs.private 静态传播）——相关但方向相反：本条是置空 private
  避免存在性校验失败
- E019（LD_LIBRARY_PATH 运行期）——通道 3 的通用基础
