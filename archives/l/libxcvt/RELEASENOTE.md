# libxcvt — HarmonyOS aarch64 预编译包

## 快速安装

```bash
# 下载预编译包
tar xzf libxcvt-0.1.3-ohos-aarch64.tar.gz -C ~/usr/local

# 进入安装目录执行安装脚本
cd ~/usr/local/libxcvt-0.1.3-ohos-aarch64 && sh install-libxcvt-0.1.3.sh

# 验证安装
cvt 1920 1080 60
```

---

## 可用版本

| 版本 | 状态 | 补丁数 | 质量门禁 | 发布日期 |
|------|------|--------|----------|----------|
| 0.1.3 | ✅ success | 0 | PASS | 2026-05-06 |

---

## 当前版本 (0.1.3) 详情

### 包信息

| 属性 | 值 |
|------|------|
| 包名 | libxcvt-0.1.3-ohos-aarch64.tar.gz |
| 大小 | 312 KB |
| 调试包 | libxcvt-0.1.3-ohos-aarch64-debug.tar.gz (106 KB) |
| 目标平台 | HarmonyOS aarch64 |

### 包内容

```
libxcvt-0.1.3-ohos-aarch64/
├── bin/
│   └── cvt                  # VESA CVT modeline 生成工具
├── lib/
│   ├── libxcvt.so.0.1.3     # 共享库
│   ├── libxcvt.so.0         # 软链接
│   └── libxcvt.so           # 软链接
├── include/
│   └── libxcvt/
│       ├── libxcvt.h        # 主头文件
│       └── libxcvt_mode.h   # mode 结构定义
├── lib/pkgconfig/
│   └── libxcvt.pc           # pkg-config 配置
├── share/man/man1/
│   └── cvt.1                # man 手册
└── install-libxcvt-0.1.3.sh # 安装脚本
```

### 编译信息

| 属性 | 值 |
|------|------|
| 构建系统 | meson 1.11.0 |
| 构建后端 | ninja 1.11.1 |
| 编译器 | clang 15.0.4 |
| 目标架构 | aarch64 |
| 质量门禁 | G1-G4 全部通过 |
| 测试结果 | 15/15 PASS |
| 补丁数 | 0 |

---

## 功能说明

### cvt 命令行工具

`cvt` 是一个用于生成 VESA CVT 标准 timing modelines 的命令行工具，主要用于 X Window System 配置显示器时序参数。

**基本用法**:
```bash
cvt <宽度> <高度> [刷新率]
```

**示例**:
```bash
# 生成 1920x1080@60Hz modeline
$ cvt 1920 1080 60
# 1920x1080 59.96 Hz (CVT 2.07M9) hsync: 67.16 kHz; pclk: 173.00 MHz
Modeline "1920x1080_60.00"  173.00  1920 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync

# Reduced blanking 模式 (节能)
$ cvt -r 1920 1080 60
# 1920x1080 59.93 Hz (CVT 2.07M9-R) hsync: 66.59 kHz; pclk: 138.50 MHz
Modeline "1920x1080R"  138.50  1920 1968 2000 2080  1080 1083 1088 1111 +hsync -vsync
```

---

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- HongMeng Kernel 1.12.0+
- 运行时依赖: libc.so (无额外依赖)

---

## 验证安装

```bash
# 检查 cvt 工具
cvt --version

# 功能测试
cvt 1920 1080 60

# 检查库文件
file $HOME/usr/local/lib/libxcvt.so.0.1.3

# pkg-config 验证
pkg-config --cflags --libs libxcvt
```

---

## 更新历史

### 0.1.3 (2026-05-06)
- ✅ 首次成功编译
- ✅ meson 构建系统验证通过
- ✅ 15 个功能测试全部通过
- ✅ 无补丁，源码直接编译成功
- ✅ ELF 签名完成