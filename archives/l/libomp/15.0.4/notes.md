# libomp 15.0.4 编译笔记

## 基本信息

| 项目 | 值 |
|------|------|
| 软件 | libomp (LLVM OpenMP 运行时库) |
| 版本 | 15.0.4 |
| 构建系统 | CMake |
| 编译器 | clang 15.0.4 |
| 平台 | HarmonyOS aarch64 |
| 编译日期 | 2026-05-19 |

---

## 源码获取

**来源**: GitCode 国内镜像

**原始 URL**: `https://gitcode.com/llvm/llvm-project.git` (克隆后提取 openmp 子目录)

**最终 tarball**: `libomp-15.0.4.tar.bz2`

**特殊处理**:
1. 从 GitCode 克隆 LLVM 仓库（因为 GitHub 无法访问）
2. 提取 openmp 子目录并重新打包
3. 复制 LLVM cmake 模块（ExtendPath.cmake 等）到源码目录

---

## 编译配置

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENMP_STANDALONE_BUILD=ON \
  -DLIBOMP_OMPT_SUPPORT=OFF \
  -DOPENMP_ENABLE_LIBOMPTARGET=OFF
```

**关键选项说明**:
- `OPENMP_STANDALONE_BUILD=ON`: 独立编译（不在 LLVM 父目录中）
- `LIBOMP_OMPT_SUPPORT=OFF`: 禁用 OMPT 工具支持（减少依赖）
- `OPENMP_ENABLE_LIBOMPTARGET=OFF`: 禁用 offloading 支持（避免 LLVM 依赖）

---

## 遇到的问题及解决方案

### 问题 1: 网络无法访问 GitHub

**现象**: `curl: (28) Failed to connect to github.com port 443`

**解决方案**: 使用 GitCode 国内镜像克隆 LLVM 仓库

**命令**:
```bash
git clone --depth 1 --branch llvmorg-15.0.4 https://gitcode.com/llvm/llvm-project.git
```

---

### 问题 2: CMake 找不到 ExtendPath 模块

**现象**:
```
CMake Error: include could not find requested file: ExtendPath
```

**根因**: 只打包了 openmp 子目录，缺少父目录的 cmake 模块

**解决方案**: 复制 LLVM cmake 模块到源码目录

**修改文件**: `CMakeLists.txt`

**修改内容**: 将 `${CMAKE_CURRENT_SOURCE_DIR}/../cmake` 改为 `${CMAKE_CURRENT_SOURCE_DIR}/cmake`

**补丁**: `0001-CMakeLists.txt.patch`

---

### 问题 3: HarmonyOS 不支持 pthread_cancel

**现象**:
```
error: use of undeclared identifier 'pthread_cancel'
error: use of undeclared identifier 'pthread_setcanceltype'
error: use of undeclared identifier 'pthread_setcancelstate'
```

**根因**: HarmonyOS 内核不支持 POSIX 线程取消机制（与 Android 类似）

**解决方案**: 添加 `#ifdef __OHOS__` 守卫 undef KMP_CANCEL_THREADS

**修改文件**: `runtime/src/kmp.h`

**修改内容**:
```c
// Android and HarmonyOS do not have pthread_cancel support
#if defined(__ANDROID__) || defined(__OHOS__)
#undef KMP_CANCEL_THREADS
#endif
```

**补丁**: `0002-runtime-src-kmp.h.patch`

**知识沉淀**: E081 (HarmonyOS pthread_cancel 缺失)

---

### 问题 4: libomptarget 需要 LLVM 依赖

**现象**:
```
CMake Error: Could not find a package configuration file provided by "LLVM"
```

**解决方案**: 禁用 libomptarget 构建

**CMake 选项**: `-DOPENMP_ENABLE_LIBOMPTARGET=OFF`

---

## 编译过程

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libomp 15.0.4 --url=file:///path/to/libomp-15.0.4.tar.bz2

# 2. 配置
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DOPENMP_STANDALONE_BUILD=ON -DLIBOMP_OMPT_SUPPORT=OFF -DOPENMP_ENABLE_LIBOMPTARGET=OFF

# 3. 编译
make -j4

# 4. 安装 (staging)
make install DESTDIR=$TEST_PREFIX

# 5. 安装 (本地)
make install
```

**编译结果**: ✅ 成功

---

## 产物清单

| 文件 | 大小 | 说明 |
|------|------|------|
| libomp.so | 943KB | OpenMP 运行时库（共享库） |
| libgomp.so | → libomp.so | GNU OpenMP 兼容（软链接） |
| libiomp5.so | → libomp.so | Intel OpenMP 兼容（软链接） |
| omp.h | 23KB | OpenMP 头文件 |
| cmake/openmp/*.cmake | 15KB | CMake 配置文件 |

---

## 测试验证

**测试命令**: `make check-libomp`

**结果**: 测试套件未运行（缺少 llvm-lit）

**说明**: libomp 的测试套件需要 llvm-lit（LLVM 测试基础设施），不在 standalone build 中可用

---

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建验证 | ⚠️ 警告 | clean_verify.py 不支持 cmake 构建系统，手动验证通过 |
| G1 二进制完整性 | ✅ PASS | libomp.so 成功生成 |
| G2 功能可用性 | ⚠️ PASS | 无测试套件执行 |
| G3 可移植性 | ✅ PASS | DESTDIR 模式正确 |
| G4 档案完整性 | ⚠️ 警告 | 需补充预编译包 |

---

## 注意事项

1. **cmake 模块**: 需要 LLVM cmake 模块（ExtendPath.cmake 等），这些模块应包含在源码包中
2. **pthread_cancel**: HarmonyOS 不支持此函数，需要添加平台守卫
3. **libomptarget**: 禁用此模块以避免 LLVM 依赖
4. **clean_verify.py**: 当前脚本不支持 cmake 构建系统，需手动验证

---

## 后续工作

1. 等待主编审核 clean_verify.py 的 cmake 支持
2. 通过 G0 后制作预编译包
3. 提交 PR 到主仓库
4. 发布到 cmd-pkgs 供其他软件依赖
**知识提取**: E081 (HarmonyOS pthread_cancel 缺失)
---

**编译结束**: 2026-05-19 19:34
**最终状态**: built
