# metis 5.1.0 编译进度记录

## 编译时间线

### 2026-05-06 Step 1: init-build
- ✅ 源码下载完成
- ✅ 解压到 /storage/Users/currentUser/builds/metis-5.1.0.orig
- ✅ 工作目录创建: /storage/Users/currentUser/builds/metis-5.1.0.work
- ✅ 档案初始化完成

### 2026-05-06 Step 2: 编译阶段
- ✅ cmake 配置成功
  - 需要使用 CMAKE_POLICY_VERSION_MINIMUM=3.5 解决旧版本兼容性问题
  - 需要设置 GKLIB_PATH 为绝对路径
- ✅ make 编译成功（有警告但无错误）
- ✅ make install DESTDIR=$TEST_PREFIX 成功
- ✅ 功能验证通过（gpmetis 测试）

### 2026-05-06 Step 2.5: 质量门禁
- ✅ G1-G4 门禁全部通过

### 2026-05-06 Step 3: package + finish
- ✅ 预编译包制作成功
- ✅ 本地安装验证成功

## 编译参数记录

```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DGKLIB_PATH=$BUILD_SRC_DIR/GKlib ..

make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 产物清单

### 二进制文件
- gpmetis - 图分区程序
- ndmetis - 嵌套剖分程序  
- mpmetis - 多级分区程序
- m2gmetis - 网格到图转换程序
- graphchk - 图检查程序
- cmpfillin - 填入比较程序

### 库文件
- libmetis.a - 静态库

### 头文件
- metis.h

## 知识沉淀
1. cmake_minimum_required 版本过低时，使用 CMAKE_POLICY_VERSION_MINIMUM 参数
2. metis 的 GKlib 路径需设置为绝对路径，否则 try_compile 会失败
---

**编译结束**: 2026-05-06 18:35
**最终状态**: success
