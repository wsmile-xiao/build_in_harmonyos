# miniasm 0.3 适配笔记

## 编译环境
- 构建系统: 上游 Makefile；本仓库直接编译（custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `0.3` 对应上游 git tag `v0.3`。
- 源码：`https://codeload.github.com/lh3/miniasm/tar.gz/refs/tags/v0.3`
  （官方 GitHub codeload 主机；`github.com/.../archive/...` 作为备份 URL，字节一致）
  sha256 `9b688454f30f99cf1a0b0b1316821ad92fbd44d83ff0b35b2403ee8692ba093d`。

## 编译步骤

上游 Makefile 用 gcc、`LIBS=-lm -lz -lpthread`。本仓库改为按源文件逐个编译，
并显式传入 Conan zlib 的 include/lib：

```sh
clang -c -O2 -Wall -I <src> -I <zlib-include> -o <build>/<name>.o <src>/<name>.c   # 8 个源文件
clang -O2 -o <build>/miniasm <objs> -L <zlib-lib> -lz -lm
```

- **不含 `-lpthread`**：OHOS 用 bionic，pthread 符号在 libc 中，显式 `-lpthread` 反而可能找不到。
- 需要 zlib：`conanfile.py` 中 `self.requires("zlib/1.3.1")`。

`package()` 安装 `bin/miniasm`、`share/man/man1/miniasm.1`、`licenses/LICENSE.txt`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试 | Makefile 只有 all/miniasm/minidot/clean/depend，无 check/test | 自构造确定性的 all-vs-all PAF 做端到端功能测试 |
| 2 | zlib 依赖 | paf.c 用 gzopen/gzread 读 PAF | Conan `zlib/1.3.1`，编译/链接显式指定其 include/lib |
| 3 | OHOS 无独立 pthread | bionic 把 pthread 并入 libc | 不链接 `-lpthread`，只保留 `-lm -lz` |
| 4 | 命令行工具需要声明 | 产物含 `bin/` | 软件级 `commands.json`（R38） |
| 5 | `source()` 偶发被跳过 | 某些 `conan create` 路径在 cache 源码目录已存在时跳过 `source()`，导致源码目录为空 | `build()` 内加兜底：源码缺失时自行 `download`+`unzip` |
| 6 | 小型合成图被剪枝为空 | 默认 `max_ext=4` 会剪掉微小 unitig | 功能测试用 `-c 1 -e 0` 保留微小图 |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

- zlib/1.3.1（Conan 制品仓，已发布）

## 验证结果

```bash
./miniasm -V                 # -> 0.3-r179
./miniasm -f reads.fa reads.paf   # 输出 GFA，含 S 段
./miniasm -p paf reads.paf        # 输出重叠记录
./miniasm -p bed reads.paf        # 输出区间
# 6 项消费者检查全部通过
```

`conan create miniasm/0.3` 退出码 0。

## 注意事项

- miniasm 0.3 无上游测试；测试由本包补充（自构造 PAF）。
- 任务同时提到 minidot，本次只打包 `miniasm` 主程序。
