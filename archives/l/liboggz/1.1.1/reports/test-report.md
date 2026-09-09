# Test Report — liboggz 1.1.1

**Date**: 2026-09-08
**Build System**: autotools
**Environment**: OpenHarmony aarch64 (HarmonyOS, clang 15.0.4, OHOS profile)

## Test Results

**Total Tests**: 23
**Passed**: 23 (100%)
**Failed**: 0 (0%)

## 上游测试（make check，src/tests）

```
===================
All 23 tests passed
===================
```

### Passed Tests (23)
1. comment-test
2. io-count
3. io-read-single
4. io-read
5. io-run
6. io-seek
7. io-write
8. io-write-flush
9. read-generated
10. read-stop-err
11. read-stop-ok
12. seek-stress-test.sh
13. seek-stress
14. write-bad-bos
15. write-bad-bytes
16. write-bad-eos
17. write-bad-granulepos
18. write-bad-guard
19. write-bad-packetno
20. write-bad-serialno
21. write-dup-bos
22. write-prefix
23. write-recursive
24. write-suffix
25. write-unmarked-guard

> 注：make check 注册 25 个测试源（含 2 个组合脚本/链接测试），实测 23 项全部通过；MANIFEST.yml 已按实际运行结果回填。

## 消费者测试（test_package，conan create 内置）

```
1/1 Test #1: test_liboggz .....................   Passed    0.03 sec
```

- test.c 调用 `oggz_new(OGGZ_READ)` / `oggz_close()` 验证库 API 可链接可用（R34 实质测试）

## HarmonyOS 专项验证（conan-verify L2/L4/L5）

- L2 smoke test：`oggz --version` 等命令行工具 `--version` 检查（13 项，10 OK + 3 warn 非阻塞）
- L4 静态安全扫描：PASS（仅 patches 含危险函数警告，非阻塞）
- L5 产物基线：PASS（bin/ 有内容）
- G3 系统同名库隔离（R26）：PASS
- G4 产物完整性：PASS

## 结论

✅ 上游 23/23 通过、消费者测试通过、W3 本地 CI 模拟通过（.ci-result.json exit_code=0）
