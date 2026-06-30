# libmedc (MED-fichier)

MED-fichier 是一个用于科学数据交换的库，基于 HDF5 格式存储网格数据、场数据等。

## 简介

MED (Model for Exchange of Data) 是一个标准化的数据模型，用于存储和交换有限元分析、计算流体力学等科学计算领域的数据。libmedc 是其 C 语言实现库。

## 特性

- 支持 2D/3D 网格数据存储
- 支持标量场、向量场数据
- 兼容 HDF5 格式
- 提供文件操作和查询工具

## 版本

### 4.1.0 (2026-06-08)

**编译状态**: ✅ published

**编译方式**: CMake (静态链接)

**预编译包**: `libmedc-4.1.0-ohos-aarch64.tar.gz` (42MB)

**依赖**:
- HDF5 1.10.8 (静态链接)

**产物**:
- 静态库: `libmedC.a` (4.4MB)
- 工具: mdump, mdump2, mdump3, mdump4, medconforme (静态链接)

**功能测试**: 22/22 通过 ✅

详见 [4.1.0/reports/test-report.md](4.1.0/reports/test-report.md)

**使用限制**:
1. 使用 libmedC.a 需要用 C++ 编译器链接 (clang++)
2. medimport 工具因符号冲突在静态库版本中无法构建
3. 预编译包中的工具是静态链接版本，可直接运行

## 安装

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmedc 4.1.0

# 验证安装
mdump4 --help
```

## 使用示例

```c
#include <med.h>

int main() {
    med_idt fid = MEDfileOpen("test.med", MED_ACC_CREAT);
    MEDfileClose(fid);
    return 0;
}
```

编译:
```bash
clang++ -I$HOME/usr/local/include test.c -L$HOME/usr/local/lib -lmedC -lhdf5 -lz -lm -o test
```

## 文档

- [编译笔记](4.1.0/notes.md)
- [功能测试报告](4.1.0/reports/test-report.md)