# spawn-fcgi

spawn-fcgi 是一个用于启动 FastCGI 进程的工具，通常与 lighttpd Web 服务器配合使用。

## 功能特性

- 启动 FastCGI 进程供 Web 应用使用
- 支持 IPv6 连接
- 支持 Unix 域套接字
- 支持 chroot 及切换用户/组以增强安全性
- 无外部依赖

## 鸿蒙（OHOS）平台适配说明

- 使用 meson 构建系统（非 autotools）
- 在 OHOS 平台上进行 native 编译，无需交叉编译参数
- 无需源码补丁即可在 OHOS 上编译
- 需要设置 `PYTHONHOME=/data/service/hnp/python.org/python_3.12` 环境变量以解决 meson 脚本路径问题
- spawn-fcgi 使用 `-v` 显示版本信息（不支持 `--version`）

## 编译命令

```bash
meson setup build --prefix=$DEFAULT_PREFIX
ninja -C build -j1
DESTDIR=$TEST_PREFIX ninja -C build install
```

## 依赖

- 无外部依赖（仅使用 libc 函数：issetugid、socket、inet_pton）

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.6.6 | built | 2026-06-13 |

## 参考资料

- 主页: https://www.lighttpd.net/
- 源码: https://www.lighttpd.net/download/spawn-fcgi-1.6.6.tar.gz
