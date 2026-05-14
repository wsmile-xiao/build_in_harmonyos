# metis — 图分区库

## 软件简介
METIS 是一套用于分区图和网格以及计算填充减少顺序的串行程序。由明尼苏达大学开发。

主要功能：
- 图分区 (gpmetis)
- 嵌套剖分 (ndmetis)
- 多级分区 (mpmetis)
- 网格到图转换 (m2gmetis)
- 图检查 (graphchk)

## 已编译版本

| 版本 | 状态 | 补丁数 | 发布日期 |
|------|------|--------|----------|
| 5.1.0 | success | 0 | 2026-05-06 |

## 编译指导

### 编译依赖
- cmake >= 3.5
- C 编译器 (clang/gcc)
- make

### cmake 配置参数
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DGKLIB_PATH=$BUILD_SRC_DIR/GKlib ..
```

### 编译命令
```bash
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 关键注意事项
1. **cmake 版本兼容性**: metis-5.1.0 的 cmake_minimum_required(VERSION 2.8) 与新版 cmake 不兼容，必须使用 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
2. **GKLIB_PATH**: 必须设置为绝对路径，否则 cmake 的 try_compile 无法找到测试文件

## 补丁清单
当前版本无补丁。

## 已知限制
- 仅编译为静态库 (libmetis.a)，无动态库
- 无官方测试套件，使用示例数据验证

## 功能验证

### 验证命令
```bash
# 使用示例图文件测试分区功能
gpmetis graphs/4elt.graph 2

# 检查图文件有效性
graphchk graphs/4elt.graph
```

### 验证结果
- gpmetis 分区测试通过
- graphchk 图检查通过

## 安装使用

### 快速安装
```bash
tar xzf metis-5.1.0-ohos-aarch64.tar.gz -C ~/usr/local
cd metis-5.1.0-ohos-aarch64 && sh install-metis-5.1.0.sh
```

### 程序列表
- `gpmetis` - 图分区程序
- `ndmetis` - 嵌套剖分程序
- `mpmetis` - 多级分区程序
- `m2gmetis` - 网格到图转换程序
- `graphchk` - 图检查程序
- `cmpfillin` - 填入比较程序

### 库文件
- `lib/libmetis.a` - 静态库

### 头文件
- `include/metis.h`

## 参考链接
- 官网: http://glaros.dtc.umn.edu/gkhome/metis/metis
- 源码: https://karypis.github.io/glaros/files/sw/metis/metis-5.1.0.tar.gz