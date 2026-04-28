# libffi 3.4.4 适配笔记
## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-21
- 编译器: clang
- 状态: success

## 编译步骤
1. init-build 成功，历史记录存在
2. 应用补丁 `0001-port-for-ohos.patch` + sed umask 077→022
3. `./configure --prefix=$DEFAULT_PREFIX --enable-shared`
4. `make -j$(nproc)`
5. DESTDIR staging 隔离安装
6. 打包生成 `libffi-3.4.4-ohos-aarch64.tar.gz`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS umask 077 导致安装文件权限异常 | HMDFS 文件系统默认 umask 077 | `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | HMDFS 软链接读取受限 | HMDFS 安全策略 | 打包时手动处理 symlinks |
| 3 | clang -print-multi-os-directory 不支持 | LLVM 不支持此选项 | 非致命，忽略 |

## 依赖版本
无外部依赖

## 验证结果
- 头文件、库文件、pkgconfig 均正确 ✅
- ffi_call 核心功能正常 ✅

## 注意事项
- libffi 测试需要 DejaGnu，已跳过
- 3.4.4 不包含 FFI_VERSION_STRING 宏（3.5.0+ 才有）
