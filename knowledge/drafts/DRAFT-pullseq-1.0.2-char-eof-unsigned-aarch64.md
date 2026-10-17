# DRAFT: aarch64 plain char 无符号 → EOF 判定失效 → 单字符读循环无界扩容（GB 级内存失控）

> 状态：DRAFT（pullseq/1.0.2 触发，待 PR 关联）｜severity: P1｜category: c, portability, memory
> 提交窗口：GLM-72｜日期：2026-09-21

## 1. 可复现症状与稳定错误签名

在 OHOS aarch64 真机上运行打包后的 pullseq 消费者冒烟（两记录、共 34 字节的 FASTA 夹具）：

```
smoke: pullseq -n failed rc=143 (Signal 15 )
[memguard] 越线 rss=6438MB (limit=6000MB, app) pid=22567 comm=pullseq
           cmd=.../bin/pullseq -i in.fa -n names.txt   （in.fa 仅 34 字节）
```

特征：**输入 KB 级、内存 GB 级**——进程不崩溃、不报错，只表现为 RSS 线性/指数爬升直到被
OOM 或止损看门狗（SIGTERM → rc=143）终止；同一二进制在有符号 char 平台（x86-64 glibc）
上同输入完全正常。此前 GLM-67 时代的"smoke 喂大输入拖死整机 10.26GB"事件实为同一根因
（当时夹具也不大，被误判为输入规模问题）。

## 2. 根因与最小复现

C 标准：`getc()/fgetc()/getchar()` 返回 **int**（为容纳 EOF=-1）。上游 pullseq 1.0.2
`src/file_read.c:23` 把接收变量声明成 plain char：

```c
char ch;                              /* aarch64 clang: char == unsigned char */
...
while ((ch = getc(fp)) != EOF) {      /* EOF 存入 ch 变 255，255 != -1 永真 */
        ...
        (*lineptr)[buf_pos++] = ch;   /* 行缓冲 realloc 指数扩容，永不停止 */
        if (ch == '\n') break;
        ...
}
```

aarch64 工具链（OHOS clang 等）默认 plain char **无符号**，EOF(-1) 截断为 255，
`ch != EOF` 恒真 → 到达文件尾后循环永不退出，每轮 realloc 翻倍直到内存耗尽。
上游在有符号 char 平台开发，`ch == -1 == EOF` 正常退出，缺陷从不显现。

最小复现：任何 `char ch; while ((ch = getc(f)) != EOF)` 形态的代码在 aarch64 上
对一个无换行/已 EOF 的小文件运行即可复现（无需大输入）。

## 3. 已尝试方案（含失败）

- `ulimit -v 2097152` 冒烟护栏：**无效**——本机 busybox ash 不支持 `ulimit -v`，
  静默失败（`2>/dev/null || true` 掩盖）；且不解决缺陷本身。
- 归因"输入过大/消费者测试设计不当"（GLM-67 时代结论）：**误判**——本窗用 34 字节
  夹具复现 6.4GB RSS，证明与输入规模无关。

## 4. 最终方案与真实验证

单行修复（patches/0001-file-read-int-ch-eof.patch，全源码唯一 getc 站点）：

```c
int ch;                               /* C 标准口径：接收 getc 返回值一律 int */
```

真实验证（OHOS aarch64 真机，2026-09-21）：

- 修复前：34 字节输入 → RSS 6.4GB+（memguard 止损，rc=143），conan-verify G2 FAIL；
- 修复后：conan-verify 全绿（G0–G4、L2/L4/L5 PASS），消费者冒烟 2 场景/6 断言全过，
  整轮验证 memcap 实测进程组峰值 RSS **197MB**（预算 2500MB），用时 42.7s。

备选（未采用）：编译期 `-fsigned-char` 强制有符号 char 可整包消除此类缺陷，
但会掩盖其它 char 符号性依赖，逐点改 int 更符合 C 标准口径。

## 5. 适用范围 / 反例 / 解除条件 / 风险

- 适用：aarch64/ARM 工具链上构建的、逐字符读文件或流的 C 程序（文本/FASTA/CSV/
  配置解析器、CLI 工具）；任何以 char 接收 `getc/fgetc/getchar` 返回值的读循环。
- 反例：已用 int 接收的代码无此问题；C++ `istream::get()` 返回 int_type 无此问题；
  MSVC（char 有符号）不复现。
- 解除条件：源码修复（int 接收）或编译期 `-fsigned-char`。
- 风险：症状是资源失控而非断言失败，容易被误报为"测试输入过大/测试设计不当"，
  若据此缩小测试输入或跳过冒烟，缺陷会潜伏到用户侧。

## 6. 查重与新增价值说明

- 四范围查重（知识图谱/E 族/既有草稿/家族条目）：E011/E386 家族为 shell/getcwd/
  CONFIG_SHELL 类环境机制，E216 为 CMakeDeps include 传播问题，均与本条
  （C 语言 char 符号性 + EOF 判定）机制不同；知识库无同族条目命中。
- 新增价值：a) 把"小输入大内存"这一反直觉症状与 char/EOF 机制建立因果；
  b) 给出可 prescan 的代码模式（`char ch;` + `= getc(`）供工具自动预扫描；
  c) 记录 `ulimit -v` 在 busybox ash 静默失效的事实，防止护栏误依赖；
  d) 纠正历史误因（10.26GB 事件归因输入规模）。
