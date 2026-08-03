# most 5.2.0 for HarmonyOS

## 概述

most 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | most |
| 版本 | 5.2.0 |
| 下载地址 | https://www.jedsoft.org/releases/most/most-5.2.0.tar.gz |
| 官方文档 | https://www.jedsoft.org/most/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译步骤

```bash
# 1. 下载源码
wget https://www.jedsoft.org/releases/most/most-5.2.0.tar.gz
tar -xzf most-5.2.0.tar.gz
cd most-5.2.0

# 2. 应用补丁（如有）
# patch -p1 < patches/0001-xxx.patch

# 3. 配置
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 依赖

- S-Lang 库 (slang) 2.x

## 补丁说明

当前版本无补丁，首次适配。

## 测试结果

详见 [test-report.md](./5.2.0/reports/test-report.md)（待 CI 生成）

## 验证安装

```bash
most --version
most --help
```

## 经验总结

1. most 依赖 S-Lang 库，需先确保 slang 已适配并发布到鸿蒙制品仓
2. 构建系统为 autotools，可能需要 config.guess/config.sub 平台识别补丁

## 参考资料

- https://www.jedsoft.org/most/
- https://www.jedsoft.org/releases/most/
- https://github.com/jedsoft/most