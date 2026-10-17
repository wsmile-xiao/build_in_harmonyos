# E596 draft — sectar CBC 尾块未记录明文长度

## 复现

在 OHOS/aarch64 静态编译后的 `sectar` 上，`qemu-aarch64 sectar -k key -e -o enc.star plain` 与 `-d -o dec enc.star` 对 33 字节输入执行后，`cmp plain dec` 返回 1：`cmp: EOF on plain after byte 33`。改成 32 字节整块时相同命令 `cmp` 返回 0。`key` 为 64 个十六进制字符，`--version` 输出 1.02。

## 根因与边界

`sectar/crypt.c` 的 `cryptEncode` 写入 keyfile 名称与 `stword32` 块长，`fread` 返回非整块时只清理下一轮缓冲；`cryptDecode` 无明文长度或规范去填充字段，逐块写出 32 字节。即使加解密功能正确，非整块输入仍会留多余的尾部字节。本次另通过 `0001-sectar-globaldefs.h.patch` 将 LP64 上的 `stword32` 固定为 `int32_t`，对应的字段宽度问题与尾块长度问题相互独立；`E595` 已覆盖一般 LP64 文件头，`E483` 已覆盖无扩展名下载 URL，本草稿只讲未记录明文长度的消费者测试误报，不重复入库。

## 推荐与验证

用整块输入建立上游原格式可验证的用例：`test_package/consumer.c` 经**包安装的 CLI**加密、解密，再由 Conan OHOS profile 编译生成的 `roundtrip.c` 并通过 `qemu-aarch64` 真正运行。已实跑的 `conan-verify` 日志包含 `RUN: qemu-aarch64 ./consumer` 与 `sectar OHOS aarch64 consumer OK`，退出 0。正文必须披露：不宣称上游格式支持任意长度的无损往返或密码学认证。若需修正格式，必须显式升级格式版本并兼容旧格式，不得在同版本悄改。

仅是协作者草稿，请主编核对测试并决定是否 promote。
