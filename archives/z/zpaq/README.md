# zpaq

**ZPAQ 开放压缩标准的参考实现**（journaling 归档器，Matt Mahoney，7.15 / 2016-08-17）

zpaq 是面向"用户级增量备份"设计的日志式归档器：支持 AES-256 加密、
5 级多线程压缩、内容感知的文件片段级去重，归档格式自描述（后续版本可在
不破坏兼容性的前提下扩展）。默认压缩级别通常比 zip 更快且压缩率更好。

## 用法

```bash
# 创建/追加归档（日志式：只新增变化的文件，旧版本保留）
zpaq add archive.zpaq files...

# 列表（含各版本、去重与压缩记账）
zpaq list archive.zpaq

# 解压（-to 可改名/改目录；缺失的输出目录会自动创建）
zpaq extract archive.zpaq files... -to out...

# 回滚到第 N 个版本
zpaq extract archive.zpaq file -until 1 -to old-copy
```

| 命令 | 说明 |
|------|------|
| `add` / `a` | 创建或追加（日志式，保留历史版本） |
| `extract` / `x` | 解压（`-to` 改名、`-until` 回滚、`-force` 覆盖） |
| `list` / `l` | 列表（版本数、片段数、去重与压缩比） |
| `-method N` | 选择压缩级别（5 档多线程；`-method 14` 为默认之一） |

> zpaq 7.15 **没有** `--version` / `--help` 开关：任何未识别参数都会打印
> 版本横幅 + 用法并以退出码 1 结束。退出码不是"错误一律 0"：`x <不存在的归档>`
> 返回 2，而 `add <归档> <不存在的输入路径>` 只打诊断、仍返回 0 —— 所以脚本断言
> 要"诊断文本 + 退出码"一起看。版本号体现在每次运行打印的
> `zpaq v7.15 journaling archiver` 横幅里。

> 目录结构：本仓的归档元数据放在**版本级** `7.15/manifest.yaml`；软件级目录
> （本目录）只放 `README.md` 与 `commands.json`，不设软件级 manifest.yaml
> —— 与仓内既有约定一致。

## OHOS 适配

- **构建**：上游 readme 的单条命令（`g++ -O3 -march=native -Dunix zpaq.cpp
  libzpaq.cpp -pthread -o zpaq`）的一次等价调用；上游 `Makefile` 只是把
  它包成 `zpaq` 目标。
- **必须 `-DNOJIT`**：`libzpaq.cpp` 的 `ZPAQL::assemble()` 在运行期生成
  x86-32/x86-64 机器码并跳转执行；aarch64 上不加该宏可以编译、也能压缩，
  但解压时立即 `Illegal instruction (core dumped)`。
- **`-static-libstdc++`**：OHOS SDK 的 `libc++_shared.so` 是链接器脚本，
  musl 加载器无法解析；静态烘焙后产物 `DT_NEEDED` 只剩 `libc.so`。
- **零外部依赖**：AES-256 / SHA-1 / SHA-256 / scrypt / divsufsort 全部在
  `libzpaq.cpp` 内自实现，系统侧只需要 pthread。
- **适配分支/PR**：`feat/zpaq-7.15`；详细踩坑见 `7.15/notes.md`，
  逐项测试台账见 `7.15/reports/test-report.md`。

## 依赖

无（零 Conan 依赖）。

## 参考

- 上游仓库：zpaq/zpaq（GitHub，作者 Matt Mahoney 的官方仓库）
- 格式说明：ZPAQ 开放标准（`zpaq.pod` 随源码分发）
- 同上游另有 `libzpaq/0.01`（2009 年 level 0 实验版，单文件、需 min.cfg/max.cfg）
