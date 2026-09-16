# libtbox

## 简介

tbox 是 TBOOX 团队的类 glib 跨平台 C 库，提供 stream、coroutine、container、
algorithm、charset、hash、xml、regex、object、database 等模块，是 xmake 构建工具
的上游基础库。对外入口为 `tb_init()` / `tb_exit()`，头文件 `tbox/tbox.h`。

## OHOS 适配

- 自带 script-only `configure`（xmake.sh 引擎），生成纯 Makefile 构建，
  真机/CI 均无需安装 xmake 二进制
- `--toolchain=envs` 让构建从环境变量取 `CC`/`CXX`（值由 Conan conf 格式化
  传入，R33 合规），`CONFIG_SHELL` 显式指定 OHOS bash（R5）
- xmake.sh 不认识 ohos plat，`--plat=linux --arch=arm64`（OHOS 用户态对纯 C 库
  走 Linux 兼容的 posix/epoll 路径）
- `--demo=n` 关示例、`--small=n` 开全模块，可选三方包
  （zlib/sqlite3/mysql/openssl/polarssl/pcre2/pcre）全部关闭，保持 hermetic
- 上游无测试套件，test_package 自建 `tb_init` / CRC32 已知答案 / vector
  真实调用验证；默认静态链接

## 依赖

- 无三方依赖（仅 pthread / dl / m / c 系统库）

## 功能验证

```bash
# test_package 消费者验证（二进制由 conan create 自动构建运行）
./test_libtbox  # 期望输出: ALL TESTS PASSED
```

## 参考

- 上游仓库: https://github.com/tboox/tbox
- 源码: https://github.com/tboox/tbox/archive/refs/tags/v1.8.1.tar.gz
- 文档: https://docs.tboox.org
