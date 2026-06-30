# AES Crypt (aescrypt-packetizer)

AES Crypt 是一款使用 AES-256 算法的命令行文件加密/解密工具，由 Paul E. Jones (Packetizer, Inc.) 开发。包含两个可执行文件：`aescrypt`（加密/解密）和 `aescrypt_keygen`（密钥文件生成）。

## 编译指导

在 HarmonyOS/OpenClaw 平台编译时需注意：

1. **覆盖 LDLIBS**：HarmonyOS 的 `uname -s` 返回 "HarmonyOS" 而非 "Linux"，Makefile 会错误添加 `-liconv`。必须显式设置 `LDLIBS=` 为空。
2. **覆盖 CC**：Makefile 默认使用 `gcc`，需设置 `CC=clang`。
3. **静态链接**：R26 要求终端工具静态链接，设置 `LDFLAGS=-static`。

```bash
make -C src CC=clang \
     CFLAGS="-fPIC -O2 -Wall -Wextra -pedantic -std=c11 -D_FILE_OFFSET_BITS=64" \
     LDLIBS= \
     LDFLAGS=-static
```

Makefile 的 install 目标不支持 DESTDIR，需手动复制产物。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [3.16](./3.16/) | published | 2026-06-29 |
