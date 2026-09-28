# rhonabwy

JOSE (JSON Object Signing and Encryption) 的 C 实现库：JWK / JWS / JWE / JWT 全流程，
以及 `rnbyc` 命令行工具（生成密钥、签名、验签、加解密、远程 JWKS 获取）。

- License: LGPL-2.1-or-later
- Homepage: https://github.com/babelouest/rhonabwy

## OHOS 适配

- 目标平台：HarmonyOS PC / OHOS aarch64（设备原生编译，CI profile `ohos-aarch64`）。
- 密码学后端：制品仓 `gnutls/3.8.10` + `nettle/3.10.2.1`；JSON 使用 `jansson/2.15.1.1`。
- 上游 CMake 工程经两处可移植性补丁适配（`patches/0001-CMakeLists.txt.patch`、
  `patches/0002-src-misc.c.patch`），补丁内无平台宏。
- 上游测试：`conan create` 的 `build()` 阶段真机执行 19 个自足 CTest 程序（libcheck 252 用例全通过）。

## 依赖关系

运行依赖 `gnutls`、`nettle`、`jansson`、`zlib`、`curl`、`orcania`、`libyder`（`gmp` 以 override 固定为 6.3.0.1）；
构建上游测试额外需要 `check/0.15.2`。

## 参考资料

- https://github.com/babelouest/rhonabwy
- https://github.com/babelouest/rhonabwy/blob/master/README.md
