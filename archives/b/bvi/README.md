# bvi - Binary Visual Editor

## 软件简介

**bvi** 是一个类似 vi 的二进制文件（十六进制）编辑器，提供可视化界面来编辑和查看二进制文件。

### 主要特性

- **vi 风格操作**: 提供熟悉的 vi/vim 编辑体验
- **十六进制视图**: 以十六进制和 ASCII 双栏显示二进制内容
- **bmore 查看器**: 包含二进制文件分页查看工具 bmore
- **命令别名**: 提供 bview 和 bvedit 作为 bvi 的软链接别名

### 项目信息

- **官方主页**: http://bvi.sourceforge.net/
- **源码仓库**: https://sourceforge.net/projects/bvi/
- **许可证**: GPL-3.0-or-later

---

## HarmonyOS 编译版本

### 当前可用版本

| 版本 | 状态 | 编译日期 | 平台 |
|------|------|----------|------|
| 1.5.0 | ✅ built | 2026-06-08 | HarmonyOS aarch64 |

### 编译依赖

- ncurses (静态链接)

### 安装方法

使用 cmd-pkgs 公共安装脚本:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- bvi 1.5.0
```

---

## 平台适配说明

### 已解决的问题

1. **config.guess 平台识别**: 应用 HarmonyOS 平台识别补丁
2. **umask 行为差异**: HarmonyOS `umask 077` 导致临时目录权限异常
3. **termcap 头文件**: 添加缺失的 termcap.h 包含
4. **硬链接限制**: HMDFS 不支持硬链接，改用软链接

### 运行时注意事项

- 需要终端环境运行
- `/tmp` 目录只读，使用 `$TMPDIR` 替代
- 软链接 bview/bvedit 指向 bvi 主程序

---

## 文件结构

```
bvi/
├── README.md          # 本文件（软件级说明）
└── 1.5.0/
    ├── manifest.yaml  # 版本级元数据
    ├── notes.md       # 编译笔记
    ├── patches/       # 平台适配补丁
    │   ├── 0001-Makefile.in.patch
    │   ├── 0002-bm_unix.c.patch
    │   ├── 0003-config.guess.patch
    │   └── 0004-config.sub.patch
    ├── packaging/     # 预编译包
    │   ├── bvi-1.5.0-ohos-aarch64.tar.gz
    │   └── bvi-1.5.0-ohos-aarch64-debug.tar.gz
    └── reports/       # 测试报告
        ├── test-report.md
        └── quality-report.md
```

---

## 使用示例

### 编辑二进制文件

```bash
bvi /path/to/binary/file
```

### 查看二进制文件

```bash
bmore /path/to/binary/file
```

### vi 命令支持

bvi 支持常用的 vi 命令:
- `i` - 进入插入模式
- `ESC` - 返回命令模式
- `:w` - 保存文件
- `:q` - 退出编辑器
- `:wq` - 保存并退出

---

*最后更新: 2026-06-08*
