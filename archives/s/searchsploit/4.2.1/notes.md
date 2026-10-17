# searchsploit 4.2.1 适配笔记

## 软件性质
searchsploit 是纯 Bash 脚本工具（非 C/C++），来自 Offensive Security 的 Exploit Database 项目。
版本 4.2.1，约 600 行 bash 脚本 + CSV 数据库（47K exploits + 1K shellcodes）。

## 鸿蒙适配要点

### 1. grep -P 检测修复
鸿蒙 GNU grep 3.12 在 `--help` 中列出 `--perl-regexp`，但实际编译时禁用了 PCRE 支持。
原脚本通过检查 `grep --help | grep --perl-regexp` 判断是否支持 -P，导致误判。
修复：改为实际执行 `echo test | grep -P "test"` 检测。

### 2. tput cols fallback
鸿蒙无 tput 命令，原脚本用 `$( tput cols )` 获取终端宽度会失败。
修复：添加 fallback，优先用 $COLUMNS，默认 80。

### 3. 正则表达式 -E 兼容
grep -P 不支持后回退到 -E，但 -E 模式不识别 `\d`/`\w`/`\s` 转义。
修复：`\d`→`[0-9]`，`\w`→`[a-zA-Z0-9_]`，`\s`→`[[:space:]]`，`\-`→`-`。

### 4. 配置文件路径自动检测
原 `.searchsploit_rc` 硬编码 `/opt/exploitdb`，改为用 BASH_SOURCE 自动检测脚本目录。

## 打包方式
- 脚本 + 配置 + CSV 数据文件打包到 res/ 目录
- bin/searchsploit 为指向 res/searchsploit 的符号链接
- exploit 实际文件（47K+）不包含在 Conan 包中，用户可通过 `searchsploit -u` 下载

### 包内容 vs 完整数据库的影响
Conan 包仅含 CSV 索引，不含 `exploits/` 和 `shellcodes/` 目录下的实际漏洞利用代码。
- 搜索类功能（搜索/标题搜索/JSON输出/CVE搜索/过滤排除/版本模糊搜索）只读 CSV，开箱即用
- 文件类功能（`-p` 路径展示/`-m` 镜像复制/`-x` 查看代码）需要实际文件，首次使用前需运行 `searchsploit -u` 通过 git 拉取完整数据库

## 测试结果
8 项功能全部通过：基本搜索、标题搜索、JSON 输出、CVE 搜索、路径展示、版本模糊搜索、过滤排除、镜像复制。
---

**编译结束**: 2026-08-24 14:27
**最终状态**: built
