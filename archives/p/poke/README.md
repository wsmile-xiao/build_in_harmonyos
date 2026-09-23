# poke

**GNU poke — 结构化二进制数据可扩展编辑器**

GNU poke 是一个交互式编辑器，用于处理任意结构的二进制数据：ELF 文件、分区表、文件系统镜像、数据库文件……核心是 **Poke 语言**（描述/操作结构化数据的领域专用语言）与 pickles（数据结构的可复用描述库）。软件包含 `poke`（REPL/CLI）、`pokefmt`（模板处理器）、`libpoke`（库）与一组 pickles。

## 用法

```bash
# 交互式 REPL
poke

# 非交互求值
poke --color=no -c 'printf "%v\n", 0xff & 0x0f;'
poke --color=no -s script.pk     # 执行 .pk 脚本

# 加载 pickle 后操作数据
poke --color=no -s analyze.pk

# pokefmt：处理含嵌入 Poke 代码的模板（模板走 stdin，Poke 代码走参数）
echo 'tool: %(2 + 3)%' | pokefmt
```

Poke 语言注意：位移运算符是 `<<.` 与 `.>>`（带点）；printf 使用 Poke 格式标签（`%v`、`%u16x` 等，无 C 的 %d）。

## OHOS arm64 适配要点

- 上游 5.0 已移除 Guile 支持，依赖仅 bdw-gc + readline（+ 传递依赖 ncurses）
- libnbd 在 OHOS 不可用，configure 传 `--disable-libnbd`
- `makeinfo` 缺失：tarball 预构建文档 + 时间戳钉扎 + `MAKEINFO=true` 兜底
- 运行时数据经环境变量重定位：`POKEDATADIR`/`POKECONFIGDIR`/`POKEPICKLESDIR`/`POKEFMTAPPDIR`

详见版本目录 [5.0/notes.md](5.0/notes.md)。

## 已知限制（5.0）

- DejaGnu（runtest/expect/tclsh）在 OHOS 不可用：上游 .exp 套件未执行，以 poke.libpoke C 测试 181 项 + test_package 冒烟代偿
- OHOS 上 stdin 管道 REPL 模式静默无输出，脚本化须用 `poke -c` / `poke -s`
- bin/ 下 pk-strings 等 4 个辅助脚本 shebang 硬编码 prefix=/，重定位场景需调整
- poke 5.0 pickles 无 elf.pk

