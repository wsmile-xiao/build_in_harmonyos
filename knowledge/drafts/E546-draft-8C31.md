# E546 — polkit 适配 OHOS：`-Dlibs-only=true` 仅构建 libpolkit-gobject-1 客户端库

## 错误特征

polkit 完整构建失败或依赖解析报错：

```
polkitd: command not found
polkitbackend requires D-Bus system bus
```

下游（accountsservice）只需 `libpolkit-gobject-1` 客户端库。

## 触发条件

- 构建系统: meson
- 阶段: configure

## 根因分析

polkit 完整构建需要 polkitd 守护进程 + D-Bus 系统总线 + systemd 依赖，OHOS
平台没有系统总线与守护进程运行场景。但下游软件（如 accountsservice）只在
meson.build 里 `dependency('polkit-gobject-1')` 链接客户端库，因此只需裁剪出
GObject 客户端库即可满足构建依赖。

## 解决方案

### 推荐方案

meson 配置裁剪服务组件：

```bash
meson setup build --prefix=$DEFAULT_PREFIX \
  -Dlibs-only=true \
  -Dintrospection=false \
  -Dgtk_doc=false
```

- `-Dlibs-only=true`：跳过 polkitd/polkitbackend/polkitagent/programs，
  仅产出 libpolkit-gobject-1 客户端库。
- `-Dintrospection=false -Dgtk_doc=false`：关闭 gobject-introspection 与
  gtk-doc 文档依赖（OHOS 无对应工具链）。

### 禁止做法

- ❌ 硬加 systemd 相关依赖选项——libs-only 模式下不接触 service 组件，
  加 systemd 反而破坏裁剪。
- ❌ 尝试在 OHOS 运行 polkitd——无系统总线，运行期授权不可用（只做库级
  构建依赖交付，notes.md 已记录该运行期限制）。

## 验证

```bash
meson setup build -Dlibs-only=true -Dintrospection=false -Dgtk_doc=false
meson compile -C build
conan create . --build=missing
ls build/lib/libpolkit-gobject-1.so
```

## 关联条目

- 相关: E544（cmake-extras 模块缺失）
