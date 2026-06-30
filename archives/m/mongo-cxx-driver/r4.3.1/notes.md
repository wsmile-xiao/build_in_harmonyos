# mongo-cxx-driver r4.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载mongo-cxx-driver r4.3.1源码tarball
2. 先编译并安装mongo-c-driver 2.3.0（r4.3.1需要C Driver >= 2.3.0）
3. cmake配置：`cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=OFF -DBUILD_TESTING=OFF -DBSONCXX_POLY_USE_IMPLS=ON -DBUILD_VERSION=r4.3.1`
4. make -j4编译
5. cmake --install安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BUILD_VERSION无法自动计算 | 从tarball构建时没有git仓库，calc_release_version.py脚本调用git失败 | 使用-DBUILD_VERSION=r4.3.1显式指定版本号 |
| 2 | 需要C Driver 2.3.0+ | r4.3.1最低要求C Driver 2.3.0，系统中只有1.30.8 | 先编译安装C Driver 2.3.0 |
| 3 | make install触发重新configure | make install可能导致cmake重新configure失败 | 使用cmake --install代替make install |

## 依赖版本

- mongo-c-driver 2.3.0 (编译安装)
- OpenSSL 3.5.6

## 验证结果

```bash
ls ~/usr/local/lib/libmongocxx.so ~/usr/local/lib/libbsoncxx.so
# libmongocxx.so  libbsoncxx.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mongo-cxx-driver-r4.3.1-ohos-aarch64.tar.gz | ~1MB | 运行时文件 |
| mongo-cxx-driver-r4.3.1-ohos-aarch64-debug.tar.gz | ~200KB | 调试符号 |

## 注意事项

- r4.3.1需要C Driver 2.3.0+，与1.x版本的C驱动不兼容
- C Driver 2.x的库文件名是libmongoc2.so/libbson2.so，不同于1.x的libmongoc-1.0.so/libbson-1.0.so

---
**编译结束**: 2026-06-09 12:30
**最终状态**: built