# lv — Powerful Multi-lingual File Viewer/Grep

## 软件简介

**lv** (Leap View) 是一个强大的多语言文件查看器和 grep 工具，专为处理多种字符编码设计。

### 主要特性

- **多编码支持**: UTF-8, ISO-8859 系列 (1-16), EUC-JP, EUC-KR, EUC-CN, Big5, GB2312, Shift-JIS, HZ 等
- **文件查看**: 类似 less/more 的交互式查看器
- **grep 模式**: 通过 lgrep 命令提供 grep 功能
- **编码检测**: 自动检测文件编码
- **多语言界面**: 支持日文、中文、韩文等多语言显示

### 软件信息

| 项目 | 内容 |
|------|------|
| 名称 | lv |
| 版本 | 4.51-10 |
| 许可证 | GPL-2.0-or-later |
| 语言 | C |
| 构建系统 | autotools |
| 源码来源 | Debian salsa.debian.org |

## 编译版本

### 4.51-10 (当前版本)

**编译状态**: built
**编译日期**: 2026-06-05
**编译平台**: OpenHarmony aarch64

**关键特性**:
- 支持 ncurses 终端界面
- ELF 签名已完成
- 符号链接适配（lgrep）

**下载地址**:
- 预编译包: `lv-4.51-10-ohos-aarch64.tar.gz`
- 通过 cmd-pkgs 公共仓库安装

**已知问题**:
- HMDFS 平台不支持硬链接（已适配为符号链接）
- 无自动化测试套件

## 使用方法

### 文件查看
```bash
lv filename.txt          # 查看文件
lv -c UTF-8 filename     # 指定编码
lv -I ISO-8859-1 file    # 强制输入编码
```

### grep 模式
```bash
lgrep "pattern" *.txt    # 在文件中搜索
lgrep -i "pattern" files # 忽略大小写
```

### 帮助
```bash
lv -h                    # 查看帮助
man lv                   # 查看手册
```

## 依赖库

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4+ | 终端界面库 |

## 编译归档

归档目录: `archives/l/lv/`

### 目录结构
```
4.51-10/
├── manifest.yaml       # 版本级元数据
├── notes.md            # 编译笔记
├── patches/
│   └── 0001-Makefile.in.patch  # HMDFS 适配补丁
├── packaging/
│   ├── lv-4.51-10-ohos-aarch64.tar.gz      # 预编译包
│   └── lv-4.51-10-ohos-aarch64-debug.tar.gz # 调试符号
└── reports/
    ├── quality-report.md  # 质量门禁报告
    └── test-report.md     # 测试报告
```

## 相关资源

- [Debian 源码仓库](https://salsa.debian.org/debian/lv)
- [lv 官方网站](http://www.ff.iij4u.or.jp/~nrt/lv/)
- [OpenHarmony cmd-pkgs](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)

---

**归档创建**: 2026-06-05
**维护者**: OpenHarmony 编译协作者