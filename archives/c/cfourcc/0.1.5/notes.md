# cfourcc 0.1.5 适配笔记

## 编译环境
- **构建系统**: makefile（单文件 C CLI 工具，无 configure）
- **编译日期**: 2026-08-30
- **编译器**: clang（OHOS 交叉工具链，来自 conan conf R33）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁，纯标准 C）

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cfourcc/0.1.5 --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的官方 GitHub tag 归档下载并 strip_root。

### 2. 编译（build()）
- 上游 Makefile 直接用 `CC` 编译 `cfourcc.c`（约 265 行）为 `cfourcc` 二进制：
  `$(CC) $(CFLAGS) $< -o $@`
- R33：编译器从 conan conf 取（`tools.build:compiler_executables:c`），不依赖 shell `${CC}`
- R9：`make -j1`（不用 -j$(nproc)）
- CFLAGS 由上游 Makefile 自带 `-O2 -pedantic -ansi -Wall`，无需覆盖

### 3. 打包（package()）
- cfourcc 是 CLI 工具（package_type=application），无库/无头文件
- 直接 `copy("cfourcc")` 到 `bin/`（比 `make install` 更简单——上游 install 用
  `install -Dm755` + `strip`，strip 在 OHOS 交叉工具链下可能失败，且多余）

## 验证结果
- **构建**: `cfourcc/0.1.5: Package created`
- **R34 消费者验证**: test_package/test_cfourcc.py — 真实执行 `cfourcc -h`，
  输出含版本串（1/1 = 100%）
- **上游测试**: 无测试套件（tar tzf 全量核验，TODO 明示上游无单元测试）
- **commands.json**: archives/c/cfourcc/commands.json（R38 CLI 工具门禁）

## 已知限制
- 无（单文件工具，纯标准 C，无外部依赖）
