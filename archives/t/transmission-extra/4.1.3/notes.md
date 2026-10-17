# transmission-extra 4.1.3 HarmonyOS PC 适配说明

## 构建范围

本归档对应 Alpine `transmission-extra` 子包语义，仅交付：

- `transmission-create`
- `transmission-edit`
- `transmission-show`

上游同目录还会构建 `transmission-remote`，配方在安装阶段删除该文件，避免扩大任务范围。

## 依赖策略

- 使用已发布的 `curl/8.15.0`、`openssl/3.5.6.1`、`zlib/1.3.1.1`、`libevent/2.1.13` 和 `libdeflate/1.25` OHOS armv8 制品。
- miniupnpc、libnatpmp、libpsl、DHT、libutp、fmt 等使用官方 4.1.3 Release 源码包内置版本，不声明未发布依赖。
- 关闭 GTK、Qt、daemon、CLI、Web、NLS、systemd、inotify 和 kqueue。
- CMake ExternalProject 在 OHOS 并行构建中不会及时传播内置依赖的头文件与静态库前缀；配方先构建并 staging 内置静态库，补丁使用源码或生成目录中的对应头文件。
- 安装后删除 `transmission-remote` 及内置依赖附带的开发文件和辅助工具，最终应用包仅保留三个目标工具与许可证。

## 测试结果

上游 CTest 发现 545 项。精确排除依赖外部 DHT 环境的 1 项，以及受 HarmonyOS POSIX 权限位和文件锁语义影响的 2 项。其余 542 项中：509 项通过、22 项由上游按 locale/IPv6 环境跳过、11 项为上游禁用、失败 0。跳过、禁用和排除项均不计为通过。

消费者测试验证最终包仅含三个目标工具、无 `include/lib/share` 开发目录，并执行版本检查以及真实创建 torrent、查看元数据、添加 tracker 后再次查看，共 12/12 PASS。

详细口径见 `test_package/MANIFEST.yml` 和版本 `manifest.yaml`。
---

**编译结束**: 2026-08-18 22:43
**最终状态**: built
