# DRAFT-case.c-0.2.0-makefile-no-install-static-lib-conan — 极简无 install 目标 Makefile 库的 Conan 配方模式 + 上游测试漏注册恢复

> **Contributor**: pc7-3 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium | **Category**: ohos / makefile / conan-recipe / testing
> **Audience**: 上游为"单文件/少量源码 + 纯 Makefile + 无 configure + 无 install 目标（Makefile 仅 test 目标）"的小型 C/C++ 库配方作者

## 问题（Problem）

极简 Makefile 库（如 case.c 0.2.0：仅 `src/case.c` + `src/case.h`，Makefile 只有 `test` 目标）在 OHOS Conan 流水线上出现两类问题：

1. **配方形态误判**：`conan-init` 按 URL 猜测构建系统为 autotools，生成 `Autotools` 配方；build() 调 `autotools.configure()` 时源码根无 `configure` 脚本，直接失败；`autotools.install()` 也因上游无 install 目标而无产物。
2. **测试声明漏注册**：上游 test.c 用宏 `TEST(name)` 声明了 13 个独立用例，但 `main()` 只 `RUN_TEST` 了 12 个（`camel_space_seperators` 漏注册），未注册用例永远不执行；按 SKILL 源码测试入口恢复规则，声明即须纳入实际运行。

## 根因（Root Cause）

1. 极简库无 configure/install 是上游刻意简化（小型工具库，用户自建构建方式），Conan 配方不能套 autotools/cmake 标准流程；URL 猜测的构建系统不可靠，必须以实际 Makefile 形态为准。
2. 上游测试宏体系（`TEST` + `RUN_TEST`）要求"声明 + 注册"两步，漏写注册是常见上游疏漏；双口径台账要求 `source_declared_total` 以源码声明数为分母，未注册用例必须恢复纳入。

## 最小方案（Minimal Solution）

### 模式 A：无 install 目标极简 Makefile 库的 Conan 配方骨架

```python
def build(self):
    apply_conandata_patches(self)
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c", "clang") if compilers else "clang"
    ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
    ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
    # 无 configure / 无 install 目标：手动编译静态库
    self.run(f"{cc} -std=c99 -O2 -c src/case.c -o case.o")
    self.run(f"{ar} rcs libcase.a case.o")
    if ranlib:
        self.run(f"{ranlib} libcase.a")
    # 集成上游测试并实际运行（R34：禁止空壳）
    self.run(f"{cc} -std=c99 test.c src/case.c -o test_case")
    bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
    self.run(f"{bash} -c './test_case'", env="conanrun")

def package(self):
    copy(self, "case.h", os.path.join(self.source_folder, "src"),
         os.path.join(self.package_folder, "include"))
    copy(self, "libcase.a", self.source_folder,
         os.path.join(self.package_folder, "lib"))

def package_info(self):
    self.cpp_info.libs = ["case"]
```

要点：

- **R33**：编译器从 `self.conf.get("tools.build:compiler_executables")` 获取，禁止裸用 `${CC}`（CI worker 上为空）。
- **R9**：手动编译用 `-j1` 语义（单文件无所谓，多文件也不要并发乱序）。
- `apply_conandata_patches` 在 build() 开头执行（补丁相对 `self.source_folder`，路径必须 `a/`、`b/` 前缀）。
- test_package 只经公开头文件/API 做消费者验证（编译 + 链接 + 运行 + 断言），禁止空壳。

### 模式 B：上游测试"声明但未注册"的最小补丁恢复

```patch
--- a/test.c
+++ b/test.c
@@ -122,6 +122,7 @@
   RUN_TEST(camel_empty_string);
   RUN_TEST(camel_hypen_seperators);
   RUN_TEST(camel_underscore_seperators);
+  RUN_TEST(camel_space_seperators);
   RUN_TEST(camel_leading_seperator);
   RUN_TEST(camel_trailing_seperator);
   printf("\n");
```

- 补丁只注册既已声明、测试逻辑完整的用例；不新增/不改断言、不伪造结果。
- 补丁后重新编译运行，台账按双口径：`source_declared_total`（源码声明数）与 `configured_executable_total`（注册执行数）一致时 13/13。

## R01 真实验证证据（Verified Evidence）

- 官方来源：`https://github.com/stephenmathieson/case.c` tag `0.2.0`，MIT；tarball SHA-256 `dbdd4ccb7d3daf6c6a16bce3a279eeef10ab3f9c4bd1047071ef06d9ea35efdf`。
- 补丁后上游测试：`clang -std=c99 test.c src/case.c -o test && ./test` → 13 个用例全部 ✓，退出码 0。
- conan-verify：G1-G4 + L2/L4/L5 全部 PASS（G2 conan create 成功）。
- 消费者 test_package：`case_lower`/`case_upper`/`case_camel` 3 断言 PASSED（只链公开产物 `-Iinclude -lcase`）。
- 环境：OHOS aarch64 clang 15.0.4，`os=OHOS arch=armv8`，Conan 2.29.1。

## 验证边界（Honest Validation Boundary）

- 本模式验证的是"配方可复现构建 + 上游测试全部实际执行 + 消费者经公开 API 可用"；不声称对更复杂构建系统的覆盖。
- 若上游存在 configure/install 目标（zlib 式），应走常规 autotools/cmake 流程，不套用本模式。

## 禁止做法（Forbidden）

- 把无 install 目标库硬套 autotools 配方（configure 失败后 sed 伪 install）。
- 把"已声明未注册"的用例写成未实例化/失败，或伪造 RUN_TEST 输出。
- 空壳 test_package（只打印字符串、不调用公开 API）。
- 复制库私有头文件/内部符号到消费者测试。
