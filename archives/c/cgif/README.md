# cgif — OpenHarmony 编译记录

## 软件概述
- **名称**: cgif (A fast and lightweight GIF encoder)
- **官网**: https://github.com/dloebl/cgif
- **类型**: GIF 编码器库 (多媒体)
- **许可证**: MIT
- **依赖**: 无 (纯 C 库)

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 测试结果 | 编译日期 |
|------|------|----------|--------|----------|----------|
| 0.5.2 | ✅ success | meson | 0 | 48/48 PASS | 2026-05-06 |

---

## 编译指导 (0.5.2)

### 前置要求
| 工具 | 版本要求 | 检查命令 |
|------|---------|---------|
| meson | >= 0.56 | `meson --version` |
| ninja | >= 1.11 | `ninja --version` |
| clang/cc | C编译器 | `cc --version` |
| python3 | >= 3.12 | `python3 --version` |

### 安装依赖
```bash
# 安装 meson (如果未安装)
python3 -m pip install meson --user
export PATH="$HOME/.local/bin:$PATH"
```

### 编译命令
```bash
# 设置环境变量
export DEFAULT_PREFIX="$HOME/usr/local"
export TEST_PREFIX="$HOME/tmp/test-install-cgif-0.5.2"

# 下载源码
curl -L -o cgif-0.5.2.tar.gz \
  https://gh-proxy.com/https://github.com/dloebl/cgif/archive/refs/tags/v0.5.2.tar.gz

# 解压
tar -xzf cgif-0.5.2.tar.gz
cd cgif-0.5.2

# 配置
meson setup build --prefix=$DEFAULT_PREFIX

# 编译
ninja -C build

# 安装到 staging
DESTDIR=$TEST_PREFIX ninja -C build install

# 测试
ninja -C build test

# 安装到本地
ninja -C build install
```

### 验证安装
```bash
# pkg-config 验证
pkg-config --modversion cgif   # 应输出: 0.5.2
pkg-config --cflags cgif       # 应输出: -I~/usr/local/include
pkg-config --libs cgif         # 应输出: -L~/usr/local/lib -lcgif

# 库文件检查
ls -la ~/usr/local/lib/libcgif.so*
```

---

## 补丁清单

**无补丁** — 原生源码可直接编译。

---

## 已知问题与解决

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| GitHub下载超时 | 网络限制 | 使用 gh-proxy.com 镜像 |
| meson not found | 未安装 | `pip install meson --user` |
| /tmp 只读 | 平台限制 | 使用 `$HOME/tmp` |
| BUILD_SYSTEM误判 | 无 configure | 手动使用 meson |

---

## 知识沉淀

### meson 构建系统要点
1. meson 配置: `meson setup build --prefix=$PREFIX`
2. ninja 编译: `ninja -C build`
3. 安装命令: `ninja -C build install`
4. 测试命令: `ninja -C build test`

### cgif 特性
- 无外部依赖
- 纯 C 实现 (C99)
- 支持 GIF89a 动画
- pkg-config 支持

---

## 预编译包下载

| 包名 | 大小 | 类型 |
|------|------|------|
| cgif-0.5.2-ohos-aarch64.tar.gz | 245KB | 运行时 |
| cgif-0.5.2-ohos-aarch64-debug.tar.gz | 135KB | 调试符号 |

---

## 功能验证代码

```c
#include <stdio.h>
#include <cgif.h>

int main() {
    CGIF_Config config = {0};
    config.width = 10;
    config.height = 10;
    printf("cgif API test: width=%d, height=%d\n", config.width, config.height);
    return 0;
}
```

编译运行:
```bash
cc test.c -I~/usr/local/include -L~/usr/local/lib -lcgif -Wl,-rpath,~/usr/local/lib
./a.out  # 应输出: cgif API test: width=10, height=10
```
