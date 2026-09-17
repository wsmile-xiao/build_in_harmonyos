# libsecret

GNOME 密钥管理库：[Secret Service API](https://www.freedesktop.org/wiki/Specifications/secret-storage-spec/)
的 GObject 客户端绑定。

交付内容：
- `libsecret-1` 共享库（org.freedesktop.Secrets D-Bus 客户端 + 本地文件后端）
- `secret-tool` 命令行工具（store/lookup/search/clear/lock）

## 已编译版本

- 0.21.7 (2026-09-15)

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | glib/gobject/gio/gio-unix |
| libgcrypt | 1.11.0 | 传输加密后端（文件后端必需） |

## OHOS 适配说明

- meson 构建系统；`crypto=libgcrypt` 启用文件后端——OHOS 无 gnome-keyring
  daemon，`SECRET_BACKEND=file` 是唯一可用的 secret 存储路径
- getpass() 声明补丁（SDK 头缺失，musl 符号存在，glib 2.84 同款问题）
- egg 测试 scratch 目录改用 g_get_tmp_dir()（/tmp 只读 E002）
- 上游测试：16 个 meson 目标中 8 个可运行（62 子用例全过），8 个依赖
  python D-Bus mock service（环境类豁免，见 notes.md）
