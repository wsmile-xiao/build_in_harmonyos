# rdma-core 56.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
mkdir build && cd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_RESOLVE_NEIGH=0 \
    -DNO_PYVERBS=1 \
    -DNO_MAN_PAGES=1 \
    -DENABLE_STATIC=1 \
    -DNO_COMPAT_SYMS=1 \
    -DENABLE_VALGRIND=0 \
    -DENABLE_WERROR=OFF \
    -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libnl-3.0 not found | OHOS 无 libnl 包 | 设置 ENABLE_RESOLVE_NEIGH=0 禁用 libnl 依赖 |
| 2 | Cython not found | OHOS CI 无 Cython | 设置 NO_PYVERBS=1 禁用 Python 绑定 |
| 3 | pandoc not found | OHOS CI 无 pandoc | 设置 NO_MAN_PAGES=1 禁用 man 页面 |
| 4 | GNU symbol versioning | OHOS 使用 musl libc，不支持 GNU symver | 设置 NO_COMPAT_SYMS=1 |
| 5 | valgrind headers missing | OHOS 无 valgrind | 设置 ENABLE_VALGRIND=0 |

## 依赖版本

- 无外部 conan 依赖
- 系统依赖: pthread, librt, libdl (系统库)

## 验证结果

```bash
# test_package 验证 libibverbs API 可调用
./test_rdma_core
# 输出: rdma-core libibverbs API test: PASS
```

## 注意事项

- rdma-core 是 Linux InfiniBand/RDMA 子系统的用户空间库
- OHOS 可能没有 RDMA 硬件，ibv_get_device_list 返回 NULL 是正常的
- 如需 libnl 支持，需要先适配 libnl 包并设置 enable_resolve_neigh=True
---

**编译结束**: 2026-09-04 05:42
**最终状态**: built
