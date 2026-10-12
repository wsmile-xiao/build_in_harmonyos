# libwandder 2.0.22 适配纪要

上游标签 `2.0.22-1`（库版本 2.0.22）。仓库 https://github.com/LibtraceTeam/libwandder 。

## 构建

标签包只有 `configure.ac` / `Makefile.am`，没有生成的 `configure`。与 wandio/4.2.7 一样，不在沙箱里跑 autotools bootstrap，直接编译 `src/Makefile.am` 的五个库源文件。

`configure.ac` 要求 `uthash.h`、`libm`、`libpthread`。ETSI 源文件调用 OpenSSL `EVP_*`，配方 `requires` 制品仓已发布的 `uthash/2.3.0` 与 `openssl/3.5.7`。`libm` / `libpthread` 用系统库。

没有补丁。默认静态库 `libwandder.a`。安装的公开头文件与上游 `include_HEADERS` 一致：`libwandder.h`、`libwandder_etsili.h`。

## 上游测试

标签树没有 `tests/`，`Makefile.am` 没有 `TESTS` / `check_PROGRAMS`，`configure.ac` 没有测试框架，`.github/workflows` 只有 deb/rpm 打包。`build()` 不运行上游套件。上游用例数是 0，不是漏跑。

## 消费者测试

`test_package/test_wandder.c` 链接打好的库。DER 值放进 universal SEQUENCE 再解出来，因为 `wandder_encode_finish()` 只用顶层 `childrensize` 分配缓冲区，裸的顶层 primitive 会在 `encode_pending()` 里断言。BER 用 `wandder_encode_next_ber`。另外调用 `wandder_decode_integer_value` 和 `wandder_create_etsili_decoder` / `wandder_free_etsili_decoder`。

真机 `CONAN_HOME=~/work/psj/ch-lwd15031`，`conan create` 退出码 0。测试程序打印 `CHECKS 107/107 passed, 0 failed`。上游套件 0/0。
