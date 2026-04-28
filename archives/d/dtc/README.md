# dtc (Device Tree Compiler)

## 软件信息
- **名称**: dtc
- **描述**: Device Tree Compiler - 设备树编译器，用于处理设备树源文件和二进制文件
- **许可证**: GPL-2.0-or-later OR BSD-2-Clause
- **主页**: https://devicetree.org/

## 可用版本
| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.7.2 | partial | 1 |

## 1.7.2 版本详情

### 编译信息
- 构建系统: Makefile (非完整 autotools)
- 编译器: clang 15.0.4
- 目标平台: HarmonyOS aarch64

### 补丁说明
- `0001-Makefile.patch`: 移除 clang 不支持的 GCC 特有警告选项 `-Wsuggest-attribute=format`

### 安装产物
- 二进制工具: dtc, convert-dtsv0, fdtdump, fdtget, fdtoverlay, fdtput, dtdiff
- 库文件: libfdt.a (静态库), libfdt.so.1.7.2 (动态库)
- 头文件: fdt.h, libfdt.h, libfdt_env.h

### 快速安装
```bash
tar xzf dtc-1.7.2-ohos-aarch64.tar.gz -C ~/usr/local
cd dtc-1.7.2-ohos-aarch64 && sh install-dtc-1.7.2.sh
```

### 使用注意
动态链接的工具（fdtget, fdtoverlay 等）需要设置：
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

### 验证命令
```bash
dtc --version  # 显示 Version: DTC 1.7.2
```

## 已知限制
1. 部分测试脚本与当前平台不兼容（stat 命令格式）
2. 动态链接工具需要手动设置 LD_LIBRARY_PATH

## 依赖
无外部依赖