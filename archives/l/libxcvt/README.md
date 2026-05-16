# libxcvt — OpenHarmony 预编译包

## 软件简介

**libxcvt** 是一个用于生成 VESA CVT (Coordinated Video Timing) 标准 timing modelines 的库和命令行工具。它主要用于 X Window System 配置显示器时序参数。

### 核心功能
- 生成符合 VESA CVT 标准的 display mode lines
- 支持标准模式和 reduced blanking 模式
- 提供 C 语言共享库 (libxcvt.so) 和命令行工具 (cvt)

### 典型用途
- X11 配置文件中的 Monitor section
- 显示器时序参数计算
- 视频模式验证和调试

## 基本信息

| 属性 | 值 |
|------|------|
| 软件名 | libxcvt |
| 版本 | 0.1.3 |
| 构建系统 | meson |
| 目标平台 | HarmonyOS aarch64 |
| 源码URL | https://www.x.org/releases/individual/lib/libxcvt-0.1.3.tar.xz |
| 许可证 | MIT |

---

## 编译指导

### 依赖要求

#### 必需工具
- **meson** >= 0.40.0 (推荐使用 pip 安装)
- **ninja** (构建后端)
- **clang** 或 gcc (C 编译器)

#### 安装 meson
```bash
# 使用 pip 安装 meson
python3 -m pip install --user meson

# 确认安装
~/.local/bin/meson --version
```

### 编译步骤

```bash
# 1. 设置环境变量
export DEFAULT_PREFIX="$HOME/usr/local"
export TEST_PREFIX="$HOME/tmp/test-install-libxcvt-0.1.3"

# 2. 解压源码
tar xf libxcvt-0.1.3.tar.xz
cd libxcvt-0.1.3

# 3. meson 配置
~/.local/bin/meson setup build --prefix=$DEFAULT_PREFIX

# 4. 编译
ninja -C build

# 5. 安装到 staging 目录
DESTDIR=$TEST_PREFIX ninja -C build install

# 6. 安装到本地
ninja -C build install
```

### HarmonyOS 特殊注意事项

1. **ELF 签名**: HarmonyOS 要求 ELF 文件必须签名才能执行
   ```bash
   # 使用 ohc-run.py 签名
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/cvt
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/lib/libxcvt.so.0.1.3
   ```

2. **PATH 配置**: 确保 meson 和 ninja 在 PATH 中
   ```bash
   export PATH="$HOME/.local/bin:$HOME/usr/local/bin:$PATH"
   ```

---

## 补丁清单

**当前版本 (0.1.3) 无补丁** - 源码直接编译成功，无需修改。

---

## 已知限制

| 限制 | 说明 | 影响 |
|------|------|------|
| ELF 签名 | HarmonyOS 要求 ELF 文件签名 | 需要使用 sign-elf 工具 |
| meson 依赖 | 需要手动安装 meson | 编译前置步骤 |
| 无测试套件 | 源码不含自动化测试 | 需手动验证功能 |

---

## 功能验证

### cvt 命令行工具测试

```bash
# 基本测试: 生成 1920x1080@60Hz modeline
cvt 1920 1080 60

# 输出:
# 1920x1080 59.96 Hz (CVT 2.07M9) hsync: 67.16 kHz; pclk: 173.00 MHz
Modeline "1920x1080_60.00"  173.00  1920 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync
```

```bash
# Reduced blanking 模式测试
cvt -r 1920 1080 60

# 输出:
# 1920x1080 59.93 Hz (CVT 2.07M9-R) hsync: 66.59 kHz; pclk: 138.50 MHz
Modeline "1920x1080R"  138.50  1920 1968 2000 2080  1080 1083 1088 1111 +hsync -vsync
```

### 库验证

```bash
# 检查库文件
file $HOME/usr/local/lib/libxcvt.so.0.1.3
# 输出: ELF 64-bit LSB shared object, ARM aarch64, ...

# 检查依赖
readelf -d $HOME/usr/local/lib/libxcvt.so.0.1.3 | grep NEEDED
# 输出: Shared library: [libc.so] (仅依赖 libc)

# pkg-config 验证
pkg-config --cflags --libs libxcvt
# 输出: -I$HOME/usr/local/include -L$HOME/usr/local/lib -lxcvt
```

---

## 安装产物

### 文件清单

```
$HOME/usr/local/
├── bin/
│   └── cvt                  # 命令行工具 (31KB)
├── lib/
│   ├── libxcvt.so           # 软链接 -> libxcvt.so.0
│   ├── libxcvt.so.0         # 软链接 -> libxcvt.so.0.1.3
│   ├── libxcvt.so.0.1.3     # 共享库 (23KB)
│   └── pkgconfig/
│       └── libxcvt.pc       # pkg-config 配置
├── include/
│   └── libxcvt/
│       ├── libxcvt.h        # 主头文件
│       └── libxcvt_mode.h   # mode 结构定义
└── share/
    └── man/
        └── man1/
            └── cvt.1        # man 手册页
```

---

## API 使用示例

```c
#include <libxcvt/libxcvt.h>
#include <stdio.h>

int main() {
    // 生成 1920x1080@60Hz 的 mode info
    struct libxcvt_mode_info *mode = libxcvt_gen_mode_info(
        1920, 1080, 60.0, 0  // 0 = 标准 CVT 模式
    );
    
    if (mode) {
        printf("Pixel Clock: %d kHz\n", mode->dotclock);
        printf("HDisplay: %d\n", mode->hdisplay);
        printf("VDisplay: %d\n", mode->vdisplay);
        
        libxcvt_free_mode_info(mode);
    }
    
    return 0;
}
```

编译:
```bash
cc -I$HOME/usr/local/include -L$HOME/usr/local/lib -lxcvt myprogram.c -o myprogram
```

---

## 已编译版本

| 版本 | 状态 | 补丁数 | 编译日期 |
|------|------|--------|----------|
| 0.1.3 | ✅ success | 0 | 2026-05-06 |

---

## 相关资源

- 官方源码: https://www.x.org/releases/individual/lib/
- X.Org Wiki: https://www.x.org/wiki/
- VESA CVT 标准: https://www.vesa.org/