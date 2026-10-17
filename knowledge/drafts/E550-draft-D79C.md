# E550 草稿：`MAXNAMLEN` 不适合完整路径缓冲区

## 错误特征
`miscfuncs.c:68:26: error: use of undeclared identifier 'MAXNAMLEN'`。`xtail/2.1` 的 `scan_directory()` 将目录路径加目录项名称放入 `pathname[MAXNAMLEN]`。

## 根因与适用范围
OHOS 的 `<dirent.h>` 未暴露 BSD 宏 `MAXNAMLEN`；即使从 `<sys/param.h>` 导入该宏，通常也仅约 255 字节，目录路径拼接文件名后可能溢出。针对将 `dirname + "/" + d_name` 放入 `MAXNAMLEN` 大小数组的旧式 C 程序，不是通用的 `<dirent.h>` 缺失问题（已查 `E032`：它针对 `_GNU_SOURCE` 后暴露 dirent API；本例 `DIR`/`readdir` 均可用）。本地 `knowledge/graph` 与 `knowledge/drafts` 对 `MAXNAMLEN` 查重无命中。

## 修复
包含 `<limits.h>` 并将完整路径缓冲区改为 `PATH_MAX`；在复制目录前、复制每个 `d_name` 前各检查所需总长度，超界不写入。其他平台可采用按实际路径长度动态分配；不要简单 `#define MAXNAMLEN 255`，这只掩盖编译错误，留存溢出。

## 验证
`make -j2` 使用 aarch64-linux-ohos-clang 编译通过。相同 `.o` 用 `-static` 重链后，`qemu-aarch64` 对长度超过 255 字节的目录路径中新建文件监视通过；动态交付产物在 x86 runner 上未直接执行。

## 关联
`draft-review E550-draft-D79C --json` 报 `review-similar`，最相近 `E500`（评分 0.42）处理 `MAX_INPUT` 宏，非 `MAXNAMLEN`，根因与缓冲区溢出风险不同；`E032` 是 dirent 特性宏问题。建议主编审核后选择空闲正式编号 promote，避免覆盖现有 E550 其他贡献者草稿。
