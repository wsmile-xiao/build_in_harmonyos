# yydecode

**yEnc / uuencode / Base64 解码命令行工具**

yydecode 最初是 Usenet 上 yEnc 编码二进制的解码器。自 0.2.8 起，它也支持
标准 uuencode 与 Base64 [RFC2045] 编码输入，可作为 `uudecode` 的直接替代。

## 用法

```bash
yydecode [-b|--write-broken] [-r|--remove-broken] [-e|--evil-filenames]
         [-f|--force-overwrite] [-l|--large-parts] [-o|--output-file=FILE]
         [-D|--directory=DIR] [-v|--verbose] FILE ...

yydecode --version
yydecode --help
```

| 选项 | 说明 |
|------|------|
| `-o, --output-file=FILE` | 将输出写入指定文件（`-` 表示 stdout） |
| `-D, --directory=DIR` | 将输出文件写入指定目录 |
| `-f, --force-overwrite` | 覆盖已存在的输出文件 |
| `-b, --write-broken` | 允许写出损坏的（CRC 校验失败）数据 |
| `-r, --remove-broken` | 删除损坏的部分 |
| `-l, --large-parts` | 支持大于 400MB 的部分 |
| `-e, --evil-filenames` | 使用输入文件中出现的原始文件名 |
| `-v, --verbose` | 输出详细过程信息 |

示例：

```bash
# 解码若干分卷
yydecode msg-1.txt msg-2.txt msg-3.txt

# 从管道读取
cat msg-*.txt | yydecode
```

## 构建

- 构建系统：autotools（`configure` + `make`）
- 许可证：GPL-2.0-or-later
- 上游：https://sourceforge.net/projects/yydecode/
- 源码：`yydecode-0.2.10.tar.gz`（官方发布点）

## 构建产物

- `bin/yydecode` — yEnc/uuencode/Base64 解码命令行工具（无可链接库）

## 依赖

无第三方依赖（仅 libc）。

## OHOS 适配

- 补丁 `0001-configure-hmdfs-umask.patch`：`config.status` 的临时目录创建在
  HMDFS 上需 `umask 022`（`umask 077` + `mktemp -d` 生成的目录不可写）
- `package()` 直接复制可执行文件（上游 `make install` 依赖的 `install -c`
  在 OHOS 构建环境中复制成功后仍返回非零）
