# DRAFT-E582 — OHOS 拒绝执行经 ld -r + objcopy --keep-global-symbols 合并对象链接出的可执行文件

## 错误特征
```
sh: ./test_base64: Operation not permitted     # 退出码 126 (EPERM)
sh: ./bin/base64: Operation not permitted
make: *** [Makefile:17: test] Error 127
```

## 触发条件
- 构建系统: Makefile（上游同时提供 CMake 的库，如 aklomp/base64 0.5.0）
- 阶段: linking → runtime（链接成功，但产物无法被 OHOS exec）
- 平台: OpenHarmony PC aarch64 (OHOS 6.0)

## 根因分析
上游 Makefile 使用 `$(LD) -r` 把多个 codec 对象（generic/neon/avx 等）合并为一个"可重定位对象"
`lib/libbase64.o`，再用 `llvm-objcopy --keep-global-symbols=lib/exports.txt` 剥除非导出符号。
该合并对象参与最终链接产出的可执行文件被 OHOS 内核 exec 安全策略拒绝
（`Operation not permitted` / exit 126），而同目录下直接链接原始 `.o` 文件编译出的
最小程序（hello）可正常运行；CMake 路径（正常 `add_library`，无 objcopy 合并步骤）
产出的测试程序与 CLI 均可执行（ctest 2/2 通过）。

实验证据（base64 0.5.0）：
1. `make -j2` 成功产出 bin/base64 + lib/libbase64.o；`./bin/base64` → Operation not permitted
2. `make -C test` 编译成功；`./test_base64` → Operation not permitted (126)
3. 同一编译器直接链接 lib/*.o（不经过 ld -r + objcopy）的最小程序 → 正常运行
4. CMake 路径 `cmake -DBASE64_BUILD_TESTS=ON .. && make && ctest` → 2/2 通过

## 解决方案

### 推荐方案
配方优先走 CMake 构建路径（CMakeLists.txt 用正常 add_library，无 objcopy 合并步骤），
产出的 libbase64 库与 base64 CLI、test_base64 测试均可执行。

```bash
cmake -DBASE64_BUILD_TESTS=ON -DBASE64_WERROR=OFF ..
make -j1
ctest --output-on-failure   # 2/2 通过
```

### 回退方案
必须使用 Makefile 路径时，用原始 `.o` 文件手工链接测试/CLI（绕过 ld -r + objcopy 合并对象）。

### 禁止做法
- ❌ 让 `objcopy --keep-global-symbols` 合并对象参与最终可执行文件链接
- ❌ 把 EPERM 误判为"平台不支持执行"而跳过上游测试（本库其他路径可执行）

## 影响范围
OHOS aarch64 上使用 `ld -r` + `llvm-objcopy --keep-global-symbols` 合并模式的
Makefile 库（如 aklomp/base64 0.5.0）。

## 验证
- 诊断验证: 直接链接原始 .o 的最小程序可执行；CMake 路径 ctest 2/2 通过
- 方案验证: conan create (CMake 路径) 内 test_package ctest 通过，W3 本地 CI L0-L5 pass

## 适用边界
- 仅 OHOS exec 安全策略（合并对象链接产物被拒）；Linux/其他平台不受影响
- 仅影响可执行文件（测试/CLI）；库产物 .a/.so 本身可正常打包链接

## 关系
- similar_to: E077 (ELF/codesign 签名失效 EPERM)、E537 (HMDFS ELF 修改后 Permission denied) — 均为 EPERM 类但根因不同
- caused_by: 无
- conflicts_with: 无
