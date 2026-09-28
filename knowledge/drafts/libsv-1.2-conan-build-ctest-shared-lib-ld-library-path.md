# conan build() 内跑 ctest 加载共享库失败：三连环修复（rpath 缺失 / conan 剥环境 / build_folder 陷阱）

> 草稿（DRAFT）。与同目录 `libsv-1.2-conan-build-ctest-shared-lib-ld-library-path.kv` 成对。

## 适用场景

conan 2 配方在 `build()` 内执行上游 ctest（如 `ctest --test-dir <build> --output-on-failure`），
被测库为**共享库**（`shared=True`），测试程序与 lib*.so 同在 conan 构建树、
且产物**未安装**到 package 目录（构建期测试）。OHOS（musl）真机环境。

## 现象

```text
1/7 Test #1: comp .............................***Failed    0.03 sec
Error loading shared library libsv.so: (needed by .../build/Release/test_comp)
Error relocating .../build/Release/test_comp: semver_compn: symbol not found
...
0% tests passed, 7 tests failed out of 7
```

测试程序**能启动**（排除签名/执行权限问题），只败在 musl 加载器找不到
构建树里的 lib*.so。

## 根因（三环叠加，缺一解不掉）

1. **构建树产物无 rpath**：OHOS 工具链链接的测试二进制不带 RUNPATH
   （readelf -d 无 rpath/runpath 段），运行期完全依赖 `LD_LIBRARY_PATH`。
   注意与 E088 的边界：E088 讲系统 musl namespace 忽略 RUNPATH/
   LD_LIBRARY_PATH；但**hnp worker 的 conan 构建环境下 LD_LIBRARY_PATH
   是有效的**（实测手动跑 7/7 通过）——不要一看到库加载失败就套 E088。
2. **conan 的 self.run 会剥离命令级变量前缀**：把
   `LD_LIBRARY_PATH="..." ctest ...` 写进 `self.run()` 的命令字符串
   **无效**——profile `[buildenv]` 注册了同名变量（LD_LIBRARY_PATH），
   conan 的环境管理会用自己管理的值覆盖 shell 级前缀。
3. **cmake_layout 的 build_folder 陷阱**：`self.build_folder` 本身就
   **是** `<...>/build/Release`（单配置生成器的输出目录）。再拼
   `"build/Release"` 会得到不存在的 `<...>/build/Release/build/Release`，
   LD_LIBRARY_PATH 指向空处，症状与没设置一模一样。

## 解法（r6 实测全绿：上游 7/7 + test_package 26 断言 + 门禁全过）

生成包装脚本，**在脚本内部 export**（脚本内部设置不受 conan 环境管理影响）；
`lib_dir` 用 `self.build_folder` 并做存在性兜底：

```python
from conan.tools.files import save

def _run_upstream_tests(self):
    lib_dir = self.build_folder  # cmake_layout: 即 build/Release
    if not os.path.isfile(os.path.join(lib_dir, "libsv.so")):
        fallback = os.path.join(self.build_folder, "build", "Release")
        if os.path.isfile(os.path.join(fallback, "libsv.so")):
            lib_dir = fallback
    log_path = os.path.join(self.build_folder, "upstream-ctest.log")
    script = os.path.join(self.build_folder, "run-upstream-ctests.sh")
    save(self, script,
         "#!/bin/sh\n"
         'LD_LIBRARY_PATH="%s" ctest --test-dir "%s" --output-on-failure'
         ' > "%s" 2>&1\n'
         "exit $?\n" % (lib_dir, self.build_folder, log_path))
    self.run('sh "%s"' % script)
```

（ctest 从 PATH 解析；启动会话需带工具链 PATH，见姊妹草稿
`libsv-1.2-shadow-ci-runner-toolchain-path`。）

## 附带事实

- **适配版 conan（2.29.1）的 `ConanFile` 没有 `can_run()`**（AttributeError
  实测）；交叉守卫用 `from conan.tools.build import cross_building`。
- test_package 的 `test()` 里运行安装后的二进制用
  `self.run(..., env="conanrun")`——conanrun 对 shared 包提供指向
  package 目录 lib 的 LD_LIBRARY_PATH（lasi/laszip 同款）。

## 诊断捷径（本轮实证的顺序）

1. 先在设备上手动复刻：`LD_LIBRARY_PATH=<build输出目录> ctest --test-dir <同目录> --output-on-failure`
   ——手动过、conan 里不过 → 必是环境传递/路径拼接问题，不是库本身。
2. 检查 conan 日志的 `RUN:` 行：**脚本/命令实际落点**会暴露 build_folder
   的真实层级（r5 即由此发现脚本生成在 `.../build/Release/run-upstream-ctests.sh`）。

## 证据（libsv 1.2，2026-09-27，r3→r6）

- r3/r4：ctest 0/7（无 rpath）。r4 命令级前缀 → 仍 0/7（被 conan 剥离）。
- 设备手动：`LD_LIBRARY_PATH="$R" ctest --test-dir "$R" --output-on-failure`
  → **100% tests passed, 7/7**（证明方案本体正确 + hnp 环境 LD_LIBRARY_PATH 有效）。
- r5：包装脚本方式 + 错误 lib_dir（`build_folder + "/build/Release"`）→ 仍 0/7。
- r6：lib_dir 改为 `self.build_folder`（兜底探测）→ ctest 7/7，
  `HMBS_UPSTREAM_TEST_RESULT passed (executed=7, failed=0)`，
  test_package `26 checks, 0 failures`，L0/L1/L4/L5 全 pass。
