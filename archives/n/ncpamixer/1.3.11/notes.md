# ncpamixer 1.3.11 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build
cmake --install build --prefix $DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | -Werror 导致编译失败 | OHOS 平台头文件触发 warning | 注释掉 `-Werror` 编译选项 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| src/CMakeLists.txt | 注释掉 `-Werror` 选项，保留 `-Wall -Wpedantic` |

---

**编译结束**: 2026-06-01
**最终状态**: built