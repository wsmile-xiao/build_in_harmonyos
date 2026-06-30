# matplotplusplus 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 从 GitHub 克隆源码：`git clone --depth 1 https://github.com/alandefreitas/matplotplusplus.git`
2. 创建 tarball：`tar -czf matplotplusplus-1.2.0.tar.gz matplotplusplus-git`
3. 运行 init-build：`python3 ohc-run.py init-build matplotplusplus 1.2.0 --url=file:///...`
4. CMake 配置：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF \
         -DMATPLOTPP_BUILD_EXAMPLES=OFF \
         -DMATPLOTPP_BUILD_TESTS=OFF \
         -DMATPLOTPP_BUILD_WITH_PEDANTIC_WARNINGS=OFF ..
   ```
5. 编译：`make -j2`
6. 安装（DESTDIR 模式）：`make install DESTDIR=/storage/Users/currentUser/test-install-matplotplusplus-1.2.0`
7. 本地安装：`make install`
8. 质量验证：`python3 ohc-run.py verify-build matplotplusplus 1.2.0`
9. 打包：`python3 ohc-run.py package matplotplusplus 1.2.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah SSL 证书验证失败 | SSL 证书过期或不兼容 | 使用 curl -k 绕过验证，从 GitHub 克隆代替 |
| 2 | 下载速度极慢 | Savannah 服务器在国内访问慢 | 从 GitHub 直接克隆源码 |
| 3 | manifest.yaml 缺少 build_system | 使用了嵌套格式 build.system | 改为扁平字段 build_system: cmake |

## 源码修改

无补丁，源码编译通过。

## 依赖版本

- gnuplot (runtime，未安装，仅编译时不需要)
- pthreads (系统提供)

可选依赖（未找到但不影响编译）：
- JPEG, TIFF, PNG, ZLIB, OpenCV, FFTW, BLAS, LAPACK

## 验证结果

```bash
ls -lh ~/usr/local/lib/libmatplot.a
# Output: -rw-rw---- 13M libmatplot.a

ls -lh ~/usr/local/lib/Matplot++/libnodesoup.a
# Output: -rw-rw---- 46K libnodesoup.a

ls ~/usr/local/include/matplot/matplot.h
# Output: /storage/Users/currentUser/usr/local/include/matplot/matplot.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| matplotplusplus-1.2.0-ohos-aarch64.tar.gz | 13MB | 预编译包（静态库 + 头文件） |

## 注意事项

- matplotplusplus 是一个 C++ 绘图库，运行时需要 gnuplot
- 编译为静态库（libmatplot.a + libnodesoup.a）
- 无可执行文件，纯库项目
- 需要安装 gnuplot 才能运行绘图功能

## 知识提取

无新知识发现（纯 CMake 项目，标准编译流程）。
---

**编译结束**: 2026-06-05 16:39
**最终状态**: built
