# libaudclient

Audacious 音乐播放器的 D-Bus 远程控制客户端库：`audctrl` API 封装 dbus-glib 代理调用，让第三方前端/脚本控制运行中的 Audacious（播放、播放列表、均衡器、播放队列等 71 个导出函数），并随包安装 `audclient.pc`。Audacious 2.x 时代独立发布，最后版本 3.5-rc2。

## 功能概述

- 播放控制：play/pause/stop/play_pause、jump_to_time、音量与均衡（`audacious_remote_*`）
- 播放列表管理：add/delete/clear、URL 插入、playqueue 队列操作
- 状态查询：is_playing/is_paused、playlist_pos/length、tuple 元数据字段
- 会话辅助：`audacious_get_tuple_field_data`、`audacious_remote_get_tuple_fields`

## OHOS 适配

- 构建系统为 audacious 自研 buildsys.mk（非 automake）；官方发布 tarball 自带预生成 `configure` 与 `dbus-client-bindings.h`，无需 autotools 工具链
- config.guess/config.sub 应用 E007 OHOS 识别（HarmonyOS uname → `aarch64-unknown-linux-ohos`）
- glib/dbus/dbus-glib OHOS 制品 static-only：libaudclient.so 通过 E236 la-free 目录内联整条静态依赖链，DT_NEEDED 仅 libexpat.so
- 上游 Makefile 的 `LIBS += ${GLIB_LIBS} ${DBUS_LIBS}` 顺序在静态链接下无法解析（消费者 libdbus-glib-1.a 在 glib 归档之前）；补丁 0003 交换为 DBUS_LIBS 在前
- configure 有独立的 `glib-2.0 >= 2.28` 模块检查，pkg.m4 预置变量必须非空（空串会触发 pkg-config 查询并中止）
- configure 硬性要求 dbus-binding-tool（AC_PATH_PROG + AC_MSG_ERROR）；从 dbus-glib 包 bin/ 预置绝对路径
- 上游无自动化测试套件（buildsys.mk.in 无 check 目标），由 test_package 执行链接期 ABI + dlopen(soname) + 全量 71 导出符号 dlsym 验证

## 依赖关系

- 编译依赖：dbus-glib/0.114、dbus/1.14.10（传递 glib/2.88.0、expat/2.8.2、pcre2/10.45、zlib/1.3.1）
- 运行时：libaudclient.so 的 DT_NEEDED 仅 libexpat.so（静态链已内联）

## 已知限制

- OHOS 无 D-Bus session bus（dbus 包不含 dbus-daemon），且无运行中的 Audacious；audctrl 所有 API 都立即发送 D-Bus 消息，方法调用路径无法在设备上执行
- 消费者若在链接 libaudclient.so 的同时直接调用 glib API，会引入第二份 GType 运行时（glib static-only 所致，dbus-glib 0.114 E257 同类风险）
- 上游 audctrl.h 声明的 `audacious_set_session_uri`/`audacious_get_session_uri`/`audacious_set_session_type` 在 3.5-rc2 的 audctrl.c 中无实现（仅声明），引用会在链接期失败

## 参考资料

- 上游仓库：https://github.com/audacious-media-player/libaudclient
- 发布源：https://distfiles.audacious-media-player.org/
- 许可证：BSD-2-Clause
