# kgb — .kgb 高压缩比归档工具

`kgb` 是 **KGB Archiver** 的 POSIX 命令行版本，基于 Matt Mahoney 的 **PAQ6** 压缩器，提供极高的压缩率（代价是较高的内存与 CPU 占用）。它可以压缩、解压 `.kgb` 归档。

## 主要功能

- **压缩**：`kgb -<m> archive.kgb files <@list_files>`，其中 `-m`（0–9）选择内存/压缩级别（`-0` 最快 2 MB，`-9` 最强 1616 MB，默认 `-3` 18 MB）。
- **解压**：`kgb archive.kgb`，将归档内容解压到当前目录。
- **查看目录**：`more < archive.kgb`（归档头部以文本形式列出文件名与大小）。

## OHOS 适配要点

- **单文件 C++ + 手写 Makefile**：无 `configure`，`make CXX=clang++ LDFLAGS="" -j1` 即可；`CXXFLAGS` 沿用上游默认（`-std=c++0x -O3 -DPROGNAME='"KGB_arch"'`）。
- **无三方依赖**：仅需 C++ 标准库。
- **归档格式与 `PROGNAME` 绑定**：归档头写入 `PROGNAME`（Makefile 的 `MAGIC`，默认 `KGB_arch`）；移植时保持该宏不变，保证与既有 `.kgb` 归档兼容。
- **无上游测试**：上游 Makefile 仅有 `all`/`clean`；由 `test_package/test_kgb.sh` 补齐消费者断言，包括字节级 round-trip 与 Debian 自带测试所用的确定性 `gpl.kgb` 校验和。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/kgb` | 归档器可执行文件 |
| `licenses/LICENSE` | GPL-2.0 许可证 |
| `share/doc/kgb/README.md` | 上游说明 |

## 参考资料

- 上游仓库：<https://github.com/FS-make-simple/kgb/>
- 原作者：Tomasz Pawlak（KGB Archiver），基于 PAQ6（Matt Mahoney）
- 许可证：GPL-2.0-or-later
