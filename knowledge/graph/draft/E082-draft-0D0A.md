# E082: glib-genmarshal/glib-mkenums 版本不兼容

## 基本信息

| 字段 | 值 |
|------|-----|
| 严重度 | 2 |
| 类别 | tool-compat \| version-mismatch \| build-system |
| 触发工具 | meson \| glib-genmarshal \| glib-mkenums |
| 阶段 | build \| configure |

## 错误模式

### 典型错误日志
```bash
Usage:
  glib-genmarshal [OPTION...] [FILE...]

Options:
  --header                 Output header file
  --body                   Output source file
  --prefix=STRING          Marshall prefix
  ...

ERROR: Unknown option '--quiet'
ERROR: Unknown option '--output'
ERROR: Unknown option '--pragma-once'
```

### 典型场景
```bash
# Meson 构建调用
glib-genmarshal --quiet --output gdk-pixbuf-marshal.h --pragma-once gdk-pixbuf-marshal.list

# 系统版本（旧版）
glib-genmarshal --version
glib-genmarshal version 2.38.2

# 需要版本
# glib-genmarshal version 2.88.0+
```

## 触发条件

1. **构建系统**: Meson（通常需要较新的 glib 工具）
2. **系统工具版本**: glib 2.38.2（HarmonyOS 默认版本）
3. **需要的版本**: glib 2.88.0+（或支持新参数的版本）
4. **具体工具**: `glib-genmarshal` 和 `glib-mkenums`

## 根因分析

### 参数差异对比

| 参数 | glib 2.38.2 | glib 2.88.0+ | 用途 |
|------|-------------|--------------|------|
| `--quiet` | ❌ 不支持 | ✅ 支持 | 静默模式 |
| `--output FILE` | ❌ 不支持 | ✅ 支持 | 指定输出文件 |
| `--pragma-once` | ❌ 不支持 | ✅ 支持 | 使用 `#pragma once` |
| `--prototypes` | ✅ 支持 | ✅ 支持 | 输出函数原型 |
| `--prefix=PREFIX` | ✅ 支持 | ✅ 支持 | 函数前缀 |

### 兼容性演进

glib-genmarshal 工具在 glib 2.54+ 版本进行了重大重构：
- **glib 2.38.x**: 使用旧的 Python 脚本实现
- **glib 2.54+**: 使用新的命令行参数格式
- **glib 2.80+**: 进一步优化参数，支持 `--quiet`、`--output` 等

### HarmonyOS 环境

HarmonyOS 默认提供的 glib 工具版本较旧：
```bash
# 检查系统版本
glib-genmarshal --version
# 输出: glib-genmarshal version 2.38.2

# 检查需要的参数
meson build --help
# Meson 构建脚本期望 glib 2.80+ 版本的参数
```

## 解决方案

### 方案 A：降级构建参数（推荐 - 适用于简单场景）

修改 Meson 构建文件，使用旧参数：

```python
# 原始调用
genmarshal = find_program('glib-genmarshal')
marshal_output = custom_target('marshal',
    output: ['marshal.h', 'marshal.c'],
    command: [genmarshal, '--quiet', '--output', '@OUTPUT@', '--pragma-once', '@INPUT@']
)

# 修改为兼容参数
marshal_output = custom_target('marshal',
    output: ['marshal.h', 'marshal.c'],
    command: [genmarshal, '--header', '@INPUT@'],
    capture: true,  # Meson 捕获输出
)
# 或使用 shell 重定向
command: [genmarshal, '--header', '@INPUT@', '>', '@OUTPUT@']
```

**限制**：
- 需要手动修改构建文件
- 某些参数无法完全替代

### 方案 B：手动生成文件（推荐 - 最可靠）

在其他平台预生成输出文件：

```bash
# 步骤 1: 在 Linux 主机上生成
# （需要 glib 2.80+ 版本）
glib-genmarshal --header --pragma-once gdk-pixbuf-marshal.list > gdk-pixbuf-marshal.h
glib-genmarshal --body gdk-pixbuf-marshal.list > gdk-pixbuf-marshal.c

# 步骤 2: 复制到 HarmonyOS 构建目录
scp gdk-pixbuf-marshal.{h,c} device@harmonyos:/path/to/build/

# 步骤 3: 修改 Meson build 文件跳过生成步骤
# 注释掉 custom_target 调用，直接使用预生成的文件
```

**优点**：
- 绕过版本兼容性问题
- 不影响最终构建结果

**缺点**：
- 需要额外的预生成步骤
- 每次修改 marshal.list 需要重新生成

### 方案 C：安装新版本 glib 工具（推荐 - 长期方案）

自行编译并安装新版本的 glib 工具：

```bash
# 步骤 1: 编译 glib 2.80+
cd ~/builds
git clone https://gitlab.gnome.org/GNOME/glib.git
cd glib
git checkout 2.88.0  # 或更新的稳定版本

# 步骤 2: Meson 构建
meson setup builddir --prefix=~/usr/local
ninja -C builddir
ninja -C builddir install

# 步骤 3: 更新 PATH
export PATH=~/usr/local/bin:$PATH

# 步骤 4: 验证版本
glib-genmarshal --version
# 应输出: glib-genmarshal version 2.88.0
```

**注意事项**：
- 需要解决 glib 本身的大量依赖
- 可能需要先编译 meson、ninja 等

### 方案 D：使用替代工具

某些情况下，可以使用其他方式绕过：

```bash
# 手动编写 marshal 函数（简单场景）
# 或者使用 Perl 脚本替代（旧版 glib-genmarshal 的实现）
```

## 禁止做法

❌ **直接忽略错误**
- 原因：会导致后续编译步骤缺少必需的生成文件

❌ **强制使用不兼容的参数**
- 原因：工具会报错并退出，无法继续

❌ **修改系统 glib 版本**
- 原因：可能影响其他依赖系统 glib 的软件

## 验证方法

```bash
# 1. 检查系统工具版本
glib-genmarshal --version
glib-mkenums --version

# 2. 测试参数兼容性
glib-genmarshal --quiet --help
# 如果支持 --quiet，会输出帮助信息
# 如果不支持，会报错 "Unknown option '--quiet'"

# 3. 测试手动生成
echo 'VOID:INT' > test.list
glib-genmarshal --header test.list
# 如果成功，会输出 marshal 函数声明
```

## 影响范围

所有需要 glib-genmarshal 或 glib-mkenums 的软件：
- **gdk-pixbuf**: 图像加载库
- **GTK 系列**: GTK 3/4, GIMP 等
- **GStreamer**: 多媒体框架
- **其他 GObject-based 库**

## 具体案例：gdk-pixbuf 2.44.6

### 构建命令
```bash
meson setup builddir \
    --prefix=$DEFAULT_PREFIX \
    --buildtype=release \
    -Dintrospection=disabled
```

### 遇到的错误
```bash
[1/150] Generating gdk-pixbuf/gdk-pixbuf-marshal.h with a custom command
FAILED: gdk-pixbuf/gdk-pixbuf-marshal.h
/path/to/glib-genmarshal --quiet --output gdk-pixbuf-marshal.h --pragma-once gdk-pixbuf-marshal.list
Usage: glib-genmarshal [OPTION...] [FILE...]
ERROR: Unknown option '--quiet'
```

### 采用方案
- **方案 B**（手动生成文件）
- 在 Linux 主机上预生成 gdk-pixbuf-marshal.{h,c}
- 复制到 HarmonyOS 构建目录
- 修改 meson.build 跳过生成步骤

## 相关条目

- E081: Python subprocess posix_spawn 权限错误（gdk-pixbuf 同时遇到）
- E010: toybox 工具兼容性（另一个工具版本问题）
- E053: C++ 编译器兼容性（版本不匹配问题）

## 历史记录

- **2026-05-26**: gdk-pixbuf 2.44.6 编译时发现此问题
- **2026-05-26**: 采用方案 B（手动生成）解决

---

*文档版本: 1.0*
*最后更新: 2026-05-26*
*更新内容: 初始创建，记录 gdk-pixbuf 编译问题*