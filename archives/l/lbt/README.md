# lbt — LTL 到 Büchi 自动机转换器

`lbt`（LTL to Büchi Translator）把**线性时序逻辑（LTL）**公式转换成**广义 Büchi 自动机**，常用于模型检测中表示待验证的性质。

提供两个过滤器（stdin → stdout）：

- **`lbt`**：读取一个 LTL 公式，输出广义 Büchi 自动机。
- **`lbt2dot`**：把 `lbt` 的输出转换成 GraphViz（dot）格式，便于可视化。

## 用法

```sh
echo G p0 | lbt | lbt2dot | dotty -
```

LTL 公式语法（`lbt` 的输入记号）包括：`t`/`f`（真/假）、`p<n>`（命题）、`!`（非）、`&`/`|`（与/或）、`i`（蕴含）、`e`/`^`（等价）、`X`（next）、`F`/`G`（finally/globally）、`U`/`V`（until/release）。

## OHOS 适配要点

- **手写 Makefile**：`lbt` 由 C++ 源码（`Ltl.C`/`LtlGraph.C`/`BitVector.C`/`lbt.C`）编译，`lbt2dot` 由 C 源码（`lbt2dot.c`）编译。
- **C++98**：2001 年的源码使用 `register` 存储类（C++17 已移除），需以 `-std=gnu++98` 编译；无需源码补丁。
- **HTTPS 源**：上游只在明文 HTTP 主机发布，改用 Debian 同版本 `.orig.tar.gz`（HTTPS）并固定 sha256。
- **无三方依赖**。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/lbt` | LTL → Büchi 自动机 |
| `bin/lbt2dot` | 自动机 → GraphViz |
| `share/man/man1/lbt.1`、`lbt2dot.1` | man 手册 |
| `share/doc/lbt/` | 上游 HTML 文档与 ChangeLog/NEWS |

## 参考资料

- 上游主页：<http://www.tcs.hut.fi/Software/maria/tools/lbt/>
- 许可证：GPL-2.0-or-later
