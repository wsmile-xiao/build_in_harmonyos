# menu-cache

menu-cache 是 LXDE 桌面环境的菜单缓存库，用于加速菜单读取。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1.0 | built | 2026-08-22 |

## 编译配置

- 构建系统: autotools
- configure 参数: `--disable-shared --enable-static --build=aarch64-linux-ohos --host=aarch64-linux-ohos`
- 依赖: glib-2.0, libfm-extra

## 参考

- 源码: https://github.com/lxde/menu-cache