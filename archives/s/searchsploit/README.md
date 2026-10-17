# searchsploit

Exploit Database's CLI search tool. Allows offline searching through a local copy of the Exploit Database for exploits, shellcodes, and papers.

## HarmonyOS Adaptation

### Software Type
Pure bash script tool (not C/C++). No compilation required.

### Dependencies
- bash (system provided)
- GNU coreutils: grep, awk, sed, sort, tr, cut, xargs, wc, head, tail, file
- git (for database updates)

### Patches Applied
- `0001-harmonyos-compatibility.patch`:
  - Fix `grep -P` detection (HarmonyOS grep lists --perl-regexp in --help but doesn't support it)
  - Fix `tput cols` fallback (tput not available on HarmonyOS, use $COLUMNS or default 80)
  - Fix regex compatibility for `grep -E` mode (`\d` → `[0-9]`, `\w` → `[a-zA-Z0-9_]`, `\s` → `[[:space:]]`)
  - Auto-detect script directory in `.searchsploit_rc` instead of hardcoded `/opt/exploitdb`

### Known Limitations
- Clipboard feature (`-p` clipboard copy) requires xclip/pbcopy, not available on HarmonyOS
- `apt`/`brew` update methods disabled (use `git` update via `-u` instead)

### Package Contents vs Full Database

Conan 包仅包含脚本、配置和 CSV 索引文件，**不含 `exploits/` 和 `shellcodes/` 目录下的实际漏洞利用代码**（47,000+ 文件，体积过大）。

| 功能 | 是否可用 | 说明 |
|------|---------|------|
| 搜索 (`searchsploit <terms>`) | ✅ | 只读 CSV 索引，开箱即用 |
| 标题搜索 (`-t`) | ✅ | 同上 |
| JSON 输出 (`-j`) | ✅ | 同上 |
| CVE 搜索 (`--cve`) | ✅ | 同上 |
| 过滤排除 (`--exclude`) | ✅ | 同上 |
| 版本模糊搜索 | ✅ | 同上 |
| 查看路径 (`-p <id>`) | ⚠️ | 能查到元数据，但文件类型识别和复制失效 |
| 镜像复制 (`-m <id>`) | ❌ | 缺少源文件 |
| 查看代码 (`-x <id>`) | ❌ | 缺少源文件 |

**首次使用前**，运行以下命令下载完整漏洞利用数据库：
```bash
searchsploit -u
```
该命令通过 git 从 GitLab 拉取 `exploits/` 和 `shellcodes/` 目录。完成后所有功能均可正常使用。
