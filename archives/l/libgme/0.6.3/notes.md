# libgme 0.6.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 CMake 构建系统，**必须禁用 UBSan**：
1. init-build: 源码下载并解压到 ~/tmp/builds/libgme-0.6.3.work
2. cmake configure: `cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release -DENABLE_UBSAN=OFF ..`
3. make: `make -j4` (编译成功，有警告但无错误)
4. make install: DESTDIR 模式，安装到 staging 目录
5. package: 预编译包制作（strip + tar.gz）
6. deploy: 安装到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G0 clean-verify 失败 | clean-verify 脚本误判构建系统为 autotools | 已修复 manifest.yaml (system: cmake) |
| 2 | 动态库运行时 UBSan 符号缺失 | CMakeLists.txt 默认 `ENABLE_UBSAN=ON` | 重新编译添加 `-DENABLE_UBSAN=OFF` |

编译过程顺利，无重大问题。CMake 检测到未知平台 HarmonyOS 但继续编译成功。

## 源码修改

无补丁文件，源码无需修改即可编译。

## 依赖版本

- zlib: 系统已有
- cmake: 3.30.0
- clang: 15.0.4
- libc++: 系统自带

## 功能测试结果

**测试日期**: 2026-06-05

| 测试项 | 结果 |
|--------|------|
| 版本验证 | ✅ PASS |
| NSF 解析 | ✅ PASS |
| VGZ 解析 | ✅ PASS |
| 音频生成 | ✅ PASS |
| 错误处理 | ✅ PASS |
| 动态库运行 | ✅ PASS |

**总计**: 14/14 通过

详见 `reports/test-report.md`

## 验证结果

```bash
# ELF 二进制验证
file ~/usr/local/lib/libgme.so
# 输出: ELF shared object, 64-bit LSB arm64, stripped

# 预编译包内容
tar -tzf libgme-0.6.3-ohos-aarch64.tar.gz
# 输出: include/gme/, lib/libgme.so, lib/pkgconfig/libgme.pc

# 动态库依赖
readelf -d lib/libgme.so | grep NEEDED
# 输出: libc++_shared.so, libc.so (无 UBSan)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgme-0.6.3-ohos-aarch64.tar.gz | 369 KB | 预编译包（stripped，无 UBSan） |
| libgme-0.6.3-ohos-aarch64-debug.tar.gz | 125 KB | 调试符号包 |

## 注意事项

1. libgme 是游戏音乐模拟库，支持多种游戏音乐格式（NES、GameBoy、Sega 等）
2. **必须添加 `-DENABLE_UBSAN=OFF`** 禁用 UBSan，否则动态库不可用
3. CMake 会警告未知平台 HarmonyOS，但不影响编译
4. 编译警告：多个 override 关键字缺失（C++ 代码风格问题，不影响功能）
5. SDL2 未找到，但这是可选依赖（demo player），不影响核心库编译
6. 动态库依赖 `libc++_shared.so`，确保系统有 libc++ 运行时

---

**编译结束**: 2026-06-05 11:45
**最终状态**: published