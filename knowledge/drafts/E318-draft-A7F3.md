# E318: GNOME 生态 glib 静态链接 g_libintl_* 符号缺失 + meson host_machine.system() 平台判断

> **结构化数据**: [drafts/E318-draft-A7F3.kv](../drafts/E318-draft-A7F3.kv)
> **严重度**: 🔴 blocking | **分类**: linking|platform_detection | **自动修复**: ❌ manual

---

## 错误特征

```
undefined symbol: g_libintl_* (gettext/textdomain/bindtextdomain)
meson: host_machine = 'harmonyos' 不匹配 'linux' 条件判断
clang: error: implicit declaration of function 'dgettext'
```

链接阶段找不到 `g_libintl_*` 系列符号；meson 配置阶段因 `host_machine.system() == 'linux'` 分支被跳过致 Linux 特有链接选项缺失。

## 根因

凡依赖 glib 且用 meson 构建的 GNOME 生态库（atk/gtk+/pango 等）在 OHOS 上编译，会遇到两个独立问题：

1. **E107 变体（intl-wrapper）**：glib 的 `libintl.h` 将 gettext 系列宏定义为 `g_libintl_*`，但 OHOS musl `libintl.so` 只导出 `libintl_*` 符号。glib 静态库引用 `g_libintl_*` 但库中无定义 → 链接 undefined symbol。
2. **E090 变体（Meson host_machine）**：meson 在 OHOS 上报 `host_machine.system() = 'harmonyos'`，库的 `meson.build` 用 `if host_machine.system() == 'linux'` 包含 Linux 特有链接器选项（`-Wl,-Bsymbolic` 等），分支被跳过。

## 受影响范围

所有依赖 glib 且用 meson 构建的 GNOME 生态库（atk/gtk+/pango 等，凡静态链接 glib 并引用 libintl 符号者）。

## 解决方案

### 方案 1：intl-wrapper.c 包装库（E107 变体）

创建 `intl-wrapper.c`，将 `g_libintl_*` 符号映射到返回 `msgid` 的兜底实现（OHOS musl 单域，domain/category 忽略）：

```c
#include <glib.h>
char *g_libintl_gettext(const char *msgid) { return (char *)(msgid); }
char *g_libintl_dgettext(const char *d, const char *m) { (void)d; return (char *)(m); }
char *g_libintl_textdomain(const char *d) { return (char *)(d); }
char *g_libintl_bindtextdomain(const char *d, const char *dir) { (void)dir; return (char *)(d); }
/* ...其余 g_libintl_* 符号同模式... */
```

在 `meson.build` 中将 `intl-wrapper.c` 加入源文件列表，并注入编译宏：
`-Ddgettext(a,b)=((char*)(b))`（musl 单域，domain 忽略，返 msgid 避 int 转换）。

### 方案 2：Meson host_machine 检测（E090 变体）

```bash
# meson.build: host_machine.system() == 'linux' → in ['linux', 'harmonyos']
sed -i "s/if host_machine.system() == 'linux'/if host_machine.system() in ['linux', 'harmonyos']/g" meson.build
```

### 方案 3：pkg-config 传播

- `PkgConfigDeps` 让 configure 通过 pkg-config 找到 glib
- `package_info()` 必须声明 `self.cpp_info.requires = ["glib::glib"]`，否则消费者编译/链接必然失败
- 复制 glib 包子模块 .pc（gobject/gio/gmodule）到 generators folder

## 验证

```bash
pkg-config --modversion glib-2.0   # 依赖库版本
meson test -C builddir             # 上游测试通过
```

## 关联

- **E090**: Meson host_machine.system() == 'linux' 不匹配 HarmonyOS
- **E107**: GLib 静态库与 gettext 动态库链接冲突
- **E046**: chmod 不生效（SELinux 限制）
