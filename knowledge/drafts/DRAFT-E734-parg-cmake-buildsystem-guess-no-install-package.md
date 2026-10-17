# E-DRAFT E734: 纯 CMake 小库适配三件套（parg 1.0.3 实证）

- **触发实例**：parg 1.0.3 全新包适配（2026-09-25，任务 parg-1.0.3，分支 `feat/parg-1.0.3`）
- **上游**：`https://github.com/jibsen/parg/archive/refs/tags/v1.0.3.tar.gz`（tag `v1.0.3`，sha256 `cd54a94b4138735f6c9fbdf426a9caa8ffd5bc90988eb02f493bc86de61ce5ad`，21704 字节）
- **类别**：构建系统判定 / conan-init 模板选择 / 无 install() 规则 / 测试计数口径
- **严重度**：2（确定性复现；不改工具即可绕过，但会把排查方向带偏）
- **配对**：`knowledge/drafts/DRAFT-E734-parg-cmake-buildsystem-guess-no-install-package.kv`

> 逐字证据：`$HOME/tmp/parg-1.0.3/repro-autotools.log`（autotools 模板配方失败现场）、
> `$HOME/tmp/parg-1.0.3/local-conan-create.log`（正确配方全绿 + greatest 汇总行）、
> `$HOME/tmp/parg-1.0.3/upstream-greatest.log`（沙箱 HOME 上游套件）。

## 症状（三段，形态互不相似）

1. `.build-context-parg-1.0.3` 写着 `export BUILD_SYSTEM="autotools"`，而源码根**只有** `CMakeLists.txt`
   （无 `configure`、无 `Makefile`）；`init-build` 同时打印
   `⚠️   conanfile.py 模板不可用（autotools），跳过`、`⚠️   验证缺失: ['conanfile.py', 'conandata.yml']`。
2. 照此跑 `conan-init`，产出的配方 import `conan.tools.gnu`（`Autotools`/`AutotoolsToolchain`）
   并追加 `--enable-static`；`conan create` 在 build() 处失败：

   ```text
   RUN: "/storage/Users/currentUser/.conan2/p/b/parga1574eda8b488/b/configure" --disable-shared --enable-static ...
   /system/bin/sh: /storage/Users/currentUser/.conan2/p/b/parga1574eda8b488/b/configure: inaccessible or not found
   ERROR: parg/1.0.3: Error in build() method, line 30
       autotools.configure()
   ```
3. 换成正确 cmake 配方后全绿，但 `ctest` 汇总只打 `100% tests passed, 0 tests failed out of 1`
   ——上游真实口径（32 用例 / 196 断言）只在测试程序 stdout，不在 ctest 汇总里。

## 根因

### ① 构建系统判定链的第一优先级是「URL 关键词」，不是源码事实

`scripts/ohc/init_build.py::_guess_build_system(url)` 只看 URL 字符串：

```python
def _guess_build_system(url: str) -> str:
    u = url.lower()
    if "cmake.org" in u or "cmake" in u:
        return "cmake"
    ...
    return "autotools"      # ← 兜底分支
```

GitHub tag 归档 URL `…/jibsen/parg/archive/refs/tags/v1.0.3.tar.gz` 不含 "cmake" → 判 `autotools`。
`scripts/ohc/conan_recipe.py::_detect_build_system()` 的优先级是
**env `BUILD_SYSTEM`（init-build 写入）→ manifest → 源码目录探测**，于是源码里的 `CMakeLists.txt`
排在最后、根本轮不到，`conan-init` 套用 `conanfile-autotools.py.tmpl`。

**同一任务里另两处判定都是对的**：`lang-preflight` 输出
`"language_evidence": {"build_system": "cmake", "manifest": "CMakeLists.txt project(parg C)"…}`、
`prescan` 输出 `"metadata": {"build_systems": ["cmake"]}`。错的那套恰好是喂给配方生成器的输入。

复现（设备可直接执行，输出 `guess = autotools`）：

```sh
cd $HOME/tmp/parg-1.0.3 && python3 -c "
import sys; sys.path.insert(0, '$HOME/ws/worktrees/parg-1.0.3/scripts')
from ohc.init_build import _guess_build_system as g
print('guess =', g('https://github.com/jibsen/parg/archive/refs/tags/v1.0.3.tar.gz'))"
```

### ② 上游 CMakeLists.txt 没有 `install()` 规则

上游只有 `add_library(parg parg.c parg.h)`、`add_executable(test_parg …)`、`add_test(test_parg test_parg)`，
从不写 `install()`。照模板 `cmake.install()` 是**空操作**，包里不会有 `include/`、`lib/`（G4 产物完整性必空手）。

### ③ `ctest` 汇总按「注册条目」计数，单头框架按「用例」计数

上游 `include(CTest)` 只注册 1 条 `test_parg`，所以 ctest 打 `out of 1`；greatest 框架的
`Total: 32 tests …, 196 assertions / Pass: 32, fail: 0, skip: 0` 只在测试程序 stdout。
PR 正文要填的上游 N=32 若只依据 ctest 汇总，正文数字没有设备日志可复算（rule4 少报高危）。

## 方案（四步，零补丁、不改工具）

1. **以源码事实纠偏**：不信 `conan-init` 的产物，按 `templates/conanfile-cmake.py.tmpl` 手写配方
   （`CMakeToolchain` + `cmake_layout` + `BUILD_SHARED_LIBS=OFF` + `BUILD_TESTING=ON`）；
   `manifest.yaml` 顶层 `build_system` 与 `build.system` 两处都钉 `cmake`
   （`clean_verify` G0 探测链 CMake > meson > configure > Makefile，钉错会去找 `./configure`）。
2. **无 `install()` 就在 `package()` 里 `copy()`**：`parg.h → include/`、`libparg* → lib/`
   （`keep_path=False`）、`LICENSE → licenses/`。**不要**为此给上游补 `install()` 补丁——
   copy 方案零补丁、G4 照过。
3. **上游测试进 `build()` 且打两遍**：先 `cmake.test()`（保住 `ctest` 注册面与 CI 同源），
   再 `self.run(os.path.join(self.build_folder, "test_parg"))` 直跑一次，让 greatest 汇总行
   进 `conan create` 日志；`can_run(self)` 守卫。
4. **N 口径三处对齐**：源码 `TEST ` 宏数（32）== `RUN_TEST` 注册数（32）== 框架汇总 `Total`（32）
   才声明 N=32；196 是 assertion 数，单列不混；`test_package` 消费者 4 用例 / 44 断言只进
   PR 正文「鸿蒙特有测试」行与 `test_package/MANIFEST.yml`，不进上游分母。

## 边界（何时不适用）

- 上游**确实**是 autotools（URL 里没有 cmake 且源码根有 `configure.ac`/`configure`）→ 判定结果恰好正确，照常走。
- 上游有 `install()` 规则 → 直接 `cmake.install()`，本条第 ②步不需要。
- 上游测试是 shell/pytest 等非 CTest 可执行面 → 用各自的 runner，第 ③步的「直跑二进制」不适用，
  但仍要保证**用例级**计数有设备日志可复算。
- 若 `init-build`/`conan-init` 将来把判定改为读源码（工具侧修复），第 ①步自动消失；
  第 ②③④步与工具无关，仍适用。

## 验证证据

- autotools 模板配方失败：`conan create` rc=1，`/system/bin/sh: …/b/configure: inaccessible or not found`
  → `$HOME/tmp/parg-1.0.3/repro-autotools.log`（同型 toybox 措辞见 `device-facts` §一.26）。
- 正确 cmake 配方：`conan create` rc=0，日志含
  `Total: 32 tests (479 ticks, 0.000 sec), 196 assertions` + `Pass: 32, fail: 0, skip: 0.`
  + `100% tests passed, 0 tests failed out of 4`（消费者 4/4）→ `$HOME/tmp/parg-1.0.3/local-conan-create.log`。
- 沙箱 HOME 独立跑（`HOME=$HOME/tmp/parg-1.0.3/test-home`、`env -i` 最小环境）：
  `ctest` 1/1 Passed + 直跑 `32 tests / 196 assertions` 全 PASS → `upstream-greatest.log`。
- 打包面：`conan cache path parg/1.0.3:<pkgid>` → `include/parg.h`、`lib/libparg.a`（ar archive）、`licenses/LICENSE`。
