# xa 2.4.1 适配笔记

## 编译环境
- 构建系统: makefile（上游为纯 POSIX Makefile + `src/`、`misc/` 子目录，无 configure/autotools）
- 编译日期: 2026-09-18
- 编译器: clang 15（来自 conan profile `tools.build:compiler_executables.c`；设备上为 Harmonybrew OHOS SDK clang，目标 aarch64-linux-ohos）
- 状态: built（conan-verify G0–G4 全绿；上游 44/44 + test_package 12/12）

## 编译步骤
```bash
# 探索编译（模式 B）
cd $BUILD_SRC_DIR
make -j1 CC=<ohos-clang> LD=<ohos-clang>      # 产出 xa + uncpk + misc 五个工具

# 上游回归（Perl 驱动，44 例）
perl tests/harness -tests=ALL -cc=<ohos-clang> -cflags="-O2 -g" -make=make
# → 44/44 PASS（hextool 逐字节比对）

# Conan 配方验证
python3 scripts/ohc-run.py conan-verify xa 2.4.1 --profile ohos-aarch64-device
# 内部 conan create 真实执行：
#   build(): make -j1 CC=<conf> LD=<conf> + 上游 44 例回归（标记校验，失败即中止）
#   test_package: sh test_xa.sh → 12/12 断言通过（真实执行六个已安装二进制）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tests/harness` / `tests/hextool` 无法执行：`bad interpreter: /usr/bin/perl: no such file` | OHOS 无 `/usr/bin/perl`（perl 由 Harmonybrew 提供在 PATH）；直接改 `#!/usr/bin/env perl -s` 也不行——内核对 env 只传单个参数 `perl -s`，toybox env 无法拆分 | 补丁 0001/0002：shebang 改 `#!/usr/bin/env perl`，并在脚本内复刻 Perl `-s` 开关解析（`-name=value` / `-name`）后清理 @ARGV；测试命令与断言零改动（E037/E049 同类） |
| 2 | GitHub `github.com/.../archive/...` 从设备/构建网超时（Amax 同样超时），init-build 首次下载失败 | 构建网对 github.com 直连不稳定/不可达；canonical 归档实际由 codeload 提供 | conandata.yml 保持官方 github.com URL（R39/PF7）；本地下载经 ghfast 镜像、验证阶段由 conan_verify 自动注入 ghfast（E017 预防），并用 codeload 归档做 sha256 二次核验（字节一致：`8fecdb…eb67e`） |
| 3 | 上游 tag 归档为 `README + xa/` 两级布局，make/补丁在错误的根目录执行 | GitHub 归档保留了仓库结构（项目在 xa/ 子目录） | conanfile.py `source()` 将 `xa/` 内容提升到 source 根并移除仓库级 README；manifest 标注 build_system=makefile |
| 4 | `make install` 报 `install: inaccessible or not found` | 上游 install 目标依赖 `install(1)`，OHOS/toybox 无此命令 | `package()` 直接 copy 6 个二进制到 `bin/`、6 份 man 到 `share/man/man1`，并 chmod 0755 |
| 5 | init-build 将纯 Makefile 工程探测为 autotools，conan-init 模板不可用 | 探测启发式偏差（无 configure，但存在 Makefile 链） | 按 `templates/conanfile-makefile.py.tmpl` 与既有 CLI 包先例手写配方；build_system 记为 makefile |
| 6 | CI L2 以 `--version`/`--help` 探测 bin/ 工具 | 本包六个工具均支持 `--version`（xa 为 `xa (xa65) 2.4.1`），L2 可通过 | test_package 断言 `--version` 行为；无需特殊处理 |

## 源码修改

仅 2 个测试脚本的可移植性补丁（平台适配，无平台宏，不改变任何测试语义）：

- `patches/0001-tests-harness.patch`
  - **修改文件**: `tests/harness`
  - **修改原因**: 上游 shebang `#!/usr/bin/perl -s` 在 OHOS 不可执行（无 `/usr/bin/perl`；`env` 形式无法携带 `-s`）
  - **修改内容**: shebang 改 `#!/usr/bin/env perl`；脚本开头加入等价于 `-s` 的开关解析（`-tests=/-cc=/-cflags=/-make=/-makeflags=`），并清理 @ARGV；其余逻辑逐字保留
- `patches/0002-tests-hextool.patch`
  - **修改文件**: `tests/hextool`
  - **修改原因**: 同上（各 test Makefile 以 `../hextool -cmp=...` 直接调用）
  - **修改内容**: 同上（`-cmp=` / `-output` / `-noutput` 解析）；比较仍为逐字节 hex 比对

未修改 `src/`、`misc/`、`Makefile`、`tests/*/` 的正式源码与用例；补丁新增行不含 `__OHOS__` 等平台宏，未注入系统前缀（PF5/PF6 合规）。

## 依赖版本

无第三方依赖（W0：纯 ANSI C + 系统 libc；`requirements()` 为空）。构建期宿主工具：`make`、`perl`（上游测试驱动）、`clang 15`（工具链由 Conan profile 提供）。

## 验证结果

```text
# 上游测试（tests/harness -tests=ALL）：44/44 PASS
matching tests: adrm,align,alxl,aserr,binclude,branch,ca65,chardelimiter,charset,chppch,cll,comcom,cpktest,cpp,csapiec,dos51,expando,fordef,incerr,ldoreloc,line,linkr,listing,masmcom,math,mode,mvnmvp,neg_offset,nonl,op816,openpp,pparity,ppdefines,ppstrings,quotch,recmac,recucom,relmode,relocmode,relocundef,reset_segment,stringcom,undef,usb65
## ALL SELECTED TESTS PASS (ALL, n=44) ##

# test_package 功能测试（sh test_xa.sh）：12/12 PASS（详见 reports/test-report.md）
# conan-verify G0–G4 / L2 / L4 / L5：PASS（conan create 干净复现）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/xa | 交叉汇编器（arm64 ELF） |
| bin/file65 / bin/ldo65 / bin/reloc65 | o65 信息 / 链接 / 重定位工具 |
| bin/uncpk / bin/printcbm | C64 cpk 归档 / CBM BASIC 列表工具 |
| share/man/man1/*.1 | xa/file65/ldo65/reloc65/uncpk/printcbm 共 6 份 man 手册 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/x/xa/commands.json` 声明（R38）。
- 上游测试驱动依赖 `perl` 在 PATH：设备（Harmonybrew）与 CI worker（GNU userland）均具备；配方在缺失 perl 时选择硬失败而非跳过上游测试。
- `printcbm` 上游已标记弃用（2.4 起），保留打包以与上游 `make install` 对齐；功能测试覆盖其 BASIC 列表输出。
- `xa -o -` 可输出到 stdout；`-l`/`-P` 列表功能也已覆盖（标签表）。
- 首次执行新二进制时设备可能弹安全确认框（R7）；本任务的设备验证已在解锁状态下完成。
---

**编译结束**: 2026-09-18 13:17
**最终状态**: built
