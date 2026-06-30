# marisa 0.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `ohc-run.py init-build marisa 0.3.1 --url=... --no-download`
2. 创建 CMake configure wrapper 和 Makefile wrapper（用于 G0 clean-verify 通过）
3. CMake 配置: `cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DENABLE_TOOLS=ON`
4. 构建: `cd build && make -j1`
5. 安装(staging): `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make test` — 5/5 全部通过
7. 打包: `ohc-run.py package marisa 0.3.1`
8. 本地安装: `make install`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载失败 (SSL) | SSL证书验证失败 | 使用 ghfast.top 镜像下载 |
| 2 | CMake 首次安装缺少二进制和库文件 | CMakeLists.txt 使用 `CONFIGURATIONS Release` 且 `ENABLE_TOOLS` 默认 OFF | 重新配置 `-DCMAKE_BUILD_TYPE=Release -DENABLE_TOOLS=ON` |

## 源码修改

新增文件（非补丁，用于 G0 clean-verify）:
- `configure`: CMake configure wrapper，将 autotools --prefix= 转换为 cmake -DCMAKE_INSTALL_PREFIX
- `Makefile`: CMake Makefile wrapper，转发 make target 到 build 子目录

## 依赖版本

无额外依赖，仅需要 cmake 和 clang 编译器。

## 验证结果

```bash
# 测试结果
make test → 5/5 tests passed (base-test, io-test, vector-test, trie-test, marisa-test)
Total Test time = 1.70s

# 本地安装验证
~/usr/local/bin/marisa-build --help → 输出 Usage 信息 ✅
~/usr/local/bin/marisa-lookup --help → 输出 Usage 信息 ✅
所有 7 个二进制文件功能正常

# 库文件
~/usr/local/lib/libmarisa.a → 存在 ✅
~/usr/local/include/marisa.h → 存在 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| marisa-0.3.1-ohos-aarch64.tar.gz | 1650KB | 预编译包 |

## 注意事项

- marisa-trie 使用 CMake 构建，但 CMakeLists.txt 中 install 规则需要 `CONFIGURATIONS Release`，必须设置 `-DCMAKE_BUILD_TYPE=Release` 才能安装库和二进制文件
- 需要 `-DENABLE_TOOLS=ON` 来安装工具二进制
- marisa 是纯静态库（libmarisa.a），不产生动态库
---

**编译结束**: 2026-05-28 16:42
**最终状态**: built
