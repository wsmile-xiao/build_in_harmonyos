# bitlbee-facebook — OpenHarmony 编译档案

[bitlbee-facebook](https://github.com/bitlbee/bitlbee-facebook) 是
[bitlbee](https://www.bitlbee.org/)（IRC ↔ 即时通讯网关）的 Facebook
Messenger 协议插件，使 IRC 客户端可通过 bitlbee 收发 Facebook 消息。

## 产物与加载方式

| 项目 | 值 |
|------|-----|
| 产物 | `lib/bitlbee/facebook.so`（dlopen 模块，SONAME facebook.so） |
| 加载方式 | bitlbee 宿主运行时 `dlopen()`（非链接库，消费者永不 -lfacebook） |
| 入口符号 | `init_plugin` / `init_plugin_info`（G_MODULE_EXPORT，plugin_info ABI v1） |
| 安装布局 | `lib/bitlbee/` = bitlbee PLUGINDIR 上游默认布局 |
| 动态依赖 | DT_NEEDED 仅 `libc.so`（glib/json-glib/libffi/pcre2/zlib 全静态嵌入） |

库包（无命令行工具）：不需要 commands.json（R38）。

## 宿主关系（bitlbee 3.6）

- 运行时目标宿主为 bitlbee 3.6（ABI `plugin_info.abi_version=1`，插件
  API 符号 register_protocol/imcb_*/set_* 等由宿主可执行文件导出解析）
- conan `bitlbee/3.6` 包**仅含 bin/bitlbee 二进制**（无头文件、无
  bitlbee.pc），故不在本配方 requires 中；dev 头文件由 bitlbee 3.6
  sdist 复现上游 `make install install-dev` 语义供给（configure 生成
  config.h + 平铺头文件，同上游 CI 做法）
- 插件事件循环走 bitlbee `b_*` API，不经宿主 GMainContext

## 依赖清单（全部静态嵌入 facebook.so）

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0 | 与 bitlbee/3.6、json-glib/1.6.6 依赖图一致 |
| json-glib | 1.6.6 | Facebook Graph API 响应解析 |
| libffi | 3.4.4 | gobject 闭包编组拉入 |
| pcre2 | 10.40 | glib 依赖拉入 |
| zlib | 1.3.1.1 | **PIC 重建版**（1.3.1 的 libz.a 非 PIC 无法入共享模块）；插件运行时真实使用（MQTT payload deflate/inflate） |
| openssl | 1.1.1w | 仅构建期（bitlbee sdist configure --ssl=openssl） |

工具链：automake/1.18 + libtool/2.5.4（tool_requires，CI 沙箱自举）。

## OHOS 适配要点

- **pkg.m4 预设变量旁路**：conan PkgConfigDeps 只产聚合 glib-2.0.pc
  （缺 gio-2.0.pc/gobject-2.0.pc），且无 bitlbee.pc——配方经
  AutotoolsToolchain 环境注入 BITLBEE/GLIB/JSON 六个 _CFLAGS/_LIBS +
  GLIB_GENMARSHAL（两变量同时非空时 PKG_CHECK_MODULES 整体跳过）
- **E114**：生成 configure 后去掉 config.status 的 `umask 077`（HMDFS
  上 0700+setgid 临时目录不可写，chmod 亦不生效）
- **E236**：conan pcre2/libffi 包内 .la 元数据 stale（libdir='//lib'），
  复制 .a 到 .la-free 私有目录再 -L/-l（conan 缓存不动）；打包剔除
  facebook.la
- **E074**：make -j1（HMDFS jobserver fifo EPERM）
- **桩宿主测试范式**：test_package 编译导出 bitlbee 插件 API 全符号面
  的桩宿主（-rdynamic），dlopen(RTLD_NOW) 验证全重定位 + init_plugin_info
  ABI 三元组 + init_plugin 注册行为；L1e 破坏性反证通过

详见版本级 [1.2.2/notes.md](1.2.2/notes.md)（问题/解法 9 条全记录）。

## 上游与许可

- 上游：https://github.com/bitlbee/bitlbee-facebook（tag v1.2.2）
- 许可证：GPL-2.0-or-later（源码 COPYING 实读：GNU GPL Version 2，
  头文件声明 "or (at your option) any later version"）
- 上游无测试套件（40 文件 tarball 无 tests/，上游 CI 仅编译验证），
  详见版本级 [1.2.2/UPSTREAM_TESTS.md](1.2.2/UPSTREAM_TESTS.md)
