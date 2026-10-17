# E6401 草稿：无扩展名 POSIX shell 主程序被误判为 other

## 错误特征
slay 3.0.2 源码根只有无扩展名 `slay`（首行 `#!/bin/sh`）及手册，既无 Makefile 也无 `.sh` 文件；`detect_language()` 返回 `detected_language=other`、`source_stats=无源文件可统计`。此处预先调用只读检测函数，**未**运行会写错误终态的 `lang-preflight`。

## 根因与适用范围
`scripts/ohc/lang_detect.py` `_source_stats()` 根据文件扩展名计数并排除 bash；`_manifest_scan()` 在无构建文件时返回 None，最终退化为 other。适用于无扩展名的 POSIX 脚本主程序且无构建 manifest 的包。已有 `DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect` 讨论 install-only Makefile 被误判成 **c**，而本条是无 Makefile 被误判成 **other**，签名和根因分支不同；主编可考虑合并扩展已有草稿。

## 处理与验证
先设 `SRC=/absolute/path/to/source`，确认 `head -n 1 "$SRC/slay"` 为 `#!/bin/sh` 且无 C/C++ 目标后按当前接受的纯脚本路径直接安装；`sh "$SRC/slay" --help` 可安全调用，退出码 127 并打印 usage。不要为了迁就检测器伪造 `.sh` 扩展名、添加虚假 C 文件或修改 `scripts/`；不对真实用户名做破坏性进程测试。建议主编将无扩展名且含 shebang 的主程序计入主体检测，并让 shell-only 案例可通过预检。
