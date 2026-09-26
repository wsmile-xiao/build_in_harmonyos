# psignifit

**心理物理函数拟合与假设检验命令行引擎**（legacy 2.x，Wichmann-lab / bootstrap-software）。

- 纯 C 实现、**零第三方依赖**（只用 C 标准库）。
- 构建系统：源码内手写 `psig-src/Makefile`（无 configure / CMake / autotools）。
- 产物：单个命令行工具 `psignifit`（文本 prefs/data 驱动，支持文件、stdin 与管道输入）。
- 内置引擎自检 `psignifit -t`：内嵌 8×3 数据拟合 Weibull，对 4 个参数金值做 **0.1% 相对误差**判据 + IEEE 浮点行为组。
- 许可：GPL-2.0-or-later；上游 2005 年后停更。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [2.5.6](2.5.6/) | built | 首个 OHOS 适配（aarch64 输入面 + CLI 冒烟选项两处补丁） |

## OHOS 适配要点

详见 [2.5.6/notes.md](2.5.6/notes.md)。

- aarch64 plain `char` unsigned 导致 `fgetc/EOF` 判据失效 → 补丁 0001（Debian `arm64.patch` 同款）。
- 上游无 `--version`/`--help` → 补丁 0002（过 Conan L2 冒烟）。
- 手写 Makefile 的 `CC= gcc` / `OUTDIR= ~/bin` / `LDFLAGS=` 字面量 → make 调用行统一钉死。
