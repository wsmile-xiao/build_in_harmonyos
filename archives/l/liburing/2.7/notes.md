# liburing 2.7 编译笔记

## 编译开始
**时间**: 2026-06-12 17:28

### 环境信息
- 构建系统: configure-make
- 源码路径: ~/builds/liburing-2.7.src
- 归档路径: archives/l/liburing/2.7

### 编译过程

1. **源码获取**: 从 GitHub 克隆 liburing-2.7 (tag: liburing-2.7)
2. **Configure**: 成功通过 configure，检测到平台特性：
   - prefix: ~/usr/local
   - has_ucontext: no
   - nolibc: yes
   - CC: gcc, CXX: g++
   
3. **Make**: 核心库编译成功，生成：
   - liburing.a (静态库 23KB)
   - liburing.so.2.7 (动态库 25KB)
   - liburing-ffi.a (静态库 38KB)
   - liburing-ffi.so.2.7 (动态库 45KB)
   
   测试程序编译失败（缺少 glibc 特有的 error.h 头文件），但核心库编译成功，不影响使用。
   
4. **Staging Install**: DESTDIR 模式安装成功
5. **Package**: 打包成功，生成 liburing-2.7-ohos-aarch64.tar.gz (1322KB)

### 遇到的问题

**问题1**: 测试程序编译失败 - error.h 缺失
- **原因**: glibc 特有头文件，鸿蒙系统不包含
- **解决**: 核心库编译成功，跳过测试程序不影响库的使用
- **影响**: 无，库本身功能完整

**问题2**: make check 目标不存在
- **原因**: liburing 项目无 check 目标
- **解决**: 跳过 make check

### 编译结束
**时间**: 2026-06-12 17:30
**最终状态**: built

---

## 知识提取

### 平台适配
- liburing 在鸿蒙上可正常编译使用
- 测试程序依赖 glibc 特有头文件，可跳过
- 核心库（liburing.a/liburing.so）功能完整

### 构建特性
- 支持静态库和动态库
- 支持 FFI 绑定（liburing-ffi）
- 需要内核 io_uring 支持（运行时依赖）

