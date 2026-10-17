# appstream

## 简介
AppStream 是自由桌面生态的软件元数据规范与工具链：提供 libappstream（C 库，解析/校验
软件目录 metainfo 数据）与 appstreamcli 命令行工具（metainfo 校验、news 转 metainfo 等）。
上游：https://github.com/ximion/appstream

## OHOS 适配要点（1.2.0）

### 构建系统
Meson（meson>=0.62，c_std=gnu17），Conan 配方 `archives/a/appstream/1.2.0/`。
构建选项关闭 systemd/gir/man/docs/apidocs/qt/compose/vapi/apt-support/display-detection/bash-completion。

### 关键适配点
- **glib pc-fix**：glib 包 .pc 以 prefix=/ 安装且 Requires(.private) 带静态内嵌依赖；
  复制真实 .pc 集合、重写 prefix、剥离 proxy-libintl/libpcre2-8/zlib/libffi 后置
  PKG_CONFIG_PATH 最前，meson 才能解析 glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gio-unix-2.0。
- **glib host 工具 wrapper**：glib-compile-resources 等从 conan 缓存路径 exec 受
  HMDFS 签名/权限限制；在 machine file `[binaries]` 映射 wrapper 脚本
  （export LD_LIBRARY_PATH=glib 包 lib 再 exec 原二进制），ninja 生成 gresource C 代码正常。
- **gettext 声明**：OHOS sysroot libintl.h 是空 stub；复制 glib 包内 proxy libintl.h
  到构建 include 目录并前置 -I，gettext 宏映射到 g_libintl_*（链接期由 proxy-libintl 提供）。
- **补丁**：`0001` 移除 stemmer 硬编码 `/usr/include`（OHOS 无此目录）；`0002` 使
  itstool_join 可选（OHOS 无 itstool，回退未翻译 metainfo，校验测试仍运行）。
- **组件式 package_info**：头文件在 include/appstream/；components["appstream"] +
  全量 lib.requires 保证生成的 appstream.pc Requires 链完整，静态库消费者
  （libglib/libcurl/libxml2/libfyaml/libstemmer/libxmlb/zstd）可链接全部符号。
- **package_type=library** + commands.json：appstreamcli 是 CLI 工具，
  commands.json 声明（R38/L0k）。

### 测试
- 上游测试双口径：source_declared_total=14 / configured=8；执行 8 通过 4
  （2 项 /tmp erofs 只读硬编码路径平台阻塞、2 项 ohpcd libcurl 无 SSL 依赖缺口），
  明细见 `1.2.0/reports/evidence/r02-upstream-test-ledger.md`。
- 鸿蒙专项测试 `1.2.0/harmonyos-test/`：调用公开 API 解析 metainfo 并断言，10 项全 PASS。
- test_package：真实 API 消费者验证（R34），conan create 内 1/1 通过。

## 交付物
| 文件 | 说明 |
|------|------|
| 1.2.0/conanfile.py | Conan 配方（meson、组件式 package_info、glib pc-fix、工具 wrapper） |
| 1.2.0/conandata.yml | 官方源 + SHA-256 + 2 补丁 |
| 1.2.0/patches/ | 0001-stemmer-include-dir / 0002-itstool-optional |
| 1.2.0/test_package/ | L1 消费者验证 |
| 1.2.0/harmonyos-test/ | 鸿蒙专项测试 |
| commands.json | appstreamcli CLI 声明（R38） |

## 注意事项
- 构建机 github.com 直连超时：本地构建曾临时以本地 tarball 完成，提交前已恢复官方 URL 并核验 SHA-256
- /tmp 为 erofs 只读：上游硬编码 /tmp 的测试为真实平台阻塞
- ohpcd libcurl/8.5.0 无 SSL：https URL 格式校验误报 "URL format is invalid"，属依赖能力缺口