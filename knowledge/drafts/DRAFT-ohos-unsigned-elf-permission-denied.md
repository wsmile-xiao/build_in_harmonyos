# DRAFT-ohos-unsigned-elf-permission-denied — 未签名 ELF 被 OHOS 加载器拒绝

> **Contributor**: AtomCode (deepseek-flash) | **Status**: DRAFT | **Updated**: 2026-10-03
> **Severity**: high | **Category**: ohos / linking / packaging / conan

## Problem

在鸿蒙 PC 设备上，可执行文件依赖一个**已发布但未签名**的共享库时，加载器在进程启动
（main 之前）即失败，表现为两个层面的信息，极易被误判为“符号缺失”或“软链接失效”：

```
Error loading shared library libKF5CoreAddons.so.5: (needed by /path/to/KAuthSetupActionTest)
Error relocating /path/to/KAuthSetupActionTest: _ZN4KJob12setErrorTextERK7QString: symbol not found
```

`ctest` 直接判 `***Failed`，且因为发生在动态链接期，测试框架自身没有任何输出。

## Root cause

OHOS 加载器要求 ELF **具备有效 `.codesign` 自签名**；未签名（或 `.codesign` 段为空）
的 ELF 被拒绝映射，musl 把该拒绝上报为 `Permission denied`：

```bash
python3 -c "import ctypes; ctypes.CDLL('.../libKF5CoreAddons.so.5')"
# Error loading shared library ...: Permission denied
```

而同目录下 Qt5 的库（已签名）加载正常，`nm -D` 也能证明“缺失的符号”其实存在
（119 个 KJob 符号）。因此报错文本与真实原因无关。

### 排除项（本任务逐一实测排除）

| 曾怀疑 | 实测结论 |
|---|---|
| SONAME 软链接缺失（E274） | 无关。`readelf -d` 的 SONAME 与 NEEDED 一致，符号存在 |
| 软链接不被解析（HMDFS） | 无关。把 `libKF5CoreAddons.so.5` 复制成实体文件（及改权限 0755/0777）后仍失败 |
| 同名库污染 / 系统库遮蔽 | 无关。设备上除 conan 缓存外不存在其他 `libKF5CoreAddons*` |
| RPATH/RUNPATH 缺失 | 无关。仅影响是否有 RPATH，不影响“Permission denied”这一错误类别 |

决定性区分方法：**用 `ctypes.CDLL(<库路径>)` 单独 dlopen**。若报
`Permission denied` 即为签名问题；若报 `symbol not found`/`not found` 才是符号或
SONAME 问题。

## Implementation

两层修复（配方层，不改依赖包内容）：

1. **自身产物**：`package()` 中遍历 `package_folder`，跳过软链接，对 ELF 执行
   ```bash
   /data/service/hnp/bin/llvm-objcopy --remove-section .codesign <elf>
   /data/service/hnp/bin/binary-sign-tool sign -inFile <elf> -outFile <tmp> -selfSign 1
   # 再 move 回原位并恢复权限
   ```
   （同 accountsservice / adwaita-qt 既有模式）

2. **依赖库（来自制品仓、未签名）**：在 `build()` 的测试阶段，把各依赖
   `lib/` 下的库 `shutil.copy2`（跟随软链接→实体文件）到
   `<build_folder>/signed-runtime`，逐一签名，并把该目录置于运行时
   `LD_LIBRARY_PATH` 首位。**不修改依赖包目录**（R49/E524：只写 build_folder）。

同一模式也适用于 `test_package`（消费者二进制同样链接依赖库）。

## Verification boundary

`archives/k/kauth5/5.116.0`：`conan create` 在鸿蒙 PC 真机上通过。
修复前 `KAuthSetupActionTest` 因上述加载失败 0% 通过；修复后
`100% tests passed, 0 tests failed out of 1`，且 `test_package` 两个消费者二进制
在真机实际执行成功（`kauth5 test_package OK (KF5AuthCore 5.116.0)`）。

## Source

- Package: `archives/k/kauth5/5.116.0`
- 依赖: `kcoreaddons5/5.116.0`（制品仓二进制 `.codesign` 为空）
- 相关既有条目: E131（Permission denied / dlopen）、E135（ELF 签名 / 运行时加载）
