# libfyaml 0.9.6 编译笔记

## 编译信息
- 编译日期: 2025-05-25
- 编译系统: autotools
- 编译器: clang
- 平台: aarch64-unknown-linux-ohos

## 编译过程

### 1. 配置
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
```

### 2. 编译
```bash
make -j2
```

### 3. 安装
```bash
make install DESTDIR=/storage/Users/currentUser/test-install-libfyaml-0.9.6
```

### 4. 本地安装
```bash
make install
```

## 产物
- 共享库：lib/libfyaml.so
- 可执行文件：bin/fy-tool
- 开发头文件：include/libfyaml.h, include/libfyaml/*.h

## 验证
已安装到 ~/usr/local/，可正常使用。

## 补丁
应用了以下补丁：
1. config.guess 更新（识别 aarch64-unknown-linux-ohos）
2. config.sub 更新（识别 aarch64-unknown-linux-ohos）

## 注意事项
无特殊注意事项。
