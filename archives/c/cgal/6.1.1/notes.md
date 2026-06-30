# CGAL 6.1.1 编译笔记

## 编译信息
- **日期**: 2026-05-21
- **构建系统**: CMake 4.1.2
- **编译器**: Clang 15.0.4
- **状态**: built (header-only)

## 编译过程

### 1. 解压源码
从用户下载的 tar.xz 文件解压到 ~/builds/cgal-6.1.1.work

### 2. 配置 CMake
```bash
cmake ~/builds/cgal-6.1.1.work \
  -DCMAKE_INSTALL_PREFIX=~/usr/local \
  -DCMAKE_BUILD_TYPE=Release
```

CMake 自动检测到：
- GMP 6.3.0（已安装）
- MPFR 4.2.1（已安装）

### 3. 编译安装
CGAL 是 header-only 库，编译过程简单：
```bash
make
make install DESTDIR=~/tmp/test-install-cgal-6.1.1
make install  # 安装到 ~/usr/local
```

### 4. 验证安装
安装结果：
- include/CGAL: 64MB（141 个子目录，数千个头文件）
- lib/cmake/CGAL: 1.5MB（CMake 配置文件）
- share/doc/CGAL: 404KB（文档）

## 依赖
- GMP 6.3.0 ✅
- MPFR 4.2.1 ✅
- Boost（可选，未安装）
- zlib（可选，已安装）

## 特性
- CGAL 是 Computational Geometry Algorithms Library
- 主要用于几何计算：三角剖分、多边形处理、网格生成等
- header-only 设计，无需链接库文件

## 知识提取
1. CGAL 是 header-only 库，无二进制产物
2. 依赖 GMP 和 MPFR（精确算术）
3. CMake 配置会自动检测依赖
4. 需要 CMake 3.12+

---
**编译结束**: 2026-05-21 10:40
**最终状态**: built (header-only，无 packaging)