# chiark-utils

Ian Jackson 的 chiark 系统工具集:缓冲管道读写、文件锁执行、远程续传复制、
X11 电池监视器、nettle 校验和树、FastCGI 预 fork 解释器、setuid 特权执行等
命令行工具。裸 Makefile 构建(无 configure),多可执行程序包。

- 上游: https://www.chiark.greenend.org.uk/ucgi/~ian/git/chiark-utils.git
- 源码包: Debian 官方 pool(上游维护者即 Debian 打包者)
- 许可: GPL-3.0-or-later

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 8.0.1 | built | 12 个二进制(bin×10 + sbin×2);xduplic-copier 因 libxmu 未发布按 R36 剔除,待 8.0.1.1 补回 |

## 程序清单(8.0.1)

bin: readbuffer writebuffer with-lock-ex xbatmon-simple summer watershed
rcopy-repeatedly prefork-interp cgi-fcgi-interp acctdump
sbin: trivsoundd really

依赖: nettle/3.10.2.1, gmp/6.3.0, libx11/1.8.13, libuv/1.52.1, xorgproto/2025.1

版本级详情见 `8.0.1/manifest.yaml` 与 `8.0.1/notes.md`。
