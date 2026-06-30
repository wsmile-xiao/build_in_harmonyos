# bkcrack 1.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `codeload.github.com/kimci86/bkcrack/tar.gz/v1.8.1` (GitHub直接访问超时，通过codeload CDN下载成功)
2. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build bkcrack 1.8.1 --url=...`
3. 源码修改: 修复CMake安装路径（将DESTINATION .改为DESTINATION bin/share/bkcrack）
4. cmake配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBKCRACK_BUILD_TESTING=ON ..`
5. cmake构建: `cmake --build . -j2`
6. 安装到staging: `DESTDIR=$TEST_PREFIX cmake --install .`
7. 测试: `ctest --output-on-failure` → 31/31 tests passed
8. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package bkcrack 1.8.1`
9. 本地安装: `cmake --install .` (无DESTDIR)
10. 验证: `~/usr/local/bin/bkcrack --version` → `bkcrack 1.8.1 - 2025-10-25`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载超时 | 网络无法直接连接github.com | 使用codeload.github.com CDN下载 |
| 2 | Savannah SSL/404 | Savannah上不存在bkcrack 1.8.1 | 使用GitHub codeload CDN替代 |
| 3 | cmake install DESTDIR参数 | cmake --install不支持DESTDIR作为位置参数 | 使用DESTDIR环境变量 |
| 4 | 安装路径不规范 | bkcrack原始DESTINATION为`.`(prefix根) | 补丁修改为bin/和share/bkcrack/ |
| 5 | manifest缺少build_system | init-build猜测为autotools | 手动添加build_system: cmake |

## 源码修改

- `0001-CMakeLists.txt.patch`: 修复顶层CMakeLists.txt安装路径，example/tools/readme/license从`.`改到`share/bkcrack`
- `0002-src-CMakeLists.txt.patch`: 修复src/CMakeLists.txt安装路径，binary从`.`改到`bin`

## 依赖版本

- clang 15.0.4
- cmake 4.1.2
- pthread (系统自带)

## 验证结果

```bash
$ ~/usr/local/bin/bkcrack --version
bkcrack 1.8.1 - 2025-10-25

$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 31
Total Test time (real) = 2.10 sec
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bkcrack-1.8.1-ohos-aarch64.tar.gz | 360KB | 预编译包 |
| bkcrack-1.8.1-ohos-aarch64-debug.tar.gz | 92KB | 调试符号包 |

## 注意事项

- bkcrack是纯C++工具，无外部库依赖，使用pthread即可
- cmake在HarmonyOS上会报"System is unknown"警告，但不影响编译
- bkcrack原始安装布局将binary直接放在prefix根目录，需补丁修正为标准bin/路径
---

**编译结束**: 2026-06-04 15:21
**最终状态**: published
