# polkit 127 适配笔记

## 编译环境
- **构建系统**: meson
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 3（getspnam 存根 / statx 守卫 / pthread 取消族存根）+ gettext 恒等宏 c_args

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/polkit/127 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy/codeload tarball 下载
（上游 tag 为 `127`，无 v 前缀）。

### 2. 依赖注入（generate()）
- glib/2.84.0 提供 gio-2.0/gio-unix-2.0/glib-2.0/gobject-2.0（PkgConfigDeps
  只生成 glib-2.0.pc，其余子 .pc 从 glib 包复制并改写 prefix=/——避免工具
  变量指向 /bin/...）
- expat/2.8.2（XML）、duktape/2.7.0（JS 规则引擎）
- **authfw=shadow**：pam 在 ohpcd 无，用 shadow 口令文件（零外部依赖）
- **session_tracking=ConsoleKit**：libsystemd/libelogind 在 ohpcd 无，规避
- 注入 meson 归档器 ar/ranlib 全路径（E012 变体：真机 hnp 工具链 ar 不在 PATH）
- 关闭 man/introspection/examples/gettext/gtk_doc

### 3. 构建（build()）
- meson configure + build
- PKG_CONFIG_PATH 注入 os.environ（buildenv_info 注入对 meson 未生效）
- gettext 恒等宏 `-Dgettext(x)=(x)`（OHOS libintl.h 是空 stub，不声明 gettext）
- 上游测试：test/polkit 4 个单元测试 + test/polkitbackend jsauthority（经
  wrapper.py，依赖 Python dbusmock——OHOS pip 镜像无此包，平台限制）

### 4. 打包（package()）
- meson install；产物：libpolkit-gobject-1、libpolkit-agent-1、libpolkit-backend、
  polkitd、pkaction/pkcheck/pkexec/pkmon/pkttyagent

## 依赖
- glib/2.84.0、expat/2.8.2、duktape/2.7.0（均 ohpcd 已发布）

## 上游测试（rule 4）
- test/polkit 4 个单元测试 + test/polkitbackend jsauthority 均经
  test/wrapper.py 运行，其模块级 `import dbus`/`import dbusmock` 硬依赖
  Python dbusmock——OHOS pip 镜像 pypi.cnb.cool 无此包（versions: none 实测）；
  C 测试二进制绕过 wrapper 直接运行也 GLib-FATAL-CRITICAL
  （g_datalist_id_set_data_full: assertion 'key_id > 0' failed，需 mock D-Bus
  环境初始化）——按 rule 1.2 如实声明为平台限制（非跳过）
- 本地验证：conan create 通过（exit=0），94/94 目标编译链接成功并打包
- 适配后：test_package R34 真实产物校验

## 已知限制
- polkitd 守护进程依赖运行中的 D-Bus system bus——OHOS 沙箱无，daemon
  运行类功能按平台限制声明；库 API 与 CLI 编译可用
