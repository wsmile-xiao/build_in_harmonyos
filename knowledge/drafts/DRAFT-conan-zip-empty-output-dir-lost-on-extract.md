# DRAFT：zip 归档携带的"空输出目录"解压即丢 → makefile 链接期 cannot open output file

> 来源：simh/3.8.1（上游 V3.8-1 源码 zip，`BIN = BIN/`）· 2026-09-27 适配实测

## 现象

conan create（或直接 make）时全部 C 文件编译成功，链接第一个模拟器即失败：

```
ld.lld: error: cannot open output file BIN/pdp1: No such file or directory
clang: error: linker command failed with exit code 1
```

且每个 target 重复同类报错（simh 实测 0/26 全灭）。

## 根因

- zip 以"条目"存储；**空目录是一个独立的纯目录条目**，部分下载/解压链路
  （Conan `get()`、CI pre-download、校验工具）会丢弃它 → 解压后 `BIN/` 不存在。
- 上游 makefile 习惯输出目录"天然存在"：`BIN = BIN/`，链接规则 `-o BIN/<sim>`，
  **没有任何 mkdir**。
- 于是失败发生在链接写目标文件的瞬间，且逐 target 重复——容易被误判为
  编译器/链接器问题，实际只是目录不存在。

旁证（判定方法）：`unzip -l 归档名 | grep -c 'BIN/'` → 0（清单里根本没有目录条目）。

## 为什么集中出现在 zip 源

tar 格式把目录也作为成员保留，tar.gz 源解压后空目录通常还在；
**zip 源**才高发。遇到 `cannot open output file <dir>/<target>` 先查：
解压后的输出目录在不在、归档清单里有没有目录条目。

## 实测证据（simh 3.8.1，本机交叉编译对照实验）

| 实验 | 结果 |
|---|---|
| 不预建 `BIN/`（等价于解压后现状） | 0/26，全部 `cannot open output file BIN/<sim>` |
| `os.makedirs(<source>/BIN)` 后再 make | 26/26 成功 |

真机 shadow CI（2026-09-27）：预建后 26/26，L0-L5 全 pass。

## 处置

`conanfile.build()` 里、调用 make **之前**预建输出目录（通用、零上游改动）：

```python
os.makedirs(os.path.join(self.source_folder, "BIN"), exist_ok=True)
self.run('make CC="..." LDFLAGS="-lm" -j1', cwd=self.source_folder)
```

不推荐：打补丁改上游 makefile（改动面大、不可复用）；或指望上游自己 mkdir
（该代际 makefile 没有这个逻辑）。

## 影响面

- 所有"zip 源码归档 + 手写 makefile + makefile 不自建输出目录"的组合。
- 判据：makefile 里有 `XXX = dir/` 之类的输出目录变量且规则直接 `-o $(XXX)target`；
  解压后该目录不存在。

## 查重边界

- `DRAFT-csstidy-1.4-zip-backslash-source-drop`：zip 内反斜杠路径致**源文件**丢失——不同因不同果。
- `DRAFT-conan-downloader-xgzip-content-encoding`：Content-Encoding 破坏**归档字节流**——下载层问题。
- 避坑指南 §6.2：只提醒 strip_root 需按实际归档检查，未覆盖"空目录条目丢失"。
- 全库检索 `cannot open output`：仅命中本条 → 无重复，为独立新条目。
