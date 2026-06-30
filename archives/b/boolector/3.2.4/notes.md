# boolector 3.2.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

boolector 使用 CMake 构建系统，内含 3 个 bundled 依赖库需先编译：

### 1. 编译 bundled 依赖

**Btor2Tools** (cmake):
```bash
cd deps/btor2tools/build
cmake .. -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j2
```

**CaDiCaL** (configure):
```bash
cd deps/cadical
./configure
make -j2
```

**Lingeling** (configure.sh):
```bash
cd deps/lingeling
./configure.sh -fPIC
make -j2
```

### 2. 编译 boolector 主项目

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DTESTING=OFF \
  -DUSE_MINISAT=OFF -DUSE_CMS=OFF -DUSE_PICOSAT=OFF \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS 平台 | CMake 无 HarmonyOS platform module (E092) | 设置 CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | cmake_minimum_required(VERSION 3.3) 与 CMake 4.x 不兼容 (E103) | CMake 4.0 移除了对 3.3 的兼容 | replace_in_file 改为 3.5 + CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | GitHub SSL 证书问题 | 系统缺少 CA 证书 | 设置 SSL_CERT_FILE 和 CURL_CA_BUNDLE 环境变量 |
| 4 | GitHub 连接超时 | 网络不稳定 | gh-proxy.com 镜像作为 fallback |
| 5 | test_package 链接失败: undefined __cxa_allocate_exception | libboolector.a 含 C++ 对象，test_package 是 C 程序 | package_info() system_libs 添加 "c++" |
| 6 | MiniSat 系统依赖 | 系统有 libminisat.a 但 CI 环境可能没有 | USE_MINISAT=OFF, USE_CMS=OFF, USE_PICOSAT=OFF |

## 源码修改

无补丁文件。conanfile.py 的 build() 中使用 `replace_in_file` 在构建时修改 CMakeLists.txt 的 `cmake_minimum_required` 从 3.3 改为 3.5（E103 兼容性修复），非持久化修改。

## 依赖版本

| 依赖 | 来源 | 版本/commit |
|------|------|------------|
| Btor2Tools | bundled (GitHub) | commit 037f1fa88fb439dca6f648ad48a3463256d69d8b |
| CaDiCaL | bundled (GitHub) | commit cb89cbfa16f47cb7bf1ec6ad9855e7b6d5203c18 |
| Lingeling | bundled (GitHub) | commit 7d5db72420b95ab356c98ca7f7a4681ed2c59c70 |

## 验证结果

```
conan-verify 8 道门禁: 全部 PASS (Verdict: PASS)
boolector --version: 3.2.4
SMT2 sat 求解: sat (退出码 10)
SMT2 unsat 求解: unsat (退出码 20)
静态链接: ELF 64-bit arm64, static, not stripped
```

## 注意事项

1. boolector 的 3 个依赖库 (Btor2Tools/CaDiCaL/Lingeling) 在 conanfile.py 的 build() 中通过 subprocess 从 GitHub 下载并编译，CI 环境需要网络访问
2. 编译时间较长（约 15 分钟），主要耗时在 200+ 个 C++ 源文件编译
3. btormc 二进制（模型检查器）也被打包到 Conan 包的 bin/ 目录中
4. conandata.yml 的 patches 为空，所有修改在 conanfile.py 的 build() 中运行时完成

---

**编译结束**: 2026-06-29 15:34
**最终状态**: published
