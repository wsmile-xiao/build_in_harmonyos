# metis — HarmonyOS aarch64 预编译包

## 快速安装

```bash
# 下载预编译包后解压
tar xzf metis-5.1.0-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd metis-5.1.0-ohos-aarch64 && sh install-metis-5.1.0.sh

# 验证安装
gpmetis --help
```

## 可用版本

| 版本 | 状态 | 补丁数 | 发布日期 |
|------|------|--------|----------|
| 5.1.0 | success | 0 | 2026-05-06 |

## 当前版本 (5.1.0) 详情

### 包内容
**二进制程序 (6个)**:
- `bin/gpmetis` - 图分区程序 (277KB)
- `bin/ndmetis` - 嵌套剖分程序 (281KB)
- `bin/mpmetis` - 多级分区程序 (277KB)
- `bin/m2gmetis` - 网格到图转换程序 (134KB)
- `bin/graphchk` - 图检查程序 (126KB)
- `bin/cmpfillin` - 填入比较程序 (126KB)

**库文件**:
- `lib/libmetis.a` - 静态库 (590KB)

**头文件**:
- `include/metis.h` - C API 头文件

**包大小**: 
- 主包: 2.0MB (metis-5.1.0-ohos-aarch64.tar.gz)
- 调试符号包: 362KB (metis-5.1.0-ohos-aarch64-debug.tar.gz)

### 编译信息
- 构建系统: cmake
- 编译器: clang 15.0.4
- 目标平台: HarmonyOS aarch64
- 质量门禁: PASS
- 补丁数: 0

### cmake 配置参数
```
-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_POLICY_VERSION_MINIMUM=3.5
-DGKLIB_PATH=/storage/Users/currentUser/builds/metis-5.1.0.work/GKlib
```

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 无外部依赖

## 使用示例

### 图分区
```bash
# 将图分为2个分区
gpmetis mygraph.graph 2

# 将图分为4个分区，输出详细信息
gpmetis mygraph.graph 4
```

### 图检查
```bash
# 检查图文件格式是否正确
graphchk mygraph.graph
```

### 网格转图
```bash
# 将网格文件转换为图格式
m2gmetis mymesh.mesh mygraph.graph
```

## 已知问题
- 无官方测试套件，建议使用示例数据验证

## 更新日志
- 2026-05-06: 初次编译发布