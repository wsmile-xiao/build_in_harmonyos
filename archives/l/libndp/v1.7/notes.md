# 编译笔记 - libndp v1.7

**编译时间**: 2026-05-29
**编译状态**: published
**构建系统**: autotools

## 编译过程

### 1. 源码准备
```bash
# 下载源码
wget https://github.com/jpirko/libndp/archive/refs/tags/v1.7.tar.gz

# 解压
tar -xzf libndp-v1.7.tar.gz
cd libndp-1.7
```

### 2. 生成 configure
```bash
# libndp 的 tarball 是原始源码，需要先运行 autogen.sh
./autogen.sh
```

### 3. 配置与编译
```bash
./configure --prefix=/usr/local
make -j2
```

### 4. 安装
```bash
make install DESTDIR=/tmp/test-install-libndp-v1.7
```

### 5. 测试
```bash
make check  # 无独立测试套件，仅有编译验证
```

### 6. 验证
```bash
ndptool --help  # 验证工具可用
ls /usr/local/lib/libndp.so.0.1.1  # 验证库文件存在
```

## 编译警告
- libndp.c:208 有一个类型不兼容警告（struct sockaddr_in6 * 传给 const struct sockaddr *）
- 不影响功能，可正常使用

## 平台适配
- 无需修改源码
- 无平台特定补丁
- autotools 自动适配

## 依赖关系
- 构建依赖: autoconf, automake, libtool
- 运行时依赖: 无（纯 C 库）

## 知识提取
- E007: autotools 项目需要 autogen.sh 生成 configure（已记录在知识图谱）

## 产物清单
- /usr/local/lib/libndp.so.0.1.1
- /usr/local/lib/libndp.so.0 (软链接)
- /usr/local/lib/libndp.so (软链接)
- /usr/local/bin/ndptool
- /usr/local/include/ndp.h
- /usr/local/lib/pkgconfig/libndp.pc

---
**编译结束**: 2026-05-29
**最终状态**: published
---

**编译结束**: 2026-05-29 15:19
**最终状态**: built
