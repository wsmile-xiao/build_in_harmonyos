# pforth 2.0.1 适配笔记

## 编译环境
- 构建系统: makefile（platforms/unix/Makefile，官方 CI 同款）
- 编译器: clang（aarch64-unknown-linux-ohos）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: 真机 shadow CI 验证通过（L0/L1/L4/L5 pass，L2 skip）

## 编译步骤

pforth 是两步引导（bootstrap）构建，conanfile.py 的 build() 分步执行：

1. `make pfdicapp CC=clang -j1` —— 编译 C 内核得到 `pforth`
2. OHOS 上对 `pforth` 做 ELF 签名（`binary-sign-tool sign -selfSign 1`），因为后续步骤要运行它
3. `make pforthapp CC=clang -j1` —— 运行 `pforth` 生成 `pforth.dic` 与 `pfdicdat.h`，再编译 `pforth_standalone`
4. OHOS 上对 `pforth_standalone` 做 ELF 签名
5. `make test` —— 运行 6 个上游 Forth 测试脚本

编译器从 Conan `tools.build:compiler_executables` conf 获取（R33），make 统一 `-j1`（R9）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap 构建需运行刚编译的 `pforth` 生成 dictionary | OHOS 内核拒绝执行未签名外来二进制（E077/E135） | 在 `make pforthapp` 之前先对 `pforth` 做 `binary-sign-tool --selfSign` 签名 |
| 2 | 本机（Windows）无 conan / make，无法本地跑通 conan create | 开发机为 Windows，工具链与真机 shadow CI 环境不同 | 本机完成配方静态检查与源码 SHA256 校验，构建/测试留给真机 shadow CI |
| 3 | 真机 `make test` 中 t_file.fth 的 RESIZE-FILE 收缩 4 个断言失败（90 passed, 4 failed） | `pf_fileio_stdio.c` 的 `TruncateFile` 用 `tmpfile()` 在 /tmp 建临时文件，而 OHOS `/tmp` 为只读（erofs，E002） | 打补丁 `0001-resize-file-use-ftruncate-on-posix.patch`：POSIX 平台（`__unix__`/`__APPLE__`/`__OHOS__`）改用 `ftruncate(2)` 原地截断 |

## 源码修改

- `patches/0001-resize-file-use-ftruncate-on-posix.patch`：修改 `csrc/stdio/pf_fileio_stdio.c`
  - 在 POSIX 平台（`__unix__`/`__APPLE__`/`__OHOS__`）引入 `unistd.h`，定义 `PF_HAVE_FTRUNCATE`
  - `TruncateFile` 增加 `ftruncate(fileno(File), Newsize)` 快速路径，`tmpfile()+freopen()` 作为回退
  - 原因：OHOS `/tmp` 只读（erofs），`tmpfile()` 无法创建临时文件，导致 RESIZE-FILE 收缩失败
  - 平台影响：仅 POSIX 平台走新路径；非 POSIX（嵌入式）保留原 `tmpfile()` 逻辑不变

其余源码为官方 pforth 2.0.1（tag v2.0.1），无 glibc 特有依赖。

## 依赖版本

- 无 conan 第三方依赖。
- 系统库：libm（`-lm`）、libc（musl）。Makefile 链接 `-lm`，CMake 路径会额外链接 `rt pthread`，本配方走 Makefile。

## 验证结果

真机 shadow CI（job `pforth-2.0.1-shadow-20260920-143514`，exit 0）：
- `conan create` 通过；L0（质量门禁）、L1（test_package 执行）、L4（补丁扫描）、L5（产物检查）全部 pass
- L2（--version/--help 冒烟）skip：pforth 无该参数（Forth 风格 `-i/-q/-d`），属正常非阻塞
- L1e 破坏性负测试通过：移走 bin/ 后 test 失败，证明 test_package 实质依赖被测包
- 上游 `make test` 6 个 Forth 测试全部通过：t_corex 124 / t_strings 58 / t_locals 9 / t_alloc 1 /
  t_floats 60 / t_file 94，合计 **346 passed, 0 failed**（`PForth Tests PASSED`）
- test_package 3 断言通过：`3 4 + . => 7`、`2 3 * . => 6`

本机前置验证（已完成）：
- 源码归档 SHA256 校验：`f4c417d7d1f2c187716263484bdc534d3224b6d159e049d00828a89fa5d6894d`
  （与 Debian `pforth_2.0.1.orig.tar.gz` 一致）
- conanfile.py / test_package Python 语法检查、manifest/conandata YAML 结构检查

## 注意事项

1. **bootstrap 签名顺序**：必须先签名 `pforth` 再跑 `make pforthapp`，否则 dictionary 生成阶段执行失败。
2. **t_file.fth RESIZE-FILE**：已通过补丁在 POSIX 平台改用 `ftruncate(2)` 修复（首跑暴露，二跑 94/0 通过）。
3. 产物为 3 个文件：`bin/pforth`、`bin/pforth.dic`（与 pforth 同目录，保证默认 dictionary 查找）、
   `bin/pforth_standalone`（独立可执行，test_package 用它做消费验证）。
4. 上游源码 `pf_guts.h` 内 `PFORTH_VERSION_NAME` 仍为 "2.0.0"（tag v2.0.1 未同步内部版本名），运行 banner
   显示 "PForth V2.0.0"，属上游既有行为，不影响功能。
5. 未提交 CI 生成的 reports/、ci-metadata.json 等产物。

---

**真机验证完成**: 2026-09-20
**最终状态**: shadow CI 通过（L0/L1/L4/L5 pass，L2 skip，上游 346/346，test_package 3/3）
