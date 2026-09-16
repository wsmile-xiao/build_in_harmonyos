# minimap 0.2 适配笔记

## 编译环境
- 构建系统: 上游 Makefile；本仓库直接编译（custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `0.2` 对应上游 git tag `v0.2`（上游已归档）。
- 源码：`https://codeload.github.com/lh3/minimap/tar.gz/refs/tags/v0.2`
  （官方 codeload；`github.com/.../archive/...` 作为备份 URL，字节一致）
  sha256 `cfcf77cfe2d8d64b16ea60e0139363190eca4853da9dca9d872c38fe80bf5d68`。

## 编译步骤

上游 Makefile 用 gcc、`LIBS=-lm -lz -lpthread`，并产出 `minimap` 与
`libminimap.a`。本仓库按源文件逐个编译并显式传入 Conan zlib：

```sh
# 库对象：kthread misc bseq sketch sdust index map
clang -c -O2 -Wall -I <src> -I <zlib-include> -o <build>/<name>.o <src>/<name>.c
llvm-ar rcs <build>/libminimap.a <objs>
# CLI
clang -c -O2 -Wall -I <src> -I <zlib-include> -o <build>/main.o <src>/main.c
clang -O2 -o <build>/minimap <build>/main.o -L <build> -lminimap -L <zlib-lib> -lz -lm
```

- **不含 `-lpthread`**：OHOS bionic 把 pthread 并入 libc。
- `package()` 安装 `bin/minimap`、`lib/libminimap.a`、`include/{minimap.h,bseq.h,kseq.h}`、
  `share/man/man1/minimap.1`、`licenses/LICENSE.txt`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试 | 无 `tests/`，Makefile 仅 all/minimap/extra/clean/depend | 合成 target/query FASTA，做 CLI + 库两级验证 |
| 2 | zlib 依赖 | index/bseq 等用 gzopen/gzread | Conan `zlib/1.3.1`，编译/链接显式指定 |
| 3 | OHOS 无独立 pthread | bionic 把 pthread 并入 libc | 不链接 `-lpthread` |
| 4 | 头文件依赖 | `minimap.h` include `bseq.h`；示例还用 `kseq.h` | 三个头文件一并打包到 `include/` |
| 5 | `source()` 偶发被跳过 | 某些 `conan create` 在 cache 源码目录已存在时跳过 `source()` | `build()` 内加“源码缺失则自行下载”兜底 |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

- zlib/1.3.1（Conan 制品仓，已发布）

## 验证结果

```bash
./minimap -V                                  # -> 0.2-r123
./minimap -k7 -w4 -L10 -c1 target.fa query.fa # 出 hit
./minimap -d target.mmi target.fa && ./minimap -l target.mmi query.fa  # 出 hit
# 库消费者：链接 libminimap.a 建索引并映射，命中数 > 0
# 共 5 项检查全部通过
```

`conan create minimap/0.2` 退出码 0。

## 注意事项

- 上游已归档；按指定旧版本（v0.2）编译。
- 同时是工具与库；软件级 `commands.json` 声明为工具。
