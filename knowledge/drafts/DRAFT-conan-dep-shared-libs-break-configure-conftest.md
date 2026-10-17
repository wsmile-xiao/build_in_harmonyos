# DRAFT-conan-dep-shared-libs-break-configure-conftest

## 一句规则

Conan 依赖的共享库对 configure 的运行检测（conftest）不可见：`generate()` 必须把 host 依赖的 `libdirs` 注入 `LD_LIBRARY_PATH`（`bindirs` 注入 `PATH`），否则凡链共享库的 conftest 一律运行失败并把 configure 推入错误的交叉编译模式。

## 根因（机理链）

1. Conan 把依赖共享库放在缓存包目录（`~/.conan2/p/<pkg>/p/lib`）。
2. `AutotoolsToolchain`/`AutotoolsDeps` 只为编译/链接提供 `-I`/`-L`；运行期搜索路径不在其职责内。
3. autoconf 的 `AC_RUN_IFELSE` conftest 链接共享依赖后立即执行 → 平台加载器默认路径无此库 → `Error loading shared library libX.so: (needed by ./conftest)`。
4. autoconf 把运行失败归因为"不能运行编译出的程序"（`cannot run C compiled programs`）→ `cross_compiling=yes` → 后续检测全部使用假设值（级联同 E064 的后果链）。

## 与相近条目的边界

- **E064**：同 error_signature（`cannot run C compiled programs`），根因是安全确认弹窗超时（E054）。判别：config.log 中 `./conftest: inaccessible or not found`/exit 127 → E064；`Error loading shared library ... needed by ./conftest` → 本条。
- **E088**：安装运行态 musl namespace 忽略 `RUNPATH/LD_LIBRARY_PATH`。本条处于构建 shell 上下文（conanbuild/SSH），`LD_LIBRARY_PATH` 实证有效（探针）。
- **E019/E266/E269**：运行期/测试执行期的同思路环境注入，非 configure conftest 场景与 recipe `generate()` 注入模式。

## 方案空间

- **rec**：`generate()` 中 `Environment` 前置 host 依赖 `bindirs`→`PATH`、`libdirs`→`LD_LIBRARY_PATH`，`save_script()` 进 conanbuild（案例：dirb/2.22、aaphoto/0.45）。
- **fallback**：`ac_cv_*` 缓存变量或改链静态变体——仅覆盖检测层，须记录权衡。
- **forbid**：`--host/--build` 绕过（P-AUTOTOOLS-001）；拷 `.so` 进系统路径。

## 验证（自包含探针，任意新 shell 可跑）

见 .kv `verification_cmd`：无 `LD_LIBRARY_PATH` 运行报 `Error loading shared library libcurl.so`，注入依赖 libdir 后退出 0。设备实证存档：run dirb-2.22 `reports/curator/probes/conftest-deplib/`。

## 证据

- dirb run3：`ci-logs/build_and_test_run3.log:186-194`（cannot run C compiled programs → build() ERROR）→ run4 通过。
- aaphoto/0.45：`archives/a/aaphoto/0.45/conanfile.py`（generate 同款注入）、`notes.md` 失败表第 3 行（libpng16.so 同签名）。
