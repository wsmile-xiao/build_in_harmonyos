# lzma 5.6.2 编译进度

**日期**: 2026-07-15
**状态**: ✅ 编译成功

## 构建系统选择

使用 **CMake** 而非 Autotools，原因：
- Autotools 的 `config.status` 在 HarmonyOS HMDFS 上创建临时目录时失败
  - 错误: `can't create ./confXXXXXX/subs1.awk: Permission denied`
  - 原因: `mktemp -d "./confXXXXXX"` 创建目录后，子文件写入被拒绝
- CMake 构建无需 config.guess/config.sub 补丁，且编译测试全部通过

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | init-build 成功，源码已下载解压 |
| Step 2 configure | ✅ | CMake configure 成功，无需补丁 |
| Step 3 make | ✅ | `cmake --build` 全部目标编译成功 |
| Step 4 install | ✅ | `make install DESTDIR` 成功 |
| Step 5 check | ✅ | `ctest` 13/13 测试全部通过 |
| Step 6 staging | ✅ | 安装到 test prefix 验证通过 |
| Step 7 conan-init | ✅ | conanfile.py + conandata.yml + test_package 生成 |
| Step 8 conan-verify | ⏳ | 待验证 |

## 产物

- 库: `liblzma.a` (静态库)
- 可执行文件: `xz`, `xzdec`, `lzmadec`, `lzmainfo`
- 头文件: `lzma/*.h`, `lzma.h`

## 平台适配

- CMake 自动检测到 HarmonyOS 平台（显示 "System is unknown to cmake" 警告但不影响编译）
- 无需任何平台补丁
- 安全性: PIE + BIND_NOW 已启用

## 测试结果

```
100% tests passed, 0 tests failed out of 13
Total Test time (real) =   0.38 sec
```

测试覆盖: BCJ filter, block header, CRC check, filter flags/strings,
hardware detection, index, lzip decoder, memory limit, stream flags,
VLI encoding, MicroLZMA
---

**编译结束**: 2026-07-15 15:08
**二次校准 (2026-07-17)**:
- 响应检视意见 P2: 新增 `archives/l/lzma/commands.json` (R38)
- 响应检视意见 P3: 移除 `shared` 选项, `BUILD_SHARED_LIBS=OFF` 改为无条件 (R26)

**最终状态**: built
