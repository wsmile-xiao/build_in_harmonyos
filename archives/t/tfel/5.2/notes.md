# tfel 5.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

### 1. 源码获取
由于GitHub网络连接失败，使用git clone从GitHub仓库获取最新代码：
```bash
cd ~/tmp/builds
git clone --depth 1 https://github.com/thelfer/tfel.git tfel-5.2-src
tar czf tfel-5.2.tar.gz tfel-5.2-src
```

### 2. 初始化编译环境
```bash
python3 ohc-run.py init-build tfel 5.2 --url=file://~/tmp/builds/tfel-5.2.tar.gz
```

### 3. CMake配置
TFEL使用CMake构建系统，需要特别配置以适配HarmonyOS：
```bash
export DEFAULT_PREFIX="~/usr/local"
export LDFLAGS="-L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos -lc++ -lc++abi"

cmake -B build -S . \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -Denable-python=OFF \
  -Denable-fortran=OFF \
  -Denable-java=OFF \
  -Denable-testing=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_EXE_LINKER_FLAGS="$LDFLAGS" \
  -DCMAKE_SHARED_LINKER_FLAGS="$LDFLAGS" \
  -DUNIX=TRUE
```

### 4. 编译
```bash
cd build
make -j2
```

### 5. 安装
使用DESTDIR模式进行staging安装：
```bash
export TEST_PREFIX="~/test-install-tfel-5.2"
DESTDIR=$TEST_PREFIX cmake --install .
```

本地安装验证：
```bash
cmake --install .
~/usr/local/bin/mfront --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载失败 | SSL证书验证失败 + 网络连接超时 | 使用git clone获取源码 |
| 2 | 链接错误：undefined symbol: __cxa_allocate_exception | 缺少libc++abi库链接 | 添加LDFLAGS链接libc++和libc++abi |
| 3 | 链接错误：undefined symbol: SignalManager | CMake未识别HarmonyOS为UNIX系统 | 配置时添加-DUNIX=TRUE参数 |
| 4 | CMake提示"System is unknown to cmake" | HarmonyOS不在CMake已知平台列表中 | 添加-DUNIX=TRUE，不影响编译 |

## 关键知识点

### HarmonyOS C++编译适配要点
1. **libc++和libc++abi库位置**：
   - 路径：`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos`
   - 必须链接：`-lc++ -lc++abi`
   - 否则会出现C++异常和标准库符号缺失

2. **CMake平台识别问题**：
   - HarmonyOS目标：`aarch64-unknown-linux-ohos`
   - CMake无法自动识别为UNIX系统
   - 需要手动设置：`-DUNIX=TRUE`
   - 影响：SignalManager等UNIX特定代码的编译

3. **静态库编译建议**：
   - TFEL编译为静态库更稳定（`BUILD_SHARED_LIBS=OFF`）
   - 避免动态库的RPATH和签名问题

## 源码修改

无源码修改，仅通过CMake配置参数适配。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1
- libc++: 鸿蒙SDK内置
- libc++abi: 鸿蒙SDK内置

## 验证结果

```bash
$ ~/usr/local/bin/mfront --version
tfel
Version : 5.2.0-dev
Compiled with  on  -
Please submit bug at tfel-contact@cea.fr

$ ~/usr/local/bin/tfel-config --version
tfel-config 5.2.0-dev (git hash: f6c7337)
```

编译产物：
- mfront: 9.1MB
- tfel-config: 66KB
- 其他工具：mtest, mfront-query, mfront-doc, tfel-check等

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tfel-5.2-ohos-aarch64.tar.gz | 87MB | 预编译包（包含所有工具和库） |
| libTFEL*.a | 21个静态库 | TFEL核心库 |
| bin/* | 11个可执行文件 | mfront/mtest等工具 |

## 注意事项

1. **网络问题**：GitHub源码下载可能失败，建议使用git clone或本地缓存
2. **C++库链接**：必须显式链接libc++和libc++abi，否则链接失败
3. **UNIX平台识别**：必须设置-DUNIX=TRUE才能编译SignalManager等组件
4. **版本号**：实际编译的是5.2.0-dev（从master分支克隆）
5. **mgis依赖**：TFEL是mgis的核心依赖库，编译成功后可用于mgis编译

---
**编译结束**: 2026-06-15 12:30
**最终状态**: built