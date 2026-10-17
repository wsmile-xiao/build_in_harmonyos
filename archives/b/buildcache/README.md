# buildcache

buildcache 是一个 C/C++ 编译器缓存（类似 ccache/sccache），通过缓存编译器
中间产物来加速重复编译。本项目为 sccache 的 C++ 独立重写版，由 Marcus Geelnard
维护（上游：GitLab `bits-n-bites/buildcache`）。

## 功能

- 支持 GCC / Clang / MSVC / QCC / TI / GHS 等多种编译器的缓存
- 本地文件缓存 + 可选远端缓存（HTTP/S3/Redis）
- 单可执行文件交付，所有依赖内嵌（vendored）
- 支持 Lua 扩展（lua-examples）

## 版本

- 0.28.6（本仓库适配，OpenHarmony PC aarch64）
  - 适配点：`-DDISABLE_SSL=on` 绕开 OpenSSL 汇编问题；`TMPDIR` 指向可写目录
  - 上游 8 个 ctest 单元测试全部在构建期运行

## 许可证

Zlib License（上游 LICENSE 文件）。
