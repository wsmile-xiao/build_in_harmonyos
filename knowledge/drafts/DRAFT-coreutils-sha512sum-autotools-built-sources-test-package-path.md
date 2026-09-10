# DRAFT-coreutils-sha512sum-autotools-built-sources-test-package-path

## 问题 (Problem)

coreutils-sha512sum 9.11（GNU coreutils 9.11 单工具打包）在 HarmonyOS PC
(aarch64, Clang 15 / musl) 上 conan create：

1. 配方 build() 为"只产 sha512sum"而 `make -j2 src/sha512sum`，编译 lib/ 与
   src/ 时报：
   - `lib/group-member.c:24: fatal error: 'stdckdint.h' file not found`
   - `lib/hard-locale.c:30: error: use of undeclared identifier 'SETLOCALE_NULL_MAX'`
   - `src/system.h:73: fatal error: 'stdcountof.h' file not found`
2. 修复构建后，W3 本地 CI 的 L1e 破坏性负向测试又报：
   `[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)`

## 根因 (Root Cause)

1. **BUILT_SOURCES 生成机制**：coreutils 9.11（automake + gnulib）把 gnulib
   生成头（stdckdint.h / stdcountof.h / locale.h / configmake.h / error.h 等）
   全部登记在 `BUILT_SOURCES`。该变量只在默认 `all` 目标（及 `check`）里作为
   前置依赖被构建；配方直接 `make src/sha512sum` 只构建该目标的依赖链，生成头
   从未落盘，于是引用了这些头的 gnulib 源码（group-member.c 用 ckd_mul 需要
   stdckdint、hard-locale.c 需要 setlocale_null.h 的 SETLOCALE_NULL_MAX 宏与
   setlocale_null_r、src/system.h 用 stdcountof）编译失败。
   - 差异点：E313/E312 记录的是 "OHOS musl 缺 C23 stdckdint.h，需自建 shim 头
     注入"（Ruby gem extconf 场景）。本根因是 **automake 生成机制**缺失——同一
     报错符号、两层不同根因：平台缺头（E313）用补头解决；生成机制缺失（本条目）
     用走 all 目标让 make 自动生成解决，二者互不替代。
2. **test_package PATH 同名遮蔽**：test.sh 用裸 `sha512sum`，OHOS 系统自带
   coreutils 系二进制，PATH 解析命中系统二进制。W3 的 L1e 检测把包内 `bin/`
   移走后测试仍通过 → 判定测试未依赖包制品（R34 假测试）。

## 方案 (Solution)

1. `conanfile.py build()`：
   ```python
   autotools.make(args=[
       "-j2",
       "ACLOCAL=true", "AUTOMAKE=true", "AUTOCONF=true",
       "AUTOHEADER=true", "MAKEINFO=true",
   ])          # 默认 all 目标，BUILT_SOURCES 自动生成
   ```
   package() 阶段仍只把 `build_folder/src/sha512sum` 拷入 `bin/`。
2. `test_package/conanfile.py`：从依赖包取绝对路径传给测试脚本，测试内全部用 $1：
   ```python
   dep = self.dependencies[self.tested_reference_str]
   binary = os.path.join(dep.package_folder, "bin", "sha512sum")
   self.run(f"{bash} test.sh {binary}", env="conanrun")
   ```
   test.sh 内 `BIN="$1"`，所有调用 `"$BIN" ...`。

## 验证 (Verification)

- conan create G2 PASS、test_package (test.sh 4/4 + test_ohos.sh 4/4) PASS。
- W3 build_and_test.sh：`[ok] L1e: Negative test confirmed — test genuinely
  depends on coreutils-sha512sum`；L0/L1/L2/L4/L5 全 PASS；Build Summary
  100% (1/1)；`.ci-result.json` exit_code=0。
- 上游 sha512sum.pl 5/5 PASS；消费者验证：conan install 后文件/管道摘要一致且
  与宿主 sha512sum 交叉核对一致。

## 适用边界 / 反例

- 适用：autotools+gnulib 单工具打包的配方（coreutils 系、findutils、tar 等）；
  交付 CLI 且系统可能已有同名二进制的包（busybox/toybox/coreutils 单工具化）。
- 反例/不适用：CMake 系（无 BUILT_SOURCES 语义，E217/E309 相关）；
  E313 平台缺 stdckdint.h 的 shim 场景（补头方案仍正确，不因本条目改变）；
  E423 双工具链闭环比对、E240 能力边界拆分（负向测试不同机制）。

## 关系字段 (Relations)

- similar_to: E313 (stdckdint.h), E312 (msgpack stdckdint.h), E423 (负向测试),
  E240 (负向测试)
- caused_by: automake BUILT_SOURCES 机制 / R34-L1e 检测 + PATH 解析
- prerequisite_of: 所有 autotools 单工具包配方；所有 CLI 包 test_package 规范

*由 coreutils-sha512sum 9.11 R01 适配产出，路径 B 知识库扩展 (new_draft)*