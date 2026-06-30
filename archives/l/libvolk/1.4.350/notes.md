# libvolk 1.4.350 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译：`ohc-run.py init-build libvolk 1.4.350 --url=https://github.com/zeux/volk/archive/refs/tags/1.4.350.tar.gz`
2. 手动配置 cmake（需要启用 VOLK_INSTALL）：
   ```bash
   cd ~/builds/libvolk-1.4.350.work
   rm -rf build
   mkdir build
   cd build
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release -DVOLK_INSTALL=ON ..
   ```
3. 编译：`make -j2`
4. 安装到 staging：`make install DESTDIR=/storage/Users/currentUser/test-install-libvolk-1.4.350`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install 失败（No rule to make target 'install'） | libvolk 默认不启用安装规则 | cmake 配置时添加 `-DVOLK_INSTALL=ON` 参数 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
ls -la /storage/Users/currentUser/test-install-libvolk-1.4.350/storage/Users/currentUser/usr/local/lib/libvolk.a
# -rw-rw---- 1 20001006 file_manager 379376 2026-06-05 10:51 libvolk.a

ls -la /storage/Users/currentUser/test-install-libvolk-1.4.350/storage/Users/currentUser/usr/local/include/
# volk.c (341133 bytes)
# volk.h (190951 bytes)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libvolk.a | 379376 bytes | Vulkan meta-loader 静态库 |
| volk.h | 190951 bytes | Vulkan 函数指针头文件 |
| volk.c | 341133 bytes | 可选的源文件（用于 header-only 模式） |

## 注意事项

1. libvolk 是 Vulkan 的 meta-loader，用于动态加载 Vulkan entrypoints
2. 默认情况下，cmake 不生成 install 规则，需要显式启用 `-DVOLK_INSTALL=ON`
3. 编译产物是静态库，不是可执行文件，无需运行测试
4. 可以通过三种方式使用：
   - 链接静态库 libvolk.a
   - 直接编译 volk.c
   - header-only 模式（定义 VOLK_IMPLEMENTATION）
---

**编译结束**: 2026-06-05 10:53
**最终状态**: built
