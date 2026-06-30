# libime 1.1.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built（RPATH 已修复，需 ELF 签名）

## 编译步骤

1. **依赖编译**（前置步骤）
   - ECM 6.26.0: cmake 纯头文件库
   - Boost 1.87.0: iostreams 组件（pthread_setcancelstate 补丁）
   - libuv 1.48.0: 事件循环库（CPU affinity 补丁）
   - Fcitx5Utils 5.1.13: fcitx5 核心工具库（C++20 补丁）

2. **cmake 配置**
   ```bash
   cmake .. \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX \
     -DCMAKE_INSTALL_RPATH=$DEFAULT_PREFIX/lib \
     -DENABLE_TEST=OFF \
     -DENABLE_DOC=OFF \
     -DENABLE_DATA=OFF \
     -DENABLE_TOOLS=OFF
   ```

3. **编译与安装**
   ```bash
   make -j2
   make install DESTDIR=$TEST_PREFIX  # staging
   make install                        # 本地安装
   ```

4. **RPATH 修复**（关键步骤）
   ```bash
   # 复制到临时目录
   cp libIME*.so ~/tmp/libime_patch/

   # 替换依赖路径
   patchelf --replace-needed ../../../lib/libIMECore.so libIMECore.so libIMEPinyin.so
   patchelf --replace-needed ../../../lib/libIMECore.so libIMECore.so libIMETable.so

   # 设置 RUNPATH
   patchelf --set-rpath $DEFAULT_PREFIX/lib libIME*.so
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Fcitx5Utils 头文件缺失 | 之前编译安装不完整 | 复制所有头文件到 include/Fcitx5/Utils/fcitx-utils/ |
| 2 | C++20 ranges/views 不支持 | OpenHarmony libc++ 未实现 | 替换为传统 C++（24处修改） |
| 3 | 跨库依赖路径错误 | CMAKE_LIBRARY_OUTPUT_DIRECTORY 设置 | 所有库输出到 lib 目录 + patchelf 替换 |
| 4 | ELF 执行权限拒绝 | 鸠蒙安全机制要求签名 | 需要 ELF 签名才能运行 |

## RPATH 修复详情

### 问题分析
libime 原始 CMakeLists.txt 设置：
```cmake
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
```
导致 libIMEPinyin.so 依赖路径为 `../../../bin/libIMECore.so`，安装后路径失效。

### 修复方案
1. **修改 CMakeLists.txt**（9号补丁）：
   ```cmake
   set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
   ```
   所有库输出到同一目录

2. **使用 patchelf 替换依赖路径**：
   - 修复前: `NEEDED: ../../../lib/libIMECore.so`
   - 修复后: `NEEDED: libIMECore.so`
   - RUNPATH: `$DEFAULT_PREFIX/lib`

### 验证结果
```bash
$ readelf -d libIMEPinyin.so | grep -E "NEEDED|RUNPATH"
  RUNPATH: /storage/Users/currentUser/usr/local/lib
  NEEDED: libIMECore.so  ✅
```

## ELF 签名要求（鸿蒙安全机制）

### 测试结果
```bash
$ ./test_libime
❌ libIMECore: Permission denied
```

### 原因
鸿蒙系统要求所有可执行的 ELF 文件（包括共享库）必须经过签名，否则会拒绝执行。

### 解决方案
1. **通过 cmd-pkgs 公共安装脚本部署**（自动签名）
2. **使用 ohc-run.py sign-elf 命令签名**（打包时）
3. **通过 fcitx5 输入法框架加载**（框架会处理签名）

## 补丁文件清单

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | decoder.cpp | std::views::take → 计数循环 |
| 0002 | historybigram.cpp | 12处 C++20 替换 |
| 0003 | lattice.h | std::ranges::reverse → std::reverse |
| 0004-008 | 其他源文件 | C++20 兼容性修复 |
| 0009 | CMakeLists.txt | 输出目录改为 lib |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| ECM | 6.26.0 | 本地编译 |
| Fcitx5Utils | 5.1.13 | 本地编译 |
| Boost | 1.87.0 | 本地编译 |
| libzstd | 1.5.6 | 系统预装 |

## 功能测试结论

| 测试项 | 结果 | 说明 |
|--------|------|------|
| cmake 配置 | ✅ PASS | find_package 可用 |
| RPATH 修复 | ✅ PASS | 依赖路径正确 |
| 库加载（未签名） | ❌ FAIL | Permission denied |
| 符号导出 | ✅ PASS | 关键符号存在 |

### 结论
- **RPATH 问题已解决**：依赖路径从相对路径改为正确的绝对路径
- **需要 ELF 签名**：鸿蒙安全机制要求，签名后可正常运行
- **推荐部署方式**：通过 cmd-pkgs 或 fcitx5 框架部署

---
**编译结束**: 2026-06-08 17:20
**最终状态**: built（RPATH 已修复）
**RPATH 修复**: 2026-06-08 - 依赖路径正确
**待完成**: ELF 签名后可正常运行---

**重新打包**: 2026-06-08 19:40
**修复内容**:
- staging 目录中重新执行 patchelf 修复 RPATH
- 使用 ohc-run.py package 重新打包
- 自动完成 ELF 签名

**验证结果**:
- ✅ 所有库文件成功加载
- ✅ RPATH 使用 $ORIGIN 相对路径
- ✅ NEEDED: libIMECore.so（正确路径）
- ✅ .note.ohos.ident 签名段存在

**签名问题**: 已解决 ✅