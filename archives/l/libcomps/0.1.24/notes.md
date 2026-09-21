# libcomps 0.1.24 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake 工程根是 `libcomps/` 子目录）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK，`/data/service/hnp/bin`）
- 状态: built
- 设备: HarmonyOS PC aarch64，`os=OHOS 6.0`，`clang 15`，CMake 4.1.2，Conan 2.29.1

## 上游信息
- 软件: libcomps —— RPM/DNF 生态的 comps（软件包组）XML 库，C 实现 + Python 3 绑定
- 版本: 0.1.24（上游 GitHub tag `0.1.24`）
- 官方源: `https://github.com/rpm-software-management/libcomps/archive/refs/tags/0.1.24.tar.gz`
- sha256: `c24a81dea8e9f7f3c877618d3812a5293df772abc6b90fad1d34fa62326141bc`（3,711,141 字节）
- 许可证: GPL-2.0-or-later（`COPYING`）
- 语言: 主体 C（49 个 `.c` + 头文件，占源文件 89%），另有 Python 绑定与测试脚本

### 顶层 `pyproject.toml` / `setup.py` 是绑定打包 manifest（人工逐份核验）
tarball 顶层有 `pyproject.toml`、`setup.py`、`setup_for_python_metadata.py`、`MANIFEST.in`，
它们是 **PyPI wheel（`libcomps`）的 scikit-build 打包元数据**，不是本包主体语言的证据：

| 文件 | 内容 | 判定 |
|---|---|---|
| `pyproject.toml` | `[build-system]` 指向 scikit-build-core，`[tool.scikit-build]` 段 | wheel 打包配置 |
| `setup.py` | 调用 `setup_for_python_metadata.py`（读取 `version.json` 供 `install_egg_info`） | wheel 元数据 |
| `MANIFEST.in` | sdist 文件清单 | wheel 打包配置 |

真正的构建入口是 `libcomps/CMakeLists.txt`：`project(libcomps C)`，`libcomps/src/CMakeLists.txt`
的语言与源文件清单一律是 C（`comps_*.c`/`comps_*.h`），Python 只是 `add_subdirectory(python)`
的绑定子目录。本包 R47 语言预检**实跑通过**：`detected_language=c`、`expected=cpp`、
证据 `CMakeLists.txt project(libcomps C)`、源文件 `c:49, python:6`（主体占比 89%），
**未命中**「绑定 manifest 被当主体语言 → mixed/env_unsupported」的已知假阳性，因此没有跳步。

## 上游测试清单（清点，附取数命令与读数）

上游 0.1.24 的测试面由两套框架组成，**注册面**如下（单位＝"用例/注册数"；断言数属另一单位，只披露不并入）：

| # | 候选口径 | 取数命令 | 读数 |
|---|---|---|---|
| M1 | CMake 测试可执行目标数 | `grep -c '^add_executable' libcomps/tests/CMakeLists.txt` | 6 |
| M2 | Check 框架注册数（全部 `check_*.c` 源码） | `grep -c tcase_add_test libcomps/tests/check_*.c` 逐文件求和 | 24 |
| M3 | Check 框架注册数（被构建的 4 个） | 同上但排除被注释掉的 `check_list.c` | 18 |
| M4 | Check 框架注册数（上游 `test` 目标实际驱动的） | `ctest` 只依赖 `test_comps_run`/`test_parse_run` | 13 |
| M5 | Python 源码 `def test` 字面计数 | `grep -cE '^\s*def test'` 三个测试模块求和 | 62 |
| M6 | Python unittest 注册数（展开基类继承后 `unittest` 实际收集的 test id） | 见下方脚本 | 99 |

`M6` 的取数脚本（AST 展开类继承，与 `unittest` 的收集规则一致）：

```sh
# $SRC = 解压后的源码根
python3 - "$SRC/libcomps/src/python/tests" <<'PY'
import ast, os, sys
d = sys.argv[1]; grand = 0
for fn in ("__test.py", "test_libcomps.py", "test_merge_comps.py"):
    tree = ast.parse(open(os.path.join(d, fn), encoding="utf-8").read())
    def bname(b):
        return b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else "?")
    classes = {n.name: ([bname(b) for b in n.bases],
                        [f.name for f in n.body
                         if isinstance(f, ast.FunctionDef) and f.name.startswith("test")])
               for n in tree.body if isinstance(n, ast.ClassDef)}
    def tests_of(name, seen=frozenset()):
        if name in seen or name not in classes:
            return []
        bases, own = classes[name]
        out = list(own)
        for b in bases:
            for t in tests_of(b, seen | {name}):
                if t not in out:
                    out.append(t)
        return out
    mod = sum(len(tests_of(c)) for c, (bases, _) in classes.items()
              if any(x.endswith("TestCase") for x in bases))
    print(fn, mod); grand += mod
print("TOTAL", grand)
PY
```

**声明的上游 N = 123**（= M6 的 99 + M2 的 24，即"用例/注册类"候选口径的最大组合；M6 单侧最大 99，
其余口径均低于此）。逐项归因差额：

| 组成 | 用例数 | 本次是否运行 | 说明 |
|---|---|---|---|
| `test_comps`（`check_comps.c`） | 5 | 运行 PASS | 上游 `test` → `ctest` → `test_comps_run` |
| `test_parse`（`check_parse.c`） | 8 | 运行 PASS | 上游 `test` → `ctest` → `test_parse_run` |
| `__test.py` | 84 | 运行 PASS | 上游 `pytest_run` → `run_tests.sh` |
| `test_libcomps.py` | 11 | 运行 PASS | 同上 |
| `test_merge_comps.py` | 4 | 运行 PASS | 同上 |
| `test_objrtree`（`check_objrtree.c`） | 1 | NOT_RUN | **上游未接线**：`ctest` 只依赖 `test_comps_run`/`test_parse_run`，该可执行文件被构建但无任何运行目标 |
| `test_validate`（`check_validate.c`） | 4 | NOT_RUN | 同上 |
| `test_list`（`check_list.c`） | 6 | NOT_RUN | **上游未构建**：`libcomps/tests/CMakeLists.txt` 把 `add_executable(test_list ...)` 与 `target_link_libraries` 全部注释掉 |
| **合计** | **123** | 运行 112 | `TOTAL = PASS 112 + FAIL 0 + SKIP 0 + NOT_RUN 11` |

`test_rtree` / `test_brtree` 是**手工演示程序**（只有 `main()`，0 个 Check 注册），不计入 N。

> `pytest_run` 的说明：上游 0.1.24 的顶层 `CMakeLists.txt` 写的是
> `add_custom_target(pytest)`（**无依赖**），而 Python 测试驱动 `pytest_run` 定义在
> `libcomps/src/python/src/CMakeLists.txt`，所以 `make test` 实际只跑 C 套件。
> 本包的 Python 绑定（`libcomps/__init__.py` + `_libpycomps.so`）是**随包交付的制品**，
> 因此配方显式构建 `pytest_run` 以验证它；这是运行上游已注册目标，不是新开构建开关。

## 编译步骤

```sh
# 1. 源码：配方 source() 用 get(strip_root=True)，得到 <src>/{libcomps/,version.cmake,...}
# 2. 应用 3 个补丁（见下"源码修改"）
# 3. 生成工具链：CMakeDeps + CMakeToolchain（默认 Unix Makefiles）
#    显式钉住依赖变量（否则命中宿主 ~/.harmonybrew，见问题 2）
# 4. cmake.configure(build_script_folder="libcomps")  ← 上游 CMake 工程在 libcomps/ 子目录
# 5. cmake.build()
# 6. cmake.build(target="test")       ← test_comps + test_parse
# 7. cmake.build(target="pytest_run") ← __test.py + test_libcomps.py + test_merge_comps.py
# 8. cmake.install() → lib/libcomps.a、include/libcomps/*.h(26)、lib/pkgconfig/libcomps.pc、
#                      python/site-packages/libcomps/{__init__.py,_libpycomps.so}
```

驱动命令（本次实际使用）：

```sh
cd archives/l/libcomps/0.1.24
CONAN_HOME="$HOME/.conan2" HOME="$TASK_DIR/test-home" \
  conan create . \
  -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$REPO/ci/conan/profiles/ohos-aarch64" \
  -c tools.build:jobs=1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: error: unable to find library -lexpat` | `libcomps/tests/CMakeLists.txt` 用裸名 `expat` 链接（`target_link_libraries(test_parse expat)`），只在 libexpat 位于默认库搜索目录时成立 | 补丁 0002 改为 CMake 刚找到的 `${EXPAT_LIBRARY}` |
| 2 | 产物静默链接到宿主 `~/.harmonybrew` 的 libxml2/zlib（`LIBXML2_LIBRARY`、`ZLIB_DIR` 指向 brew），干净 worker 必红 | Conan 的 CMakeToolchain 写 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`；配方未调用 CMakeDeps，且上游读的是 Find 模块的旧式变量（大写），CMake 于是回落到设备 PATH 上的 brew 前缀 | 配方调用 `CMakeDeps(self).generate()`，并把上游读到的每个变量（`LIBXML2_INCLUDE_DIR/LIBRARY/LIBRARIES`、`EXPAT_INCLUDE_DIR/LIBRARY/LIBRARIES`、`ZLIB_INCLUDE_DIRS/LIBRARY/LIBRARIES`、`CHECK_INCLUDE_DIR/CHECK_LIBRARY`、`PYTHON_*`）钉到 Conan 包目录 |
| 3 | 测试二进制 `Error relocating ./test_comps: XML_ParserCreate: symbol not found` | 上游测试目标的命令写 `export LD_LIBRARY_PATH="${LIBCOMPS_OUT}/:$LD_LIBRARY_PATH"`：Makefile 生成器把 `$L` 当 make 变量、Ninja 生成器把 `$LD_LIBRARY_PATH` 当 ninja 变量，**两种生成器都把继承值清空** | 补丁 0002 改为 `$$LD_LIBRARY_PATH`（两个生成器都会还原成 `$` 交给 shell） |
| 4 | `check_msg.c:317: Unable to create temporary file for communication` | check 的 IPC 临时文件受 `TEMP`/`TMPDIR` 控制，设备 `/tmp` 只读 | 配方在 `_environment(for_tests=True)` 里把 `TMPDIR`/`TMP`/`TEMP` 指到构建目录内可写目录，并置 `CK_FORK=no` |
| 5 | 消费者编译失败：`'libxml/encoding.h' file not found`，随后 `'comps_types.h' file not found` | ① 传递依赖默认不传播头文件（`transitive_headers` 默认未开启），CMakeDeps 生成的传递依赖 config 里 `INCLUDE_DIRS` 为空；② 上游 `install(FILES ${libcomps_HEADERS})` 清单漏了 `comps_types.h`，而已安装的 `comps_log.h` 会 include 它 | ① `self.requires("libxml2/...", transitive_headers=True)`，expat 同理；② 补丁 0003 把 `comps_types.h` 加进安装清单 |
| 6 | Python 模块会被装到解释器的绝对 site-packages（污染 `python/3.12.9` 依赖包） | 上游 `EXECUTE_PROCESS(... get_path('platlib'))` 得到绝对路径，`INSTALL(... DESTINATION <绝对路径>)` 无视 `--prefix`/`DESTDIR` | 补丁 0001 增加 `IF (NOT PYTHON_INSTALL_DIR)` 覆盖钩子；配方传 `<package_folder>/python/site-packages` |
| 7 | `setup_for_python_metadata.py install_egg_info` 打印 `ModuleNotFoundError: No module named 'setuptools'` | 该步生成 PyPI egg-info，Conan 的 `python/3.12.9` 不含 setuptools | 非致命（`INSTALL(CODE)` 不检查返回码），制品不受影响；仅构建日志有 traceback，已如实记录 |
| 8 | `pytest` 目标不执行 Python 测试 | 上游 0.1.24 顶层 `add_custom_target(pytest)` 无依赖，`pytest_run` 未被接入 | 配方显式 `cmake.build(target="pytest_run")`（见上"上游测试清单"说明） |

## 源码修改

| 补丁 | 作用 |
|---|---|
| `patches/0001-python-binding-install-dir.patch` | `libcomps/src/python/src/CMakeLists.txt`：允许打包器用 `PYTHON_INSTALL_DIR` 覆盖解释器绝对 site-packages（原逻辑无条件用 `EXECUTE_PROCESS` 覆盖该变量，绝对路径会逃出包目录） |
| `patches/0002-tests-portability.patch` | `libcomps/tests/CMakeLists.txt`：① 链接 CMake 找到的 `${EXPAT_LIBRARY}` 而非裸名 `expat`；② `$LD_LIBRARY_PATH` → `$$LD_LIBRARY_PATH`，使构建生成器不再吞掉继承的库搜索路径 |
| `patches/0003-headers-install-comps-types.patch` | `libcomps/src/CMakeLists.txt`：把 `comps_types.h` 加进 `libcomps_HEADERS` 安装清单（已安装的 `comps_log.h` 依赖它） |

三个补丁都只改**构建脚本**，不改任何 C 源码，也不引入平台宏（`__OHOS__` 零出现）。

## 依赖版本

`zlib/1.3.1.1`、`libxml2/2.15.3.1`、`expat/2.8.2.1`、`python/3.12.9`（host requires，绑定链接 libpython）；
`check/0.15.2`（`build_requirements()` 里的 `test_requires`，只服务上游 Check 套件，不进链接接口）。
W0 预检 5 条全部命中已发布制品（`conan install --build=never` 全通过）。

## 验证结果

```
# 上游 C 套件（cmake --build . --target test）
100%: Checks: 5, Failures: 0, Errors: 0     ← test_comps
100%: Checks: 8, Failures: 0, Errors: 0     ← test_parse

# 上游 Python 绑定套件（cmake --build . --target pytest_run）
Ran 84 tests ... OK                         ← __test.py
Ran 11 tests ... OK                         ← test_libcomps.py
Ran 4 tests  ... OK                         ← test_merge_comps.py

# 消费者测试（test_package）
libcomps consumer test: 30 checks, 0 failures
libcomps consumer test PASSED

# 结论
libcomps/0.1.24: Package '88695f031cf3d4a32d60d097ae7f554c65cb87d7' created
```

上游通过率 112/123（91.06%）；`test_package` 消费者 30/30。以上**计数**读数与采信轮权威日志 `reports/conan-create.log` 逐项一致；unittest 的墙钟耗时每轮重跑都会变（`notes/device-facts.md` §二.18），故本笔记只引用计数、不引用秒数。
台账 `TOTAL 123 = PASS 112 + FAIL 0 + SKIP 0 + NOT_RUN 11`。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libcomps.a` | 静态库（`shared=False` 默认；`OUTPUT_NAME comps`，`cpp_info.libs=["comps"]`） |
| `include/libcomps/*.h` | 26 个公开头（含补丁 0003 补入的 `comps_types.h`） |
| `lib/pkgconfig/libcomps.pc` | pkg-config 元数据（`ENABLE_DEVELOPMENT=ON`） |
| `python/site-packages/libcomps/{__init__.py,_libpycomps.so}` | Python 3 绑定（补丁 0001 使其落在包内） |
| `licenses/COPYING` | GPL-2.0-or-later |

## 注意事项

1. **`comps_types.h` 是上游缺陷的补丁点**：上游 RPM 用 `%{_includedir}/libcomps/*.h` 通配安装，
   掩盖了 CMake 安装清单漏项；本包按归档规范用 CMake 安装，必须补丁，否则消费者无法编译。
2. **`check` 只用于构建期测试**：放在 `build_requirements()` 的 `test_requires`，不进 `package_info()`。
3. **Python 绑定链接 libpython**：`python/3.12.9` 是 host requires，使用者若要用绑定需在运行时
   具备 `libpython3.12.so`（Conan runenv 已提供）。
4. **构建期日志里的 `setuptools` traceback** 是上游 `install_egg_info` 步骤的环境缺口，不影响制品。
5. `ENABLE_DOCS=OFF`：上游 docs 目标需要 Doxygen，与制品无关。
