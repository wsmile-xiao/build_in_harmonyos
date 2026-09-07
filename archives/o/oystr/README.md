# oystr

`oystr` 是递归搜索文件和目录中子字符串的命令行工具，安装后可执行文件为 `oy`。

## 用法

```sh
oy needle file
printf '%s\n' 'stream needle match' | oy needle
```

Conan reference: `oystr/0.2.0`。该适配面向 OpenHarmony aarch64，使用 Conan 的 `argparse/3.2` 和 `fmt/12.2.0`，产物类型为 `application/tool`。
