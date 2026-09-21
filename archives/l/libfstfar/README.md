# libfstfar

libfstfar 是 OpenFst 的 **FAR（FST ARchive）扩展库**：把多个 FST 装进单一档案文件，
并提供在档案上工作的命令行工具链。FAR 是 OpenGrm / 语音识别 / 机器翻译流水线里
分发与批处理 FST 模型的标准容器格式。

## 描述

OpenFst 是开源的加权有限状态转换器（FST）库。FAR 扩展提供三种档案形态：

| 档案类型 | 载体 | 特点 |
|----------|------|------|
| `sttable` | 单文件（`STTable`） | 结尾带索引表，可按 key 随机访问 |
| `stlist` | 单文件（`STList`） | 顺序列表，写一次读一遍，最省内存 |
| `fst` | 一个 FST 一个文件 | 目录即档案 |

本包交付 FAR 扩展库（`libfstfar` / `libfstfarscript`）及其头文件，并随包提供
`far*` 命令行工具与 openfst 核心 `fst*` 工具。

## 版本列表

| 版本 | 状态 | 编译日期 | 测试状态 |
|------|------|----------|----------|
| 1.8.4 | built | 2026-09-20 | 上游 10 用例 10/10 通过；鸿蒙特有测试 14/14 通过（另有 8 项包内 CLI 检查因 `--disable-bin` 记 NOT_RUN） |

## 核心功能

本包交付 **FAR 档案容器库**本身：`fst::FarWriter` / `fst::FarReader` /
`fst::STTableFarWriter` / `fst::STListFarWriter` / `fst::STTableReader` /
`fst::STListReader` 等公共 API 与 `fst::IsSTTable` / `fst::IsSTList` 两个归档嗅探函数，
支持 STTable（可随机访问）与 STList（顺序）两种档案形态的读写。

> **命令行工具不在本包交付面内**：本配方按 `--disable-bin` 构建（理由见
> `archives/l/libfstfar/1.8.4/notes.md`「为什么是 `--disable-bin`」）。需要
> `farcreate` / `farinfo` / `farextract` / `farcompilestrings` / `farprintstrings` 等
> `far*` 工具或 `fstcompile` / `fstprint` 等 `fst*` 工具时，请使用 **`openfst/1.8.4`**
> （或 `libfst` / `libfstconst`）——与本包同源同版本。

## 鸿蒙平台适配

复用 openfst 1.8.4 已验证的平台补丁（与同 tarball 兄弟包 `libfst` / `libfstconst` 相同）：

1. `config.guess` — 识别 `HarmonyOS`，产出 `aarch64-unknown-linux-ohos`（E007）
2. `config.sub` — 接受 `linux-ohos*` 三元组（E007）
3. `configure` — 生成临时目录的 `umask 077` → `022`（HMDFS 权限边界，E011）
4. `src/lib/flags.cc` — 显式 `--help` / `--helpshort` 返回 0 而非 1

编译要点：

- autotools 构建，`--enable-far` 单独启用本扩展（上游 `configure.ac` 默认 `no`，
  不显式打开则 `src/extensions/Makefile.am` 的 `HAVE_FAR` 为空、far 子目录根本不进构建）；
  `--disable-bin` 显式关掉 `fst::script` 与全部命令行工具（子库交付面）
- 默认 **shared**（`-o libfstfar/*:shared=False` 可切静态）：openfst 的 FST 类型注册表由
  `REGISTER_FST` 静态对象在**加载时**注册，静态链接会被链接器整块剔除 → `Fst::Read`
  回退 `dlopen` 假败（`notes.md` 问题 2 有完整实测与判据）
- 无外部库依赖，运行时仅需 `libc++_shared.so` 与 `libc.so`

## 依赖关系

- 编译依赖：无
- 运行时依赖：`libc++_shared.so`（clang C++ 运行时）、`libc.so`（系统库）
- 与同 tarball 兄弟包的关系：`libfst` / `libfstconst` / `libfstngram` / `libfstlookahead`
  与本包都由 `openfst-1.8.4.tar.gz` 构建，各自开一个扩展开关；本包额外声明
  `cpp_info.libs = ["fstfar", "fst"]`（`libfstfar.la` 的 `LIBADD` 依赖 `libfst.la`，
  静态链接时需一并给出）

## 使用示例

```bash
# 1) 文本 FST -> 二进制 FST
fstcompile in.txt in.fst

# 2) 合成 FAR 档案（STList 形态）
farcreate --far_type=stlist --key_prefix=entry_ in.fst model.far

# 3) 查看档案信息
farinfo model.far

# 4) 按 key 抽出条目
farextract --keys=entry_in model.far

# 5) 字符串语料 -> FAR
farcompilestrings --symbols=words.syms --unknown_symbol='<unk>' corpus.txt strings.far
farprintstrings strings.far
```

## 参考资料

- 官网：https://www.openfst.org/
- 源码：https://openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.4.tar.gz
- FAR 文档：https://www.openfst.org/twiki/bin/view/FST/FarDoc

---

*最后更新：2026-09-20*
