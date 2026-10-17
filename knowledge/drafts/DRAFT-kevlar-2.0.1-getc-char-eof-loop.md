# DRAFT-kevlar-2.0.1-getc-char-eof-loop：C stdio getc/fgetc 返回值用 char 接收时，在 plain-char 为 unsigned 的目标上 EOF 永不可达 → 死循环

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-21
> Source: kevlar 2.0.1 适配（本 PR）
> 对应：`knowledge/drafts/DRAFT-kevlar-2.0.1-getc-char-eof-loop.kv`

## 现象

`kevlar build` / `md2html` / `rst2html` 在 OHOS arm64 目标上挂起（100% CPU），
输出 HTML 文件为空。用 `timeout` 包裹后以 124 退出；插桩发现卡在
`rst_get_file_length()` 的 getc 循环里永不返回。

```c
// kevlar-2.0.1 src/kevlar_rst_to_html.c（修复前）
long rst_get_file_length(char *filename) {
  FILE *infile = fopen(filename, "r");
  long file_len = 0;
  for (char c = getc(infile); c != EOF; c = getc(infile)) {  // ← 死循环
    if (c == '\n') file_len++;
  }
  return file_len;
}
```

## 根因

C 标准规定 plain `char` 的 signedness 由实现定义。OHOS arm64（clang 15）默认
plain char 为 **unsigned**。`getc()` 返回 `int` 类型的 `EOF == -1`；赋值给
`char c` 后 `-1` 截断为 `0xFF`（255），`c != EOF` 恒为真 → 无限循环。

构建主机（glibc x86_64，plain char 为 signed）上 `char c = -1` 恰好等于 EOF，
循环正常结束——所以该 bug 只在目标平台暴露，本地冒烟测试无法发现。

## 方案

把循环变量改为 `int`，保留 `-1 == EOF` 语义，任意平台都正确：

```c
for (int c = getc(infile); c != EOF; c = getc(infile)) { ... }
```

已落地为补丁 `archives/k/kevlar/2.0.1/patches/0002-src-kevlar_rst_to_html.c.patch`，
修复后 `kevlar build`、`md2html`、`rst2html` 全部正常完成。

## 验证

- 修复前：`timeout 15 kevlar build` → 124（挂起）；dist 产物 0 字节
- 修复后：`kevlar build` exit 0，生成 `dist/index.html`（3.7KB）+ `dist/hello-world.html`（3.6KB），Markdown 内容正确渲染为 `<h1>Welcome to kevlar!</h1>`
- W3 本地 CI 模拟通过（.ci-result.json exit_code=0）

## 适用边界

- **适用**：上游代码用 plain `char` 接收 `getc/fgetc/getchar` 等返回 `int`/EOF 的 stdio 函数并与 `EOF` 比较的循环；任何 plain-char 为 unsigned 的目标（OHOS arm64、部分 AArch64 工具链）
- **反例/边界**：与 E419（plain char signedness 改变 INT8 API 数值语义，方案 `-fsigned-char`）根因同域但触发面不同——E419 是数值差异（±256），本条是控制流死循环；本条修复用源码级 `int`，不改库 API/ABI，无需工具链开关
- **不适用**：若循环已用 `int c` 或 `fread`/`memchr` 计数，则无需修复

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | false（知识库无 getc/EOF 死循环条目） |
| causal_duplicate | false（E419 是数值语义差异） |
| trigger_overlap | true（char signedness 根因域，E419） |
| solution_overlap | 部分（E419 用 -fsigned-char，本条用源码 int c） |
| combination_novelty | true（EOF 不可达死循环 + char 接收 getc 新组合） |
| boundary_novelty | true（控制流死循环 vs 数值差异新边界） |
| test_migration_novelty | true（make all + kevlar build 复跑，可跨库迁移） |

关系：`similar_to E419`、`caused_by` 平台 plain-char unsigned 默认、`conflicts_with` 无。
