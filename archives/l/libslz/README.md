# libslz（SLZ — StateLess Zip）

libslz 是 Willy Tarreau 开发的**无状态流式压缩库**：调用方每次喂入数据块，
库不保存跨调用的字典，仅用 28 字节的流描述符即可产出 **zlib（RFC1950）/ gzip（RFC1952）/
raw deflate（RFC1951）** 兼容的数据流，可被任意标准解压器还原。

## 功能概述

- `src/slz.c` + `src/slz.h`：编码器核心（`slz_init` / `slz_encode` / `slz_finish`），
  支持 gzip / zlib / raw deflate 三种封套与两个压缩级别（0=仅封套、1=压缩）。
- `src/zenc.c` → `zenc`：命令行编码器（`-G`/`-Z`/`-D` 选格式、`-0..-9` 选级别、
  `-l` 循环压测、`-t` 只测不输出）。
- `src/zdec.c` → `zdec`：**gzip 位流 dump/调试器**（逐位打印 BTYPE/BFINAL/码字），
  不是解码器，不输出还原数据——做 round-trip 校验必须另接独立解压实现（如 python zlib）。
- 零第三方依赖：只用 libc 头（`inttypes.h`/`stdio.h`/`string.h` 等），
  `zenc` 额外用 `sys/mman.h`、`sys/ioctl.h` 与（`__linux__` 守卫下的）`linux/fs.h`。

## OHOS 适配

- 构建系统是**裸 Makefile**（无 configure）：`CC` 默认 `$(CROSS_COMPILE)gcc`，
  设备与 CI worker 都没有 gcc，配方必须在 make 命令行显式传 `CC`/`AR`
  （从 `tools.build:compiler_executables` 取，R33 禁止读环境变量）。
- `PLATFORM` 由 `$(CC) -dumpmachine` 推导，clang 下为 `linux` → 构建 `libslz.so.1`
  与软链接 `libslz.so`（非 darwin/aix 分支）。
- **不使用 `make install`**：其 `install-tools` 目标对 `zenc` 执行 `$(STRIP)`，
  HarmonyOS 对可执行文件有 `.codesign` 执行策略，strip 改变布局后签名校验失配报
  EPERM（先例 integrit/E703）；配方在 `package()` 内直接复制产物。
- `slz_adler32_by1/by4` 是**裸累加器**，不做初值归一化：Adler-32 规范初值是 `1`，
  传 `0` 会得到与 zlib 不一致的值（详见知识草稿 `DRAFT-E735`）。
- 上游 v1.2.1 **无任何测试入口**（Makefile 无 `test`/`check` 目标，`tests/` 只是
  3 个数据夹具），功能验证由 `test_package` 消费者断言 + 上游夹具 round-trip 回归承担。

## 依赖关系

- 编译依赖：无（纯 C + libc）
- 运行依赖：无

## 参考资料

- 上游仓库：https://github.com/wtarreau/libslz
- 项目主页：http://www.libslz.org/
- RFC1950（zlib）/ RFC1951（deflate）/ RFC1952（gzip）
