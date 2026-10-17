# libgringotts 1.2.1 测试报告（HarmonyOS PC aarch64）

- 测试时间：2026-09-19
- 目标平台：aarch64-linux-ohos，clang 15，libc++，musl sysroot
- 构建方式：Conan 2 `conan create`（profile `ohos-aarch64`，host=build=ohos-aarch64）
- 验证关卡：`conan-verify` G0/G1/G2/G3 全部 PASS；W3 本地 CI 模拟（build_and_test）PASS；W2 PR 原子性检查 PASS（仅含配方变更 10 文件）

## 消费者测试（test_package）

`test_package/test.c` 真实调用 libGringotts 核心 API 完成**明文 → 加密文件 → 解密还原**的往返一致性校验：

| 步骤 | API | 结果 |
|------|-----|------|
| 版本校验 | `grg_get_version()` | 返回 `1.2.1` ✅ |
| 上下文初始化 | `grg_context_initialize_defaults("GRG")` | 成功 ✅ |
| 密钥生成 | `grg_key_gen(pwd, len)` | 成功 ✅ |
| 文件加密 | `grg_encrypt_file(ctx, key, path, plain, dim)` | `GRG_OK` ✅ |
| 文件解密 | `grg_decrypt_file(ctx, key, path, &out, &outdim)` | `GRG_OK` ✅ |
| 往返一致 | `memcmp(out, plain, dim)` | 42 字节完全一致 ✅ |

运行时输出：
```
libgringotts version: 1.2.1
OK: libgringotts encrypt/decrypt roundtrip verified (42 bytes)
```

## 适配要点

- 上游 `configure` 经 `libmcrypt-config` 探测 libmcrypt；conan 的 libmcrypt 包不携带该脚本，且 OHOS profile 的 PATH 重置使注入 shim 不可靠，故 recipe 在 `build()` 前 patch `configure`（`_patch_libmcrypt_config_check`）：将 `if libmcrypt-config ...` 改为 `if true`，并从 `AutotoolsDeps` 注入的 `$CPPFLAGS` / `-lmcrypt` 派生 `MCRYPT_CFLAGS/LIBS`。
- `AutotoolsDeps` 注入全部依赖（libmcrypt / mhash / zlib / bzip2）的 include / lib / `-l` 标志，修复 configure 依赖探测。
- 工具链注入 llvm `ar/ranlib/nm/ld/strip` 与 musl 预处理；`build()` 各步骤输出绑定日志文件，规避 OHOS worker 下编译器输出被静默吞掉导致的假成功。
- 交叉编译复用 `config.guess/sub` 的 OHOS hook。

## 结论

libgringotts 1.2.1 在 HarmonyOS PC aarch64 下编译、链接、安装与运行时加解密往返均通过验证，适配可用。
