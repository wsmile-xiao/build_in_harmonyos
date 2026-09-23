# openssl 3.5.6.1.2 适配笔记（动态库版）

## 背景
harmonybrew rust 工具链（librsvg 2.62+ 构建所需）的 cargo.real 运行时 NEEDED
`libssl.so`/`libcrypto.so`（readelf 实测，符号为版本化 `OPENSSL_3.0.0`——必须
OpenSSL 3.x 动态库）。harmonybrew 的 openssl@3 bottle 在 harmonybrew.atomgit.com
**全版本 404**（rust/zlib bottle 存在，唯独 openssl 缺失），bootstrap 因此失败。
ohpcd 制品仓 openssl 为静态库（R26 no-shared 防 .so 污染设计）。按 R37 发布
**3.5.6.1.2**（动态库版），专供 rust 工具链运行时。

## 相对 3.5.6.1.1 的变更
- `build()`：`no-shared` 硬编码条件化——`shared=True` 时不加 `no-shared`
  （产出 libssl.so/libcrypto.so 动态库），`shared=False` 保持静态（R26 不变）
- `package()`：沿用 `make install_sw`（shared 构建时自动安装 .so）
- 其余（Configure 参数、补丁 0001/0002、test_package）沿用 3.5.6.1.1

## 构建验证
```bash
conan create archives/o/openssl/3.5.6.1.2 --version=3.5.6.1.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --options "openssl/*:shared=True" --build=missing
```
- 包内 lib/libssl.so + lib/libcrypto.so（OpenSSL 3.5.6，OPENSSL_3.0.0 符号节点）
- test_package 3/3 通过（SSL_CTX created successfully 等）

## 使用方式（供 librsvg 配方 bootstrap）
librsvg/2.62.3.1 的 `_bootstrap_rust_toolchain()` 中 openssl bottle 项（404）改为
本包：下载后把 libssl.so/libcrypto.so 放入 rust 工具链运行时目录（或 LD_LIBRARY_PATH
注入），cargo.real 即可运行。

## 注意事项
- 本动态版**仅作为 rust 工具链运行时依赖**分发，不进入系统库路径（R26 静态设计
  仍适用于系统场景）；下游引用需显式 requires 本版本
- 若其他下游（如 gtk 的 at-spi 链）已 require openssl 静态版，版本共存无冲突

**编译日期**: 2026-09-08
**状态**: built（本地 W3 验证通过，动态库产物确认）
