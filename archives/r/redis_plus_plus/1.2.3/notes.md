# redis_plus_plus 1.2.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-24
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

### 前置依赖：编译 hiredis 1.2.0
redis_plus_plus 依赖 hiredis C 库。cmd-pkgs 无预编译包，手动编译：
```bash
# 通过 gh-proxy.com 镜像下载 hiredis 1.2.0 源码
cd ~/tmp/hiredis-1.2.0
# 修复 test.c 未初始化变量（-Werror 导致编译失败）
sed -i 's/redisContext \*c;/redisContext *c = NULL;/' test.c
PREFIX=~/usr/local make -j1 && make install
```

### 编译 redis_plus_plus 1.2.3
```bash
# 通过 gh-proxy.com 镜像下载源码
cd ~/tmp/builds/redis_plus_plus-1.2.3.work
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=~/usr/local \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DREDIS_PLUS_PLUS_BUILD_TEST=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-fPIC -O2"
make -j1
make install DESTDIR=~/tmp/test-install-redis_plus_plus-1.2.3  # staging
make install                                                   # 本地
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络无法直连 github.com | 使用 gh-proxy.com 镜像下载 |
| 2 | hiredis 缺失 | redis_plus_plus 的 C 依赖未安装 | 手动编译 hiredis 1.2.0 |
| 3 | hiredis test.c 编译失败 | `-Werror` 将未初始化变量警告变为错误 | `redisContext *c = NULL;` 初始化 |
| 4 | CMake 配置失败 | CMakeLists.txt 声明最低 3.1，CMake 4.x 不再兼容 < 3.5 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| hiredis | 1.2.0 | 手动编译安装 |

## 验证结果

### 动态库链接测试
```bash
$ clang++ -std=c++11 -I~/usr/local/include -L~/usr/local/lib test_link.cpp -lredis++ -lhiredis -o test_link
$ ./test_link
[OK] ConnectionOptions: host=127.0.0.1 port=6379
[OK] ConnectionPoolOptions: size=5
[OK] Redis 对象创建成功
[OK] redis-plus-plus 1.2.3 链接验证通过
EXIT_CODE=0
```

### 静态库链接测试
```bash
$ clang++ -std=c++11 -I~/usr/local/include test_link.cpp ~/usr/local/lib/libredis++.a ~/usr/local/lib/libhiredis.a -o test_link_static
$ ./test_link_static
[OK] redis-plus-plus 1.2.3 链接验证通过
EXIT_CODE=0
```

### pkg-config 验证
```bash
$ pkg-config --modversion redis++    → 1.2.3
$ pkg-config --libs redis++           → -lredis++ -lhiredis
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| redis_plus_plus-1.2.3-ohos-aarch64.tar.gz | 2.3MB | 预编译包（含 libredis++.a/.so + hiredis + 头文件） |
| redis_plus_plus-1.2.3-ohos-aarch64-debug.tar.gz | 403KB | 调试符号包 |

## 注意事项

- 源码下载需使用 GitHub 镜像（gh-proxy.com），直连 GitHub 超时
- hiredis 依赖需先单独编译安装
- CMake 4.x 编译时必须加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 单元测试需要运行 Redis 实例，本次跳过，改用链接验证测试替代
- 共享库 libredis++.so 依赖 libhiredis.so.1.1.0，打包时已自动收集
---

**编译结束**: 2026-06-24 14:59
**最终状态**: published
