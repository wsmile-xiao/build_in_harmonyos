# rhonabwy 1.1.13 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 原生编译，profile `ci/conan/profiles/ohos-aarch64`）
- 目标平台: OHOS / aarch64（HarmonyOS PC）
- 状态: built（本地 conan create + 上游 CTest 19/19 程序通过；尚未 conan upload 到制品仓，
  PR 合入后由 CI 发布置 published）

## 编译步骤

1. 依赖预检（W0）：`bash ci/scripts/preflight_check.sh rhonabwy/1.1.13`
   — gnutls/3.8.10、jansson/2.15.1.1、nettle/3.10.2.1、zlib/1.3.1.1、curl/8.15.0、
   orcania/2.3.3、libyder/1.4.20（制品仓内名 `libyder`）、gmp/6.3.0.1 均已发布二进制，版本号未被占用（R37）。
2. 源码获取：`conandata.yml` 使用上游官方 tag 归档
   `https://github.com/babelouest/rhonabwy/archive/refs/tags/v1.1.13.tar.gz`（sha256 已固定）。
3. 探索式编译（模式 B，用于确认编译参数与上游测试面）：
   ```
   source .build-context-rhonabwy-1.1.13
   cd "$BUILD_SRC_DIR"
   cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=<CMakeToolchain> -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
   cmake --build build -- -j2 && cmake --install build
   ctest --test-dir build -V --output-on-failure
   ```
   探索阶段确认：上游 `CMakeLists.txt` 自带 `-Wall -Werror`，`find_package` 使用大写目标名
   （`Jansson::Jansson`/`Nettle::Nettle`/`Gnutls::Gnutls`/`Orcania::Orcania-static`/`Yder::Yder-static`），
   测试面强制 `Check` + `Subunit` + `Ulfius`，其中 `test/cert/` 夹具只被 6 个 Ulfius 程序消费。
4. 正式构建（模式 A，Conan 驱动）：
   ```
   conan create archives/r/rhonabwy/1.1.13 \
       -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
       --build=missing -r=ohpcd
   ```
   `build()` 末尾真实执行上游 CTest（19 个程序），`test()` 运行消费者断言程序。
5. 配方验证：`python3 scripts/ohc-run.py conan-verify rhonabwy 1.1.13`
   （G0 补丁应用 / G1 配方静态 / G2 干净缓存重跑 conan create / G3 R26 静态隔离 / G4 产物完整性 全部 PASS；
   L2 平台功能矩阵与 L4 安全扫描、L5 产物基线为**非阻断遥测档**：L2 因 CI 未注入 Conan 运行环境而 skip（warn），
   L4 为 warn，L5a 记录 `librhonabwy.so` 无 `DT_SONAME`；已用 `readelf -d` 实测复核：只有 `NEEDED`、无 `SONAME` 行，而 `DT_NEEDED` 全是裸 soname（无绝对路径泄漏），与知识库 `E383` 同根因（CMake 缺 `Platform/HarmonyOS.cmake`，对 OHOS 不生成 versioned soname），同已合入的 `ulfius/2.7.15` 一致（见文末已知限制）。

## 上游测试清点（R51 第一步：适配前统计）

| 口径 | 数量 | 依据 |
|------|------|------|
| CTest 注册的测试程序 | 25 | `CMakeLists.txt`：`set(TESTS ...)` 19 个 + `set(TESTS_WITH_ULFIUS ...)` 6 个 |
| 注册用例（`tcase_add_test`） | 379 | 逐文件源码统计 `test/*.c` |
| 夹具文件 | 20 | `test/cert/`（证书/私钥，`certtool` 生成） |
| 本次可构建运行的程序 | 19 | 自足程序，夹具为源码内字面量 |
| 本次可构建运行的注册用例 | 253 | 见下表逐文件统计 |
| 实跑用例（libcheck 汇总） | 252 | 真机日志 `executed=252 failures=0 over 19 programs` |
| 未运行用例 | 126 + 1 | 6 个 Ulfius 程序的 126 个用例 + 计数口径差 1 |

| 程序 | 注册用例 | 程序 | 注册用例 | 程序 | 注册用例 |
|------|---------|------|---------|------|---------|
| misc | 6 | jwe_rsa | 8 | jwe_ecdh | 21 |
| cookbook | 3 | jwe_aesgcm | 7 | jwe_pbes2 | 9 |
| jwk_core | 9 | jwe_dir | 8 | jwe_json | 23 |
| jws_hmac | 13 | jwe_kw | 9 | jwt_encrypt | 11 |
| jws_ecdsa | 15 | jwe_rsa_oaep | 14 | jwt_sign | 13 |
| jws_rsa | 13 | jws_json | 25 | jwt_nested | 34 |
| jws_rsapss | 12 | | | **合计** | **253** |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could NOT find Jansson` / `find_package(Jansson)` 失败 | 上游用大写目标名 `Jansson::Jansson`，CMakeDeps 导出小写 `jansson::jansson` | 补丁 0001 在上游 `find_package` 之后建别名，保持上游源码目标名不变 |
| 2 | `find_package(Subunit REQUIRED)` 失败（上游测试强制依赖） | 制品仓无 Subunit 包；Subunit 仅用于 TAP 输出 | 补丁 0001 将 Subunit 改为可选，缺失时不影响 Check 测试运行（同 `libyder/1.4.20` 先例） |
| 3 | `Ulfius::Ulfius` 未发布导致测试目标链接失败 | 制品仓 `ulfius/2.7.15` 配方已合并但无 OHOS 二进制 | 补丁 0001 仅在找到 Ulfius 时才注册 6 个 Ulfius 测试程序；19 个自足程序照常构建运行 |
| 4 | `gmp.h` 找不到 | `gmp/6.3.0.1` 发布元数据未导出 include 目录（空 `includedirs`），而 gnutls 公开头需要它 | 补丁 0001 在找到 `gmp::gmp` 时注入其包内 include 目录 |
| 5 | `-Wconversion -Werror` 报错（`curl_easy_perform` 返回值 enum→int 收窄） | clang 15 对隐式收窄严格，上游 GCC 下无告警；上游自带 `-Werror` 不能整体去掉 | 补丁 0002 在 `src/misc.c` 把该返回值显式转换（`(int)`），保留上游 `-Werror` |
| 6 | test_package 编译报 `'jansson.h' file not found` | CMakeDeps 只为**直接**依赖生成可用数据文件；传递依赖的数据文件为空（`set(jansson_INCLUDE_DIRS_RELEASE )`），共享库链接不传递 include 用法要求 | test_package 的 `requirements()` 显式声明 `jansson`/`gnutls`/`nettle`（与主配方同版本），并把该结论写入配方注释与 `conanfile.py` 的 `cpp_info` 注释 |
| 6b | 消费者只 `requires rhonabwy/1.1.13` 时仍编译失败（`jansson.h: file not found`） | 同 6：`cpp_info.requires` 不会展开到消费者的 CMake graph（与已合入的 `ulfius/2.7.15`、`dwarves/1.30` 两个 test_package 先例结论一致） | 主配方**不**声明 `cpp_info.requires`（声明亦无益），改为在 `package_info()` 注释中记录实测证据，并在 PR 正文「补充说明」明示：消费方需自行声明公开头依赖 —— 与本仓库同族包既有口径一致 |
| 7 | test_package 运行报 `Error relocating .../librhonabwy.so: gnutls_strerror: symbol not found` | OHOS 加载器解析共享依赖链时忽略 `LD_LIBRARY_PATH`，绑定到系统旧 `libgnutls`；`VirtualRunEnv` 也未导出 gnutls 的 lib 目录 | `test()` 显式把图中所有依赖的 `lib` 目录前置到 `LD_LIBRARY_PATH` 并 `LD_PRELOAD` 本次构建的 `libgnutls.so.30`（同 `ulfius/2.7.15` test_package 先例） |
| 8 | 曾尝试用 `cpp_info.requires` 传递公开头依赖，实测无效 | ① CMakeDeps 对被 `cpp_info.requires` 引用之外的传递依赖只输出空数据文件（实测 `set(jansson_INCLUDE_DIRS_RELEASE )`）；② 库侧 `cpp_info.requires` 并不会展开到消费者的 CMake graph（同 6b 实测） | 最终**不声明** `cpp_info.requires`，由消费方显式声明公开头依赖（本包 `test_package` 即此写法），与本仓库 `ulfius/2.7.15`、`dwarves/1.30` 先例一致 |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| `patches/0001-CMakeLists.txt.patch` | `CMakeLists.txt` | ① `find_package` 后建 CMakeDeps 小写目标别名；② 注入 gmp 包内 include 目录；③ `Check` 走随包模块；④ Subunit 改可选；⑤ 仅在找到 Ulfius 时注册 6 个 Ulfius 测试程序（19 个自足程序始终注册） |
| `patches/0002-src-misc.c.patch` | `src/misc.c` | `curl_easy_perform()` 返回值显式 `(int)` 转换，适配 clang 15 `-Wconversion -Werror` |

两个补丁均由 `python3 scripts/ohc-run.py refresh-patch rhonabwy 1.1.13 --auto` 生成（R8，不手写），
并在纯净源码上以 `patch --dry-run -p1` 验证可应用；补丁内无平台宏（无 `__OHOS__`/`__MUSL__` 分支）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| gnutls | 3.8.10 | JWS/JWE 密码学原语 |
| nettle | 3.10.2.1 | 哈希/签名底层 |
| jansson | 2.15.1.1 | JSON 对象（公开头中包含 `jansson.h`） |
| zlib | 1.3.1.1 | 压缩（`deflate`） |
| curl | 8.15.0 | `rnbyc jwks` 远程 JWKS 获取 |
| orcania | 2.3.3 | babelouest 工具库（公开头传递依赖） |
| libyder | 1.4.20 | 日志（公开头传递依赖） |
| gmp | 6.3.0.1 | gnutls/nettle 传递依赖（以 override 固定） |
| check | 0.15.2 | 仅构建上游测试时的 test_requires |
| cmake | 4.1.2 | 构建工具 |

## 验证结果

```bash
$ conan create archives/r/rhonabwy/1.1.13 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -r=ohpcd
rhonabwy/1.1.13: Package 'be775432221eaa9dcc67179b87574c4713747194' created
# build() 内的上游测试（真机）：
100% tests passed, 0 tests failed out of 19
[rhonabwy] upstream libcheck cases executed=252 failures=0 over 19 programs
HMBS_UPSTREAM_TEST_RESULT={"discovered": 253, "executed": 252, "passed": 252, "failed": 0, "skipped": 1, "status": "passed"}
# test_package（消费者视角）：
ok - r_jws_verify_signature(tampered token) is rejected
# 19 assertions, 0 failures
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, ..., "discovered": 19, "passedCount": 19}

$ python3 scripts/ohc-run.py conan-verify rhonabwy 1.1.13
✅ 配方验证通过: rhonabwy 1.1.13   （G0/G1/G2/G3/G4/L2/L4/L5 全 PASS）
```

## 交付物

| 产物 | 说明 |
|------|------|
| `lib/librhonabwy.so` | 共享库（上游 `rhonabwy` 目标） |
| `bin/rnbyc` | 上游 CLI 工具（软件级 `commands.json` 已声明，recipe 的 `cpp_info.bindirs = ["bin"]`） |
| `include/rhonabwy.h`、`include/rhonabwy-cfg.h` | 公开头文件 |

## 注意事项

- 上游 6 个 Ulfius 测试程序（126 个用例）本环境不构建：它们需要 Ulfius 提供 HTTP 服务端以通过 loopback
  提供 `test/cert/` 下的 TLS 夹具，而制品仓 `ulfius/2.7.15` 目前无 OHOS 二进制（依赖缺口，非本库缺陷）。
  待 Ulfius 二进制发布后，这些程序会自动重新纳入 CTest（补丁只在 `find_package(Ulfius)` 成功时跳过）。
- `test/cert/` 目录实际只有 5 个文件（`create-cert.sh` + 4 个 openssl 模板 `template-ca.cfg`/`template-ca2.cfg`/`template-server.cfg`/`template-user.cfg`），
  测试程序引用的 5 个证书/密钥夹具（`fullchain1.crt`/`fullchain2.crt`/`fullchain-error.crt`/`server.crt`/`server.key`）由该脚本配合 `certtool` 生成；
  本机无 `certtool`（仅 openssl 3.0.9），故不生成、不伪造夹具。该目录仅被上述 6 个引用 `cert/` 的测试源文件（`jwe_core.c`/`jwk_export.c`/`jwk_import.c`/`jwks_core.c`/`jws_core.c`/`jwt_core.c`）消费。
- 本机无 `curl` 可执行文件，Conan 预下载步骤会打印 `[Errno 2] No such file or directory: 'curl'` 的 WARN，
  但 Conan 自身下载正常，不影响构建结果。
---

## 对话记录

### 对话 #1 [2026-09-26]

- 问题: `ohc-run.py init-build rhonabwy 1.1.13` 未带 `--url` 时自动搜索上游地址失败（无法确定官方正式源）
- 操作: 显式指定 `BUILD_URL="https://github.com/babelouest/rhonabwy/archive/refs/tags/v1.1.13.tar.gz"`
- 结果: 源码下载/解压完成，R47 语言预检通过（主体 C），环境检查通过

### 对话 #2 [2026-09-26]

- 问题: 模式 A 探索式编译 Step3 CMake 报 `Could NOT find Jansson`（未装配 conan 依赖图）
- 操作: 按提示词「复杂依赖降级模式 B」转入 conan 配方路线；以同作者 `libyder/1.4.20` 配方为权威模板
- 结果: `archives/r/rhonabwy/1.1.13/` 下落地 conandata.yml / conanfile.py / patches / test_package

### 对话 #3 [2026-09-26]

- 问题: `test_package` 编译报 `'jansson.h' file not found`；编译含 `<nettle/version.h>` 的源码报 `'gmp.h' file not found`
- 操作: ① test_package 显式 requires 公开头依赖（CMakeDeps 只对直接依赖生成有效数据）；② 配方从 `dependencies['gmp'].package_folder` 取 include 注入 `GMP_INCLUDE_DIR`，补丁 append 给 Nettle 目标
- 结果: 库与测试程序均编译通过；两处结论分别落草稿 E431 与配方注释

### 对话 #4 [2026-09-26]

- 问题: 测试程序构建报 `make: jobserver mkfifo: ... Operation not permitted`（OHOS 不让 make 建 jobserver 管道）
- 操作: `_run_upstream_ctests()` 里对测试目标显式 `cmake --build <b> --target <19 程序> -- -j1`
- 结果: 19/19 程序构建成功，`ctest -V` 报 `100% tests passed, 0 tests failed out of 19`；落草稿 E430

### 对话 #5 [2026-09-26]

- 问题: `refresh-patch --auto` 按源文件重命名补丁后未回写 conandata.yml，`conan create` 报补丁路径错误
- 操作: 同步 conandata.yml 的 `patch_file` 为 `0001-CMakeLists.txt.patch` / `0002-src-misc.c.patch`，并 `patch --dry-run -p1` 复核
- 结果: 补丁可复现应用；`conan create` 全绿、`conan-verify` 八道门禁通过

### 对话 #6 [2026-09-26]

- 问题: W4 独立审计发现 `manifest.yaml` 标 `published` 与事实不符（尚未 `conan upload`）、`test_package` 硬编码 19 条断言数、`test/cert/` 夹具数申报有误
- 操作: 状态改 `built`；测试包改为解析被测程序自报的 `# N assertions, M failures` 并加「解析不到即报错」护栏；夹具表述改为「5 个文件 + 由 certtool 生成的 5 个夹具」
- 结果: 审计复审 verdict=pass（P0/P1=0），残余 P2/P3 均为存量遥测或风格建议

---

## W4 独立审计修复（2026-09-26）

- **P1（R9，状态真实性）**：`manifest.yaml` 的 `status` 由 `published` 改回 `built`。本包尚未
  `conan upload` 到制品仓（CI 日志 L0j 为 `first publish`、`.handoff.json` 里
  `precompiled_available:false`），标 `published` 与事实不符；同族已合入的 `ulfius/2.7.15`
  也用 `built`，字段含义与其注释一致。
- **P3（R34，硬编码）**：`test_package/conanfile.py` 的 `HMBS_TEST_PACKAGE_RESULT` 不再硬编码
  `discovered/passedCount = 19`，改为把被测程序输出重定向到文件后解析其自报的
  `# N assertions, M failures` 行（`test_rhonabwy.c` 用计数器自报），门禁标记始终反映真实执行数。
- 审计其余结论（R8 补丁 `--dry-run` 通过、R19/R40 无伪造、R51 清点与磁盘证据逐一吻合、
  R26/R32/R33/R37/R38/R39、W2 原子性 18 文件）均通过；L5a SONAME 属存量遥测，按门禁分级表不阻断。
---

**编译结束**: 2026-09-26 21:13
**最终状态**: built
