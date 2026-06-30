# volk 3.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

1. 源码获取：从 Gitee 镜像下载 volk-3.3.0.tar.gz
2. 依赖安装：
   - fmt 10.2.1（手动编译安装）
   - Python mako 模板库（pip install mako）
3. CMake 配置：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
            -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local \
            -DCMAKE_BUILD_TYPE=Release \
            -DENABLE_TESTING=OFF \
            -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
            -DCMAKE_EXE_LINKER_FLAGS="-lc++" \
            -DCMAKE_INSTALL_RPATH=/storage/Users/currentUser/usr/local/lib \
            -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE
   ```
4. 编译：make -j4
5. 安装：make install DESTDIR=$TEST_PREFIX（staging）和 make install（本地）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FetchContent 失败下载 fmt | GitHub 网络不可达 | 手动下载 fmt 并编译安装到 ~/usr/local |
| 2 | 缺少 mako 模板库 | Python 依赖未安装 | pip install mako |
| 3 | C++ 标准库链接失败 | 未指定 libc++ 链接 | 添加 CMAKE_CXX_FLAGS="-stdlib=libc++" |
| 4 | RPATH 使用相对路径 | cmake 默认设置 | 需要从 bin 目录运行，或设置 LD_LIBRARY_PATH |

## 源码修改

无源码修改，仅通过 CMake 参数适配。

## 依赖版本

- fmt: 10.2.1（手动编译）
- Python mako: 1.3.12
- libc++: Clang 15.0.4 内置

## 验证结果

```bash
cd /storage/Users/currentUser/usr/local/bin
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos ./volk-config-info --version
# 输出: 3.3.0

./volk_profile --help
# 输出帮助信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| volk-3.3.0-ohos-aarch64.tar.gz | 4.3 MB | 预编译包 |
| libvolk.so | 1.1 MB | 共享库 |
| volk-config-info | 55 KB | 配置信息工具 |
| volk_profile | 477 KB | 性能分析工具 |

## 注意事项

1. 二进制依赖相对路径 RPATH (`../lib/libvolk.so`)，需要从 bin 目录运行
2. 运行时需要设置 LD_LIBRARY_PATH 包含 libc++_shared.so 路径
3. 无 ELF 签名（签名工具不支持库文件）

---

**编译结束**: 2026-06-15 16:17
**最终状态**: built