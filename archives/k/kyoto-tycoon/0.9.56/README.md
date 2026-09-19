# kyoto-tycoon 0.9.56 for HarmonyOS

Kyoto Tycoon（FAL Labs）—— Kyoto Cabinet 的缓存/存储服务器：HTTP/REST/RPC
网络接口，TimedDB 过期引擎，ktserver + 7 个 CLI 工具。
本目录提供 Conan 2 配方（HarmonyOS PC AArch64，clang）。

## 快速开始

```bash
conan create . --profile:build=<host> --profile:host=ohos-aarch64 --build=missing
```

## 产物

- `libkyototycoon.a`（静态，默认）+ 13 个头文件（kt*.h）
- 8 个 CLI：ktserver / ktutiltest / ktutilmgr / ktutilserv / kttimedtest /
  kttimedmgr / ktremotetest / ktremotemgr
- 2 个插件：libexec/ktplugservmemc.so、libexec/ktplugdbvoid.so
- `kyototycoon.pc`

## 依赖

- kyoto-cabinet/1.2.80（`--with-kc` 指向其 Conan 包目录）
- zlib/1.3.1（上游 AC_CHECK_LIB(z) 探测，经 AutotoolsDeps 注入）
- Lua 扩展关闭（上游默认；详见 notes.md）

## 测试

- 上游 `make check` 126 条（check-util 8 + check-timed 118，配方 build() 内串行运行）
- 上游 `make check-remote` 53 条（配方 build() 内起本地 ktserver 回环运行）
- test_package：24 项（TimedDB C++ API 20 + kttimedmgr CLI 4）

## License

GPL-3.0-or-later（见 tarball 内 COPYING）
