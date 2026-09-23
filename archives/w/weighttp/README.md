# weighttp

Lightweight and simple webserver benchmarking tool.

- 上游: https://git.lighttpd.net/lighttpd/weighttp (GitHub mirror: https://github.com/lighttpd/weighttp)
- 版本: 0.5
- 许可证: BSD-3-Clause

## OHOS 适配

- 单文件 C 程序，使用 clang 直接编译 `src/weighttp.c -lpthread -lm`
- 无额外依赖，OHOS musl 已提供 pthread/poll/socket
- 提供 gh-proxy 镜像回退保障下载

## 验证

```bash
weighttp -h
weighttp -V
weighttp -n 10 -c 2 http://127.0.0.1:8000/
```
