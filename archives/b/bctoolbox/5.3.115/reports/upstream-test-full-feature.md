# 上游 tester 全量（35 用例）验证 — bctoolbox 5.3.115

> 目的：解决人工复审 rule4（`comment 188342686`：上游测试必须真实运行、通过率 100%、分母与审方数法一致）。
> 审方数法 N = 上游注册用例总数 = **35**（`grep -oE "TEST_NO_TAG|TEST_ONE_TAG|TEST_TWO_TAG" tester/*.c tester/*.cc | wc -l`）。
> 生成时间：2026-09-11（设备本地证据，`reports/` 在本仓库被 .gitignore，故结论同时写入 `test_package/MANIFEST.yml` 与 PR 正文）

## 1. 结论（分子 = 分母）

| 配置 | 编译 | 套件 | 用例 | PASS | FAIL | 断言 |
|------|------|------|------|------|------|------|
| 交付配置 `ENABLE_MBEDTLS=OFF`（= 发布包） | 通过 | 6 | **20** | 20 | 0 | 779 |
| 全特性验证配置 `ENABLE_MBEDTLS=ON` + 测试专用 mbedtls | 通过 | 8 | **35** | 35 | 0 | 103688 |

上游注册用例全集（35）在两套配置中**真实编译并执行**，全集 35/35 通过、0 失败、0 跳过。
交付包本身（不加 mbedtls）执行其中 20 个（crypto 10 + encrypted_vfs 5 由上游 `tester/CMakeLists.txt` 的
`if(MbedTLS_FOUND)` 门控，未编译进该配置，既非 PASS 也非 SKIP）。

用例分布（取数命令见上）：containers 7、crypto 10、encrypted_vfs 5、utils 4（`tester/port.c`）、vfs 3、
parser 2、param_string 2、logger 2；`tester/ios_utils.cc` 为 `__APPLE__` 专用，OHOS 不计入。

## 2. 交付配置（包内真跑，证据来自 `conan create`）

```sh
conan create "$HOME/ws/wt-bctoolbox-5.3.115/archives/b/bctoolbox/5.3.115" \
  -pr:h=.../ci/conan/profiles/ohos-aarch64 -pr:b=.../ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=missing --user=ohpcd --channel=stable
```

日志：`$HOME/tmp/bctoolbox-5.3.115/create-bcunit513-round6.log`（包创建成功，`test_package` 6/6 PASS）

```
Run Summary:    Type  Total    Ran Passed Failed Inactive
              suites      6      6    n/a      0        0
               tests     20     20     20      0        0
             asserts    779    779    779      0      n/a
```

测试在 `conanfile.py::build()` 内执行（`self.run("<build>/tester/bctoolbox-tester")`），退出码直接决定包构建成败。

## 3. 全特性验证配置（35/35）

验证变体目录：`$HOME/tmp/bctoolbox-5.3.115/full-feature-pkg`（**交付目录的副本，不入库、不发布**）。
与交付 `conanfile.py` 的差异仅三处（`diff -u` 全量差异见日志尾部）：

1. `requirements()` 增加 `self.requires("mbedtls/3.6.6")`；
2. `generate()`：`ENABLE_MBEDTLS = "ON"`（交付为 `OFF`）；
3. `generate()`：预置 `MbedTLS_TARGET`/`MbedX509_TARGET`/`MbedCrypto_TARGET = "mbedtls::mbedtls"`
   （原因同 BCUnit：`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` 使上游 `cmake/FindMbedTLS.cmake` 成死代码，
   而 `src/CMakeLists.txt:224` 与 `tester/CMakeLists.txt:49` 链接这三个变量）。

```sh
conan create "$HOME/tmp/bctoolbox-5.3.115/full-feature-pkg" \
  -pr:h=.../ci/conan/profiles/ohos-aarch64 -pr:b=.../ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=missing --user=verify --channel=fullfeature
```

日志：`$HOME/tmp/bctoolbox-5.3.115/full-feature-create.log`
refs：`bctoolbox/5.3.115@verify/fullfeature#226e71b97191caa5e4cb69770553e2a6:af69f187ae11278f1b7ce96a7e950a7865217c5c#e29b72d9a6543be3bac6044b533b5f36`

```
Run Summary:    Type  Total    Ran Passed Failed Inactive
              suites      8      8    n/a      0        0
               tests     35     35     35      0        0
             asserts 103688 103688 103688      0      n/a
```

四个补丁在两次构建中都出现在 `Apply patch` 日志中（`0001`…`0004`）。

## 4. 测试专用 mbedtls 3.6.6（仅测试用、不进包依赖链）

- 为什么必须自建：ohpcd 只有 `mbedtls/4.1.0`（v4 API，`bctoolbox 5.3` 仅兼容 v2/v3，实测首个致命错误为
  `mbedtls/ctr_drbg.h` 缺失）；仓库内 `archives/m/mbedtls/3.6.6/` 只有 `manifest.yaml`+`notes.md`，**没有 conanfile**，
  无法 `conan create`。按 workflow §7.3「测试框架/编译依赖未发布时从源码构建到任务私有 prefix，仅测试用」处置。
- 源码：`https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-3.6.6/mbedtls-3.6.6.tar.bz2`
  sha256 `8fb65fae8dcae5840f793c0a334860a411f884cc537ea290ce1c52bb64ca007a`（5508045 字节，`BZh`）
- 配方：`$HOME/tmp/bctoolbox-5.3.115/mbedtls-3.6.6-recipe/`（任务私有，未入库）
  refs：`mbedtls/3.6.6#8b668933e8deb99e6be8a712826572f3:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#e675a0edec4822cbd376f96403b551b6`
  （**仅存在于本地 cache，ohpcd 无此 ref**）
- 与普通发行构建的唯一差异：启用 `MBEDTLS_THREADING_C` + `MBEDTLS_THREADING_ALT` 并提供
  `include/mbedtls/threading_alt.h`（`typedef void *mbedtls_threading_mutex_t;`）。
  原因（实测编译错误）：`src/crypto/mbedtls.cc:40` 在 `MBEDTLS_VERSION_NUMBER >= 0x03060000` 时无条件定义
  `BCTBX_USE_MBEDTLS_PSA` 并调用 `mbedtls_threading_set_alt()`/`mbedtls_threading_free_alt()`/`psa_crypto_init()`；
  这些声明只在 mbedtls 配置开启 `MBEDTLS_THREADING_C` 时可见（`mbedtls/threading.h` 由 `ctr_drbg.h` 等按该宏包含），
  而 mbedtls 3.6.6 默认把 threading 注释掉 → 未启用时 4 个 `undeclared identifier` 错误。
  启用点写在**源码 config 头**而非仅消费者侧：线程开关会改变 mbedtls 上下文结构体是否含 mutex 成员，
  库与消费者必须一致。
- 上游注释佐证这是 BC 定制 mbedtls 的既知依赖：`mbedtls.cc:66` 注明
  "This is also defined in mbedtls source code by a custom modification"。

## 5. 交付包对 mbedtls 的处置（不变）

交付配方保持 `ENABLE_MBEDTLS=OFF`、依赖链中**没有** mbedtls：`MbedTLS_FOUND` 为假时上游仅少注册
crypto/encrypted_vfs 两个套件（`bctoolbox_tester.c` 内 `#if (HAVE_MBEDTLS)` 门控），核心库不含任何 stub。
若后续把 mbedtls 3.x 作为 Conan 包发布到 ohpcd（需按第 4 节的 threading 配置建包），下游只需把
`ENABLE_MBEDTLS` 置 `ON` 并加 `requires`，即可在交付包内直接跑满 35/35。
