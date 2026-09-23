# gnome-autoar 0.5.2 适配笔记

## 适配场景

Windows 主机使用 Conan/MesonToolchain 交叉构建 OHOS/aarch64 归档库，并在真实设备上执行上游解压测试和消费者压缩测试。

## 关键问题与修复

1. Conan 的 Meson prefix 在 Windows 主机上可能生成带盘符的目标路径；recipe 和 `test_package` 的 OHOS 分支将目标 prefix 固定为 `/`。
2. Conan `.pc` 元数据会携带宿主 package_folder；生成阶段将 glib、libarchive、zlib 等依赖的 include/lib 复制到任务私有 `conan-deps`，并把绝对前缀改写为相对构建路径。
3. `libarchive.so` 带有 Conan 缓存 RUNPATH，不能作为目标私有运行时输入；本地化闭包只保留经过验证的 `libarchive.a`，消费者安装 ELF 使用 `$ORIGIN/../lib`。
4. Windows 不能保留官方源码中的 `/tmp` symlink fixture，因此 source 解包保留其余测试文件，目标 W3 用官方源码打包的 `tests/files` 归档恢复该 fixture，并以独立回读校正 manifest 中错误的 symlink 计数字段。

## 验证

- 本地 `conan create` r16：RC 0，日志 SHA-256 `624aafdbb4203e04feae7cff3a6839ed408f4a76e2f2df3e9f8de53f7e8c9643`。
- 目标设备 `10.62.150.125:8022`，事务 `w3-r001`，单次 launch；上游 `test-extract-unit` 22/22，消费者 10/10，release/postrelease PASS。
- 结果文件 SHA-256：`f52f1b7d46b5f0bb0aea75d7d701e880ac62467b390b1905f56d08efb174916a`。

## 边界

任务私有依赖副本和 `$ORIGIN` RPATH 只定义目标闭包，不替代目标签名、平台 CI 或 AI Review。不得修改共享 Conan 缓存；输入路径、HEAD、签名、设备身份或事务 run 漂移时必须重新验证。
