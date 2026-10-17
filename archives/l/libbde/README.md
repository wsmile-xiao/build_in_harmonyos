# libbde

libbde 是访问 BitLocker 驱动器加密 (BitLocker Drive Encryption, BDE) 卷格式的 C 函数库。BDE 是 Microsoft Windows 自 Vista 起用于整卷加密存储介质数据的卷级加密方案。

该项目还包含两个终端工具:

- **bdeinfo**: 显示 BDE 卷信息 (加密方法、卷标识、密钥保护器等)
- **bdemount**: 挂载 BDE 加密卷 (经由 FUSE  exposing 解密后数据)

## OHOS 适配

- 构建系统为 GNU Autotools, 与同门库 libesedb 完全同构, 复用其已验证的三件套:
  `config.guess` HarmonyOS 检测分支 (E007)、`config.sub` ohos 模式 (E007)、
  `configure`/`config.status` 的 `umask 077→022` (E011, HMDFS 权限限制)。
- `bindtextdomain` 位于独立 libintl, 链接 gettext 0.26 的 `-lintl` (E053)。
- 静态构建 (`--enable-static --disable-shared`), 无外部 Conan 依赖;
  上游内嵌的 libyal 子库 (libcerror、libcdata、libclocale 等) 随源码一起编译。
- 上游测试为 `make check` (24 个 `bde_test_*` 单元程序 + 3 个 shell 驱动,
  详见版本目录 `test_package/MANIFEST.yml` 的审计)。

## 依赖

无外部依赖。内部包含 libyal 系列子库 (libcerror、libcdata、libclocale、
libcnotify、libuna 等, 随源码包发布)。

## 参考

- 上游仓库: https://github.com/libyal/libbde
- 20240502 发布页: https://github.com/libyal/libbde/releases/tag/20240502
- 官网文档: https://github.com/libyal/libbde/blob/main/documentation/BitLocker%20Drive%20Encryption%20(BDE)%20format.asciidoc
