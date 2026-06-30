# 编译笔记 - mandown v1.0.5.2

**软件**: mandown (man-page inspired Markdown pager)
**版本**: 1.0.5.2
**编译日期**: 2026-05-25
**编译器**: clang 15.0.4
**状态**: built ✅

---

## 软件信息

- **项目**: https://github.com/Titor8115/mandown
- **描述**: man-page 风格的 Markdown 查看器
- **可执行文件**: mdn
- **构建系统**: Makefile (非标准 autotools)

---

## 依赖

| 依赖 | 版本 | 编译方式 | 状态 |
|------|------|----------|------|
| libncursesw | 6.4 | 预编译包 | ✅ 静态链接 |
| libxml2 | 2.15.3 | 源码编译 | ✅ 动态链接 |
| libconfig | 1.7.3 | 源码编译 | ✅ 动态链接 |

---

## 编译过程记录

### Phase 1: 依赖编译

**2026-05-25 16:26** - 尝试使用预编译包
- ncursesw: ✅ 安装成功
- libxml2: ❌ 预编译包损坏（10KB 空文件）
- libconfig: ❌ 预编译包损坏（10KB 空文件）

**2026-05-25 16:30-16:42** - 从源码编译依赖
- libxml2 2.15.3: CMake 构建，禁用 Python/Iconv 绑定
- libconfig 1.7.3: autotools 构建，禁用 C++ 绑定

### Phase 2: mandown 编译

**2026-05-25 16:42-17:08** - 首次编译
- ✅ 编译成功
- ⚠️ 发现 G3 问题：缺少 RPATH

**2026-05-25 17:40-17:44** - RPATH 修复编译
- 修改 Makefile 补丁，添加 `-Wl,-rpath`
- ✅ 重新编译成功
- ✅ RUNPATH 已正确设置

---

## 问题与解决

### 问题 1: 预编译包损坏
- **症状**: libxml2/libconfig 预编译包仅 10KB，内容为空
- **原因**: 预编译包索引与实际文件不匹配
- **解决**: 从源码编译依赖
- **知识沉淀**: E0XX - 预编译包文件损坏

### 问题 2: ncurses 头文件缺失
- **症状**: KEY_ 常量和鼠标支持宏未定义
- **原因**: 预编译 ncurses 头文件不完整
- **解决**: 从 ncurses-6.4 源码生成完整 curses.h

### 问题 3: pkg-config 不完整
- **症状**: Makefile 使用 pkg-config 查找库路径失败
- **原因**: HarmonyOS pkg-config 路径未设置
- **解决**: Makefile 直接指定库路径（避免 pkg-config）

### 问题 4: G3 可移植性（缺少 RPATH）
- **症状**: mdn 运行需要设置 LD_LIBRARY_PATH
- **原因**: LDFLAGS 未包含 RPATH
- **解决**: 添加 `-Wl,-rpath,/storage/Users/currentUser/usr/local/lib`

---

## 补丁列表

| 补丁 | 大小 | 内容 |
|------|------|------|
| 0001-Makefile.patch | 3.3KB | HarmonyOS 平台适配 + RPATH |

---

## 配置选项

```bash
# Makefile 编译
PREFIX=~/usr/local
CC=clang

# 库路径（直接指定，避免 pkg-config）
CURSES_LIBS   = -L~/usr/local/lib -lncursesw
XML2_LIBS     = -L~/usr/local/lib -lxml2
CONFIG_LIBS   = -L~/usr/local/lib -lconfig

# RPATH（运行时库查找）
LDFLAGS      += -Wl,-rpath,~/usr/local/lib
```

---

## 验证结果

```bash
$ ~/usr/local/bin/mdn --help        # ✅ 无需 LD_LIBRARY_PATH
$ readelf -d ~/usr/local/bin/mdn | grep RUNPATH
 0x000000000000001 (RUNPATH)  Library runpath: [/storage/Users/currentUser/usr/local/lib]

$ pkg-config --modversion libxml-2.0   # 2.15.3
$ pkg-config --modversion libconfig    # 1.7.3
```

---

## 知识沉淀

- **E0XX**: 预编译包文件损坏检测与处理
- **Makefile 项目 RPATH**: 非 autotools/CMake 项目需要手动添加 RPATH
- **ncurses 头文件完整性**: 预编译包头文件可能不完整，需从源码生成

---

**笔记更新时间**: 2026-05-25 17:46