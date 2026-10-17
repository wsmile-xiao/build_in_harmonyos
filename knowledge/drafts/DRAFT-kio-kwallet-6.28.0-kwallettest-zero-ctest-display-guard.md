# DRAFT-kio-kwallet-6.28.0-kwallettest-zero-ctest-display-guard

## 现象
- `ctest -N` 在 kio-kwallet（API-only kwallet）构建目录注册 **0 个测试**
  （"No tests were found"）——但上游明明有 kwallettest。
- 无头 HarmonyOS PC 上环境残留 DISPLAY 时，kwallettest（QApplication 型）
  SIGSEGV；用 conan `Environment.unset("DISPLAY")` 置空后仍 SIGSEGV。

## 根因
- KDE ECM 测试双轨制：`ecm_mark_as_test()` 只设目标属性，**没有 add_test()**
  → CTest 注册表为空是上游本态，非适配缺失。
- Qt 对 DISPLAY "存在即尝试连接"；conan `Environment.unset()` 实现为
  **置空字符串而非删除键**，`qEnvironmentVariableIsSet` 对 set-but-empty
  返回 true → 守卫被击穿。

## 解法
1. `ctest -N` 盘点（0 如实记录）+ 硬断言测试可执行文件已构建 + 直接执行
   并强制退出码（R51 三步法）。
2. `os.environ.pop("DISPLAY", None)` 真删除键；`QT_QPA_PLATFORM=offscreen`。
3. 干净 env 直跑：LD_LIBRARY_PATH 前置 /system/lib64 + 包内 lib + 依赖 lib。

## 验证
- kwallettest：2 passed / 0 failed / 1 skipped（skip=kioslave/passwords，
  需 kwalletd + D-Bus，超出 API-only 范围），退出码 0。
- 残留 DISPLAY 的 SIGSEGV 与 pop 后稳定通过均已实测复现。

## 关联
- DRAFT-kio-kwallet-6.28.0-cmake-version-soversion-symlink-e018；E002。
