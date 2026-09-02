# libtomcrypt 1.18.2 适配笔记

日期：2026-09-01　分支：`feat/libtomcrypt-1.18.2`　目标：OHOS aarch64 (HarmonyOS PC)

## 1. 上游核实

- 官方 upstream：https://github.com/libtom/libtomcrypt
- release：tag `v1.18.2`，官方 tarball `crypt-1.18.2.tar.xz`
  - URL: `https://github.com/libtom/libtomcrypt/releases/download/v1.18.2/crypt-1.18.2.tar.xz`
  - SHA-256: `96ad4c3b8336050993c5bc2cf6c057484f2b0f9f763448151567fbab5e767b84`
  - 官方 `.hashes` 提供 SHA-512，本地下载文件 sha512 与之匹配后另行记录 SHA-256
- License：WTFPL（`LICENSE`，双条款 = WTFPL-1.0/2.0 语义，公开域式宽松许可）

## 2. 上游测试结构（重点核查结论）

libtomcrypt 1.18.2 的**正式 correctness/self-test 只有一个入口**：

- `make test`（makefile 目标 `test`）→ 链接 `tests/*.o` + `libtomcrypt.a` 生成单一可执行文件 `./test`
- `tests/test.c` 内 `test_functions` 注册 **21 个套件入口**（LTC_TEST_FN 宏）：
  store / rotate / misc / mpi / cipher_hash / mac / modes / der / pkcs_1×5 /
  rsa / dh / ecc / dsa / katja / file / multi / prng
- 每套件输出 `name...passed|failed|nop`，最终汇总行
  `SUCCESS: passed=<p> failed=<f> nop=<n> duration=<t>`；任一失败则退出码非 0
- 计数单位 = **套件（21）**，不是内部单条断言（上游按套件粒度汇总，不单独计数每条 KAT）

**非正式入口（不与 correctness 混淆）：**

- `demos/timing.c`：benchmark/timing（性能测量，非正确性测试）
- `demos/*` 其余：example（用法演示）
- 无 `test_standalone` 目标（1.17 及之前版本才有；1.18.x 用 `make test` 即静态库自测）
- 无 `make check`；`make timing` 生成的是 benchmark 可执行文件
- 上游无 CI 专用脚本改变测试口径（testrunner 即上述 `./test`）

## 3. OHOS 真机执行结果（本次实测）

```
$ ./test
（21 行套件结果）
SUCCESS: passed=20 failed=0 nop=1 duration=12.0sec real=12.0sec
```

- **Total 21 / Pass 20 / Fail 0 / Skip(nop) 1**
- 唯一 nop 是 `katja_test`：上游默认未启用 LTC_MKAT
  （`tomcrypt_custom.h` 中 `/* #define LTC_MKAT */` 默认注释掉）。
  这是上游默认配置行为，与 OHOS/交叉编译无关；
  按"禁止为让测试过而关闭/开启算法"原则，保持上游默认，不额外打开。
- 真实性：`./test` 为 ELF64 / AArch64 / musl interpreter
  `/lib/ld-musl-aarch64.so.1`，直接在本 HarmonyOS PC (aarch64) 上执行
  （host=target，`can_run()` 为真）。

## 4. 依赖（MPI provider）

- libtomcrypt **无必须依赖**：不接 MPI provider 时全部 PK 套件编译通过但 nop。
- 可选 provider：libtommath（USE_LTM）/ tomsfastmath（USE_TFM）/ gmp（USE_GMP）。
- **选型 gmp/6.3.0**：
  - ohpcd 远程已发布 gmp/6.3.0 的 OHOS aarch64 二进制（实测 `conan install` 可解析下载）
  - libtommath 未发布于 ohpcd，且 libtommath 1.3.0 的 `mp_to_radix` 相比 1.18.2
    调用点新增第 5 参数 `size_t *written`（`mp_toradix` → `mp_to_radix` API 断裂），
    接入需 patch，违背"零 patch"前提，故弃用
  - gmp 接线零 patch：`-DUSE_GMP -DGMP_DESC`（`gmp_desc` 声明于
    `src/headers/tomcrypt_math.h:508`），EXTRALIBS 指向 Conan 的 gmp 即可
- `with_gmp` 选项默认 True，可关（关掉后 PK 套件 nop，与无 provider 等价）。

## 5. 构建方式（零 patch）

- 上游纯 GNU makefile（静态库走 `makefile`，共享库走 `makefile.shared`）。
- 本配方：`make library`（交付物）+ `make test`（自测，不交付），命令行注入
  `CC/AR/RANLIB/CFLAGS/EXTRALIBS`，不继承宿主环境（R33）。
- clang15/musl 无需任何源码 patch；上游 `-Wall -Wextra` 下仅个别 warning，不阻塞。
- 安装：上游 `make install` 的 pc 生成/属主逻辑在 package() 中用纯拷贝复刻
  （13 个公共头 `tomcrypt*.h` + `libtomcrypt.a` + LICENSE）。

## 6. Conan 2 输出

- `cpp_info.libs=["tomcrypt"]`；`requires=["gmp::gmp"]`（with_gmp 时）
- `cmake_file_name=libtomcrypt`、`cmake_target_name=libtomcrypt::libtomcrypt`、
  `pkg_config_name=libtomcrypt`（CMakeDeps 实测生成
  `libtomcrypt-config.cmake` / `libtomcryptTargets.cmake` 等；.pc 由消费者
  PkgConfigDeps 生成）
- 产物实测：`include/tomcrypt*.h` × 13、`lib/libtomcrypt.a`
  （ar archive，成员 ELF64/AArch64，408 个 .o，含 gmp_desc.o）

## 7. test_package（公开 API，与上游测试分开统计）

`test_package/test.c` 只用最终包的公共 API，全部标准向量来自公开标准：

| 类别 | 断言 | 向量来源 |
|---|---|---|
| hash | sha256("abc") / sha256("") KAT | FIPS 180-4 |
| cipher | AES-128 ECB KAT + encrypt/decrypt round-trip | NIST SP 800-38A F.1.1 |
| 编码 | base64 编/解码 KAT | RFC 4648 |
| PRNG | yarrow start/add_entropy/ready/read×2/两块不同 | 确定性种子长度与输出检查 |
| error path | 8 字节 buffer 摘要 → CRYPT_BUFFER_OVERFLOW + error_to_string | 错误码语义 |

- 20 项断言全 OK（`TEST PACKAGE PASSED (0 failures)`）
- `test_libtomcrypt`：ELF64 / AArch64 / PIE / musl interpreter，真机执行
- **注意：test_package 的 20 项断言不得与上游 21 套件统计混算**（见 MANIFEST.yml）

## 8. 环境备忘（本机专属，非包问题）

- `ci/conan/profiles/ohos-aarch64` 的
  `tools.build:compiler_executables` 可能指向当前主机不存在的绝对编译器路径
  （本机不存在）；本机实际工具链在
  环境中可解析到的 OHOS clang。配方内对不存在的绝对路径
  做了存在性回退（取 buildenv PATH 中的 clang），CI 机器路径存在时不受影响。
- 源码下载由 CI 预下载/缓存机制处理；CI 验证结束后 conandata.yml 已恢复为官方 HTTPS 源。
- gmp 本地缓存包路径：`~/.conan2/p/gmp1e0cc591edf00/p`
  （lib/libgmp.a + include/gmp.h）。
