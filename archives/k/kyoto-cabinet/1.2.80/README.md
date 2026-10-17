# kyoto-cabinet 1.2.80 for HarmonyOS

Kyoto Cabinet — 高速键值数据库（QDBM 后继），文件哈希/树/目录/森林后端。
本目录提供 Conan 2 配方（HarmonyOS PC AArch64，musl，clang 15）。

## 快速开始

```bash
conan create . --profile:build=<host> --profile:host=ohos-aarch64 --build=missing
```

## 产物

- `libkyotocabinet.a`（+ 17 个 CLI：kc*test / kc*mgr / kclangctest）
- 头文件 kcabspathdb.h … kcurl.h 等（见 tarball 内 HEADERFILES）
- `kyotocabinet.pc`

## 依赖

- zlib/1.3.1（压缩，默认开启，上游默认）

## 测试

- 上游 `make check`：512 条命令、11 个子目标，配方 build() 内串行运行
- test_package：27 项断言（文件 HashDB：创建/写入/读取/覆盖/删除/迭代/
  重开/持久化/非法路径/损坏输入）

## 补丁

- `0001-configure-umask-hmdfs.patch`：configure 临时目录 umask 077→022（HMDFS）

## License

GPL-3.0-or-later（含 FOSS/LINK 例外，见 COPYING / FOSSEXCEPTION）
