# roxterm

ROXTerm（realh/roxterm）：基于 VTE/GTK3 的终端模拟器，支持多标签、配色方案、快捷键方案与 DBus 会话管理。

- 版本: 3.18.2
- 许可: GPL-3.0
- 状态: published（aarch64-linux-ohos，OHOS SDK native llvm，profile ohos-aarch64）
- 依赖（均取自 ohpcd 制品仓已发布 binary）: vte/0.74.2, gtk/3.24.43, glib/2.84.0.1, pango/1.56.4, cairo/1.18.4.2, dbus/1.14.10, dbus-glib/0.114.1, pcre2/10.45, expat/2.8.2.1；gettext/0.22.5.1（tool_requires, msgfmt）
- 构建: CMake + PkgConfigDeps；产物 bin/roxterm、bin/roxterm-config
- 上游测试: N=0（无 enable_testing/add_test），以 test_package 三层探针替代（ELF/AArch64 + NEEDED 闭包 + headless 启动探测），100% 通过

关键适配点（详见 3.18.2/notes.md）：
- E527/E463: glib-compile-resources staging 复制 + 重签 + shell wrapper 解 libffi/libintl 遮蔽
- libintl.so.8 SONAME 冲突（gettext vs glib proxy-libintl）→ wrapper 强制 glib libdir 置前
- 离线 CI 无法在线拉 docbook.xsl → BUILD_MANPAGES 选项（补丁，上游默认 ON 不变）
