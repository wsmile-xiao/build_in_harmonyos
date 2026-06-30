# gnu-getopt 1.1.6 编译笔记

## 编译信息
- **日期**: 2026-05-19
- **源码**: https://github.com/sabotage-linux/gnu-getopt (master 分支)
- **构建系统**: 简单 Makefile（无 configure）

## 编译过程

### Step 1: 源码获取
- Savannah 官方源 URL 404/超时
- 从 GitHub 镜像 sabotage-linux/gnu-getopt 下载成功

### Step 2: 编译
```bash
make CFLAGS="-O2 -fPIC"
make prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install
```

### 编译结果
- libgnu_getopt.a (10712 bytes)
- 无可执行文件，仅静态库

### 注意事项
- 这是 musl 兼容版本，非官方 GNU getopt
- 编译非常简单，无依赖
- 用法：CFLAGS="-Dgetopt=gnu_getopt" LDFLAGS="-lgnu_getopt"

## 质量门禁
- G0: ✅ 干净构建验证通过
- G1: ✅ 静态库完整性通过
- G2: ✅ 无可执行文件，仅库文件
- G3: ✅ 无 RPATH 问题（静态库）
- G4: ✅ 归档完整性通过

## 知识提取
无新错误模式发现
---

**编译结束**: 2026-05-19 19:36
**最终状态**: published
