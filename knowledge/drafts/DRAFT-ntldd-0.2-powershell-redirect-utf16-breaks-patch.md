# PowerShell `>` 重定向生成 UTF-16 补丁文件：git apply 报 "No valid patches in input"

> 草稿（DRAFT）。与同目录 `DRAFT-ntldd-0.2-powershell-redirect-utf16-breaks-patch.kv` 成对。

## 现象

在 Windows 宿主上用 PowerShell 生成补丁：

```powershell
git diff --cached HEAD > ..\0001-xxx.patch   # ❌
```

随后校验补丁时失败，且报错非常有误导性：

```text
error: No valid patches in input (allow with "--allow-empty")
```

`git apply --check` 退出码 128，`git apply` 同样失败。文件大小看起来正常，但内容
每字节后跟 `\x00`（UTF-16LE BOM `FF FE` 开头）。

## 根因

Windows PowerShell 5.1 的 `>` / `Out-File` 默认编码是 **UTF-16LE**。git 的补丁
解析器只认 8-bit 文本，把 UTF-16 当成无有效 hunk 的输入，于是报
"No valid patches in input"——**不是补丁内容有问题，是文件编码坏了**。
`type` 某些查看器能"正常"显示，更具迷惑性。

## 正确做法

生成补丁（或任何要进 git 的文本工件）时：

```powershell
# 首选：git 原生输出（无编码转换）
git diff --cached HEAD --output=..\0001-xxx.patch

# 次选：显式无 BOM UTF-8
git diff --cached HEAD | Out-File -Encoding utf8NoBom ..\0001-xxx.patch   # PS7
git diff --cached HEAD | Set-Content -Encoding Ascii ..\0001-xxx.patch    # PS5.1 兜底（纯 ASCII 补丁）
```

快速自检编码：

```powershell
$bytes = [IO.File]::ReadAllBytes("0001-xxx.patch")[0..1]
$bytes   # FF FE = UTF-16LE（坏）；2D 64 / 其它 ASCII = 正常
```

同类陷阱：`git hash-object`、`conan inspect` 等读文件的工具也会被 UTF-16 破坏；
从 PowerShell 向设备传 base64 时 `Set-Content -Encoding ASCII` 才安全。

## 查重与边界

- E666 是 refresh-patch.sh 不支持 tar.xz（脚本能力），本条是宿主 shell 重定向
  编码问题，不同层。
- 避坑指南讲过 PowerShell 文本管道破坏二进制 tar；本条是它的"文本版"——连
  纯文本补丁都会被默认编码毁掉。

## 证据

ntldd/0.2（2026-09-29，Windows 宿主）：

- `git diff --cached HEAD > patch` 生成 586 行补丁，`git apply --check` 报
  "No valid patches in input"（exit 128）；
- 改用 `git diff --cached HEAD --output=patch` 重新导出后，同一工作树
  `git apply --check` 与 `git apply` 均通过，补丁随后在真机 Conan source()
  阶段成功应用。
