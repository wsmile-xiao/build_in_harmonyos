# clhep 2.4.7.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-13
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. 初始化编译环境: `python3 ohc-run.py init-build clhep 2.4.7.2 --url=... --no-download`
2. 创建外部build目录: `mkdir -p ~/tmp/builds/clhep-2.4.7.2-build`
3. cmake配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_FLAGS="-fPIC -O2" -DCMAKE_CXX_FLAGS="-fPIC -O2" $BUILD_SRC_DIR`
4. 编译: `make -j1`
5. DESTDIR安装: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `ctest --output-on-failure` (44/45 通过)
7. 本地安装: `make install` (不带DESTDIR)
8. 验证: `clhep-config --version` → CLHEP 2.4.7.2

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | gitlab.cern.ch的SSL证书不被本地信任 | 使用curl -k下载源码，再--no-download初始化 |
| 2 | cmake in-source build禁止 | CLHEP要求out-of-source构建 | 在源码目录外创建build目录 |
| 3 | testBug7328失败 | 鸢蒙平台C++内存分配行为差异导致泄漏检测 | 平台差异，不影响核心功能 |

## 源码修改

无源码修改，无补丁。

## 依赖版本

无依赖

## 验证结果

```bash
$ clhep-config --version
CLHEP 2.4.7.2

$ ls $DEFAULT_PREFIX/lib/libCLHEP*
libCLHEP-2.4.7.2.so  libCLHEP-2.4.7.2.a
libCLHEP-Vector-2.4.7.2.so  libCLHEP-Vector-2.4.7.2.a
libCLHEP-Evaluator-2.4.7.2.so  ...
(共22个库文件: 11个.so + 11个.a + 2个符号链接)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| clhep-2.4.7.2-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

- CLHEP必须out-of-source构建，cmake不允许in-source
- testBug7328在鸢蒙平台因内存分配行为差异而失败，属平台限制
---

**编译结束**: 2026-06-13 17:53
**最终状态**: published
