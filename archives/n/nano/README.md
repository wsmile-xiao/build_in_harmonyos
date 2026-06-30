# GNU nano

GNU nano 是一个简单易用的文本编辑器，支持 UTF-8 和语法高亮。

## 版本信息

- 当前版本: 7.2
- 发布日期: 2023-07-09
- 官方网站: https://www.nano-editor.org/
- 源码地址: https://ftp.gnu.org/gnu/nano/nano-7.2.tar.gz

## 功能特性

- UTF-8 支持
- 语法高亮（多种语言）
- 搜索和替换
- 多文件编辑
- 撤销/重做

## 平台适配说明

### HarmonyOS/OpenHarmony 适配

由于平台限制，以下功能已禁用：
- 鼠标支持（ncurses 预编译包未包含 NCURSES_MOUSE_VERSION）
- libmagic 文件类型检测（平台未提供）
- NLS 国际化（gettext 未配置）

### 补丁文件

| 补丁 | 说明 |
|------|------|
| 0001-config-tempdir.patch | 修复 HMDFS 临时目录创建问题（E076） |
| 0002-keydef.patch | 添加缺失的 ncurses KEY 定义 |

## 编译选项

```
--prefix=/data/service/hnp/usr/local
--disable-libmagic
--disable-mouse
--disable-nls
--enable-utf8
```

## 依赖

- ncursesw 6.4（预编译包）

## 使用方法

```bash
# 设置库路径
export LD_LIBRARY_PATH=/data/service/hnp/usr/local/lib:$LD_LIBRARY_PATH

# 运行 nano
nano [文件名]

# 查看版本
nano --version  # GNU nano, version 7.2
```

## 已知问题

- 运行前需要设置 LD_LIBRARY_PATH（ncurses 库位置）
- 鼠标功能不可用