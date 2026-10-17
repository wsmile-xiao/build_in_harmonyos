# zerofree

`zerofree` —— 清零 ext2/3/4 文件系统中**未分配（空闲）块**的命令行工具。

## Description

虚拟机磁盘镜像常见的工作流是：删除文件 → 文件系统里出现大量空闲块 → 但这些空闲块在镜像里仍是非零数据 → 镜像压缩（`gzip`/`zstd`）或稀疏化（`qemu-img convert`）效果很差。

`zerofree` 直接操作块位图，把每个空闲块重写成全零（可用 `-f` 指定填充值），从而让后续压缩/稀疏化真正生效。

- `zerofree [-n] [-v] [-f fillval] filesystem`
- `-n` 试运行（只统计不写入）、`-v` 输出进度与 `modified/free/total` 汇总

## Project URL
https://frippery.org/uml/

## License
GPL-2.0-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 1.1.1
- **构建系统**: 纯 Makefile（无 configure / 无 autotools）
- **编译器**: clang
- **依赖**: `e2fsprogs/1.47.4`（提供 `ext2fs` component）

### 适配要点

1. **Makefile 的编译器与链接参数**：上游 Makefile 是

   ```make
   CC=gcc
   all: zerofree.c
   	$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs
   ```

   `CC=gcc` 是普通赋值，命令行可覆盖；但链接行只有 `$(CFLAGS)`，交叉工具链无法把依赖包的 `-I`/`-L` 传进去。补丁 `0001` 把 `CC=gcc` 改成 `CC?=gcc`，并让链接行接受 `$(CPPFLAGS)`/`$(LDFLAGS)`/`$(LDLIBS)` —— `-lext2fs` 刻意留在 `$(LDFLAGS)` 之后、`$(LDLIBS)` 之前，保持静态链接顺序正确。

2. **libext2fs 复用已发布的 e2fsprogs**：本包 `requires("e2fsprogs/1.47.4")`，用 `package_folder` 拼 `-I`/`-L`，不重复携带 e2fsprogs。e2fsprogs 默认静态发布，静态链接还需 `-lcom_err -luuid`。

3. **不用 `make install`**：上游没有 install 目标，构建沙箱也没有 GNU coreutils `install`，`package()` 直接拷贝产物。

### 验证

`test_package/test.sh` 使用**配方自带的真实 ext2 镜像夹具**（1 MiB = 1024 块 × 1 KiB，970 个空闲块，其中空闲块被预先写入非零脏数据）：

- 参数契约：无参数 / 未知选项 / `-f 999` 超范围 / `-f abc` 非数字 / 缺失镜像，五种都必须非零退出并给出对应诊断；
- 干跑 `-nv` 必须报告正确的几何信息（1024 块 / 970 空闲）且**确实发现脏空闲块**，否则夹具就是空转；
- 真实运行后再用 `-nv` 复核：`modified` 必须归零、空闲块数不变；
- `-f 255` 走一遍非零填充值路径，断言全部 970 个空闲块都被写成非零。

断言数由 `test.sh` 自报（`[test] N/N assertions passed`），与日志里 `[ok]` 行数恒等。
