# libucontext 1.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**：从 GitHub 下载 libucontext v1.2 tarball
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libucontext 1.2 --url=https://github.com/kaniini/libucontext/archive/refs/tags/v1.2.tar.gz
   ```

2. **编译**：使用 Makefile 构建，指定架构和安装路径
   ```bash
   make ARCH=aarch64 LIBDIR=$DEFAULT_PREFIX/lib INCLUDEDIR=$DEFAULT_PREFIX/include PKGCONFIGDIR=$DEFAULT_PREFIX/lib/pkgconfig -j2
   ```

   libucontext 使用纯 Makefile 构建系统，不支持 configure 脚本。通过 Makefile 参数控制：
   - ARCH: 目标架构（aarch64）
   - LIBDIR: 库安装路径
   - INCLUDEDIR: 头文件安装路径
   - PKGCONFIGDIR: pkg-config 文件路径

3. **Staging 安装**：使用 DESTDIR 模式
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

4. **测试**：运行完整的测试套件
   ```bash
   make check
   ```

   测试结果：全部通过（check_libucontext_posix、check_libucontext_bare_posixabi、check_libucontext）

5. **本地安装验证**：安装到 DEFAULT_PREFIX
   ```bash
   make install
   ```

6. **功能验证**：编译并运行测试程序
   ```bash
   pkg-config --modversion libucontext  # 输出: 1.2
   pkg-config --libs libucontext         # 输出: -L$DEFAULT_PREFIX/lib -lucontext
   pkg-config --cflags libucontext       # 输出: -I$DEFAULT_PREFIX/include
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 未找到 libucontext URL | software-registry.yaml 中无记录 | 手动指定 URL: --url=https://github.com/kaniini/libucontext/archive/refs/tags/v1.2.tar.gz |
| 2 | verify-build G4 失败：缺少 build_system 字段 | manifest.yaml 模板问题 | 在版本级 manifest.yaml 中添加 build_system: makefile 字段；创建软件级 manifest.yaml 和 README.md |
| 3 | 测试程序运行失败：找不到 libucontext.so.1 | 库文件未 ELF 签名 | 使用 ohc-run.py sign-elf 对库文件签名 |

## 源码修改

无补丁。libucontext aarch64 架构为 tier 1 支持，无需修改源码。

## 依赖版本

- 无外部依赖（纯汇编和 C 实现）

## 验证结果

```bash
# Staging 验证
BIN_COUNT=0 LIB_COUNT=5  # 库文件完整

# 功能验证
pkg-config --modversion libucontext
1.2

# 测试程序验证
./test_ucontext
Testing libucontext installation
getcontext succeeded
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libucontext-1.2-ohos-aarch64.tar.gz | 260KB | 预编译包（包含共享库、静态库、头文件） |

## 注意事项

1. **构建系统识别**：libucontext 使用纯 Makefile，不是 autotools。init-build 检测为 autotools，但实际应使用 build_system: makefile
2. **ELF 签名必要性**：鸿蒙系统要求所有可执行的 ELF 文件（包括动态库）必须签名才能加载
3. **库类型软件验证**：库类型软件无 bin 目录下的可执行文件，G2 功能验证使用 pkg-config 或编译测试程序
4. **平台支持**：aarch64 为 tier 1 架构，支持完整，包括 hard-float、freestanding 模式、common trampoline

---
**编译结束**: 2026-06-12 17:19
**最终状态**: built