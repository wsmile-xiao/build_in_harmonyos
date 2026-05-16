# cgif — HarmonyOS aarch64 预编译包

## 软件简介
cgif 是一个快速轻量的 GIF 编码器库，用于创建 GIF 动画和静态图像。
- 官网: https://github.com/dloebl/cgif
- 许可证: MIT
- 类型: 多媒体库 (GIF编码)
- 依赖: 无

## 快速安装

### 方式1: 本地安装
```bash
tar xzf cgif-0.5.2-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local && sh install-cgif-0.5.2.sh
```

### 方式2: 在线安装
```bash
curl -fsSL <url>/install.sh | sh -s -- 0.5.2
```

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 测试通过 |
|------|------|----------|--------|----------|
| 0.5.2 | success | meson | 0 | 48/48 |

## 当前版本 (0.5.2) 详情

### 包内容
```
include/
  cgif.h           # 头文件
lib/
  libcgif.so.0.5.2 # 动态库 (主)
  libcgif.so.0     # 符号链接
  libcgif.so       # 符号链接
  pkgconfig/
    cgif.pc        # pkg-config 文件
```

### 包大小
- 主包 (runtime): 245KB
- debug包 (调试符号): 135KB

### 编译信息
| 项目 | 值 |
|------|-----|
| 构建系统 | meson 1.11.0 |
| 编译器 | clang 15.0.4 |
| 目标架构 | aarch64 |
| 目标系统 | HarmonyOS |
| 质量门禁 | PASS (G1-G4) |
| 测试结果 | PASS (48/48) |
| 补丁数 | 0 |

### 安装验证
```bash
# pkg-config 验证
pkg-config --modversion cgif  # 输出: 0.5.2
pkg-config --cflags cgif      # 输出: -I~/usr/local/include
pkg-config --libs cgif        # 输出: -L~/usr/local/lib -lcgif

# 编写测试程序
echo '#include <cgif.h>
int main() { CGIF_Config c = {0}; c.width=10; c.height=10; return 0; }' > test.c
cc test.c -lcgif && ./a.out && echo "OK"
```

## 使用示例
```c
#include <cgif.h>

int main() {
    CGIF_Config config = {0};
    config.width = 100;
    config.height = 100;
    config.path = "output.gif";
    
    CGIF *cgif = cgif_new(&config);
    // 添加帧...
    cgif_close(cgif);
    return 0;
}
```

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 无外部依赖

## 编译备注
- 原生源码可直接编译，无需补丁
- 需要先安装 meson 和 ninja
