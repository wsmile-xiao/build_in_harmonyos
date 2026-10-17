# xe

> 逐参数构造并执行命令的工具（xargs/apply 的现代替代）。

## 简介

`xe` 从标准输入（或 `-f` 文件、`-a` argv）读取参数，按需构造命令行并执行：

- 默认每行一个参数，执行一次命令；`-N` 控制每次传入的参数个数（`-N0` 表示一次全传）。
- `{}` 作为占位符在命令中原样替换；`-I` 可自定义占位符/前缀。
- `-0` 读取 NUL 分隔输入；`-n` 干跑只打印命令；`-s` 走 shell；`-j` 并行。
- 与 `xargs` 不同，默认不经过 shell，参数原样传给 `execvp`，避免转义问题。

## OHOS 适配要点

- 单文件 C 程序，无依赖，OHOS clang 直接编译。
- 上游 TAP 测试（`t/*.t`）通过设备 Perl 自带的 `prove` 运行，共 63 条断言。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | — | 仅需标准 C 库 |

## 功能验证

```bash
printf 'a\nb\nc\n' | xe echo
printf '1\n2\n3\n4\n5\n' | xe -N2 echo
printf '1\n2\n3\n' | xe echo a {} x
```

## 参考

- [源码仓库](https://github.com/leahneukirchen/xe)
