# chezdav 3.0 适配笔记

## 编译环境

- 构建系统：Meson
- 编译日期：2026-09-09
- 目标平台：HarmonyOS PC / aarch64
- 编译器：clang/clang++
- 状态：pending（等待 HarmonyOS 原生 W3/CI 终态验证）

## 上游与版本

- 官方项目：GNOME phodav
- 上游版本：3.0
- Conan/上游版本：3.0
- 任务表给出的标识：3
- 有效提交分支：`feat/chezdav-3.0`（Conan 2 不接受单字符版本 `3`，且 CI R40 要求分支与有效 Conan 版本一致）
- 官方源码：https://download.gnome.org/sources/phodav/3.0/phodav-3.0.tar.xz
- SHA256：`392ec2d06d50300dcff1ef269a2a985304e29bce3520002fca29f2edc1d138d1`

任务名称是上游源码产出的命令行工具 `chezdav`。配方从完整 phodav 3.0 源码构建，但归档只发布 `bin/chezdav`，不把 `spice-webdavd` 或公开 libphodav 开发文件混入应用包。

## 依赖预检

适配前已使用 `conan download --only-recipe -r=ohpcd` 实测以下配方均已发布：

- glib2/2.88.0
- libsoup3/3.6.5-r2
- libxml2/2.15.3.1
- zlib/1.3.1.1
- pcre2/10.45
- libpsl/0.21.5.1
- libidn2/2.3.7.1
- libunistring/1.0
- libnghttp2/1.70.0
- sqlite3/3.49.1

`libffi 3.5.2` 与 `proxy-libintl 0.5` 由已发布的 glib2 配方作为源码子项目内置，不是 chezdav 依赖图中的独立 Conan 引用。

## 上游测试清点

统一计数口径：采用 GLib 测试框架实际注册的参数化 case 数。

| 项目 | 数量 | 证据 |
|---|---:|---|
| 测试源文件 | 2 | `tests/virtual-dir.c`、`tests/virtual-dir-server.c` |
| Meson 注册测试程序 | 1 | `tests/meson.build` 中 `test(name, exe)` |
| GLib 参数化测试 case | 18 | `virtual-dir.c` 的 `TestCase tests[]` 共 18 个元素，并逐项调用 `g_test_add_data_func` |

18 个 case 覆盖 GET（5）、MKCOL（3）、COPY（4）、PUT（3）和 DELETE（3）。`virtual-dir-server.c` 是同一测试程序使用的服务器 fixture，不单独增加 case 数。

## 适配设计

1. 使用官方 phodav 3.0 tarball，并通过单个可审计补丁调整构建目标与私有 UUID helper。
2. 关闭可选 Avahi/mDNS；核心 WebDAV 监听、只读模式和 digest authentication 保持不变。
3. 将内部 libphodav 静态链接进 `chezdav`，不构建也不发布任务范围外的 `spice-webdavd`。
4. 复用仓库已验证的 GLib 单副本策略：保留 glib2 `.pc` 的编译参数，但清空其链接参数；同时把 Conan 生成的 `libsoup-3.0.pc` 链接行收敛为 libsoup 自身共享库，避免给 `chezdav` 再链接一份静态 GLib/GObject。
5. 保留上游 18 个 localhost WebDAV case，并新增 3 个打包后二进制检查：版本、帮助、实际 HTTP GET。

## 源码修改

`0001-build-chezdav-with-bundled-uuid.patch` 只做两项范围受控的构建适配：

- 在 `libphodav/phodav-method-lock.c` 中增加私有 RFC 4122 version 4 UUID helper。已发布的 shared libsoup3 只导出其自身使用到的 GLib 符号，CI #42767 实证不包含 `g_uuid_string_random`；helper 仅使用已核验导出的 `g_random_int` 和 `g_strdup_printf`，因此仍保持进程内单一 GLib/GObject 符号域。CI #42786 进一步证明上游旧 `guuid.c` 与 GLib 2.88 的同名宏不兼容，因此不再编译该旧兼容文件。
- 不构建任务范围外的 `spice-webdavd`。该 daemon 不是 chezdav 交付产物，在 CI #42767 中还会额外要求 libsoup3 未导出的 `g_socket_service_*` 符号。

补丁不修改、删除或跳过任何上游测试；`tests/virtual-dir.c` 的 18 个参数化 case 及其 fixture 均保留。

## 验证结果

- 语言预检：通过；任务语言 `cpp`，检测主体语言 `c`，二者属于 C/C++ 兼容族。
- 依赖预检：通过；直接依赖与已知传递依赖配方均可从 ohpcd 下载。
- Conan 配方静态完整性（G1）与预构建风险评估（G0）：通过。
- 同源 CI 静态门禁：L0、知识库检查 KC、杂项/原子性检查 JC 全部通过；macOS 缺少 worker 预装的 GNU `timeout`，脚本在进入 `conan create` 前停止。
- 本机 G2：依赖图解析和 8 个 HarmonyOS 二进制依赖下载成功；进入构建后因 macOS 主机没有 HarmonyOS worker 的 `meson`/工具链环境而停止，未计为 HarmonyOS 测试结果。
- 远端 CI #42767：G0/G0e、L0、KC、JC 全部通过；Meson 成功配置并完成编译，链接阶段实证 `chezdav`/测试 fixture 缺少 `g_uuid_string_random`，非交付目标 `spice-webdavd` 缺少 4 个 `g_socket_*` 符号。已按真实日志加入最小构建补丁，等待下一轮 CI 验证。
- 远端 CI #42786：确认补丁已进入构建，目标数由 32 降至 31，`spice-webdavd` 已不再构建；随后上游旧 `guuid.c` 因 `G_UUID_DEFINE_STATIC` 与 GLib 2.88 同名宏签名冲突而编译失败。现改为 phodav 私有 UUID helper，等待下一轮 CI 验证。
- 上游测试：待 HarmonyOS 原生 W3/CI 实跑，申报总数 18。
- 新增消费者测试：待 HarmonyOS 原生 W3/CI 实跑，申报总数 3。

## 已知边界

- 当前执行主机是 macOS，不能完成 HarmonyOS 原生编译与运行；不能把本机结果冒充 HarmonyOS PC 结果。
- Avahi/mDNS 是可选发现功能，因非核心依赖而关闭；目录共享、监听模式、只读和 digest authentication 功能保留。
