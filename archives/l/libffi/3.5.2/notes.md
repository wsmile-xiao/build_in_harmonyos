# libffi 3.5.2 适配笔记
## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-12
- 编译器: clang
- 状态: success

## 编译步骤
1. 下载源码 `wget https://ghfast.top/https://github.com/libffi/libffi/releases/download/v3.5.2/libffi-3.5.2.tar.gz`
2. 应用补丁 `0001-port-for-ohos.patch`（config.guess/config.sub 修改）
3. 应用补丁 `0002-closure-port-for-ohos.patch`（ffi_tramp HMDFS 路径回退修复）
4. `./configure --prefix=$TEST_PREFIX`
5. `make -j$(nproc)`
6. `make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ffi_closure 在 OHOS 上不可用 | 内核 W^X 策略禁止 PROT_EXEC 的 mmap | 启用 FFI_EXEC_STATIC_TRAMP + HMDFS 路径回退补丁 |

## 依赖版本
无外部依赖

## 验证结果
- ffi_call add(5,7)=12 ✅
- ffi_call abs(-42)=42 ✅
- 版本 API（ffi_get_version=3.5.2）✅

## 注意事项
- ghfast.top 可作为 GitHub 加速代理
- configure 会自动在子目录 `aarch64-unknown-linux-ohos` 中构建
