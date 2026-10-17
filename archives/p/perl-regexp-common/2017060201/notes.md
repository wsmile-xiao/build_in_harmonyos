# perl-regexp-common 2017060201 适配笔记

## 基本信息

- CPAN 发行版: `Regexp-Common` (Regexp::Common), 作者 Abigail
- 上游版本: 2017060201（与 Conan 包版本一致，未递增）
- 源码: https://www.cpan.org/modules/by-authors/id/A/AB/ABIGAIL/Regexp-Common-2017060201.tar.gz
- SHA256: `ee07853aee06f310e040b6bf1a0199a18d81896d3219b9b35c9630d0eb69089b`
- 许可证: Makefile.PL 声明 `mit`；发行版捆绑的 pattern 材料含 BSD/Artistic 声明（已打包 `licenses/`）
- 纯 Perl 模块，无 XS/C 代码；最低 Perl 5.10
- issue: 待补（任务下发时未提供 issue 编号）

注意: 本库已存在更高版本 `perl-regexp-common/2024080801`（published）。本 2017060201
为并行的旧版本包，目录、配方与分支相互独立，不影响 2024080801。

## W0 依赖结论

- 运行时依赖: 无 CPAN 模块依赖，仅 Perl 核心（vars/strict/warnings/Config）
- 构建依赖: ExtUtils::MakeMaker（Perl 核心）、perl 解释器、make
- 测试依赖: Test::More（Perl 核心）；META 推荐的 Test::Regexp 无任何 .t 文件使用
- 缺失依赖: 无，不需要拆分依赖适配

- 语言预检 lang-preflight: task=cpp, detected=perl, env_unsupported —— 按知识库
  （DRAFT-cl-unicode-lisp-lang-hold-verification）该结果为非失败路径，纯 Perl 库
  detected=perl 属正确检测；同库 2024080801 已 published 佐证。

## 配方要点

1. **不用 conandata.yml**，源码 URL/SHA256 直接内嵌 `conanfile.py` 的 `source()`。
   原因: 避免 CI pre-download 对 conandata.yml 处理路径上的
   `BUILD_DIR: parameter not set` 基础设施缺陷（xmodem 适配已验证的规避方式）。
2. 构建方式与同库已发布的 2024080801 配方一致:
   `perl Makefile.PL INSTALLDIRS=site` → `make -j1` → `make install DESTDIR=staging`
   → glob 复制 `.pm` 到 `lib/perl5/site_perl/...`（G4 兼容布局）。
3. `package_info()` 用 glob 动态发现 `site_perl/<版本>` 路径并设置 `PERL5LIB`
   （runenv + buildenv），不硬编码 Perl 版本。
4. 额外打包上游 `t/`（73 个 .t）、`META.json`/`META.yml` 到
   `share/perl-regexp-common/`，供 test_package 在消费侧执行完整上游 TAP 套件；
   许可证文件打包到 `licenses/`。
5. perl 发现策略: `shutil.which("perl") or "/data/service/hnp/bin/perl"` ——
   鸿蒙 PC 设备 runner 默认 PATH 不含 hnp perl（与 perl-cgi 配方的处理一致）。

## test_package 设计

- Test A（Python, 38 断言）: 打包清单静态验证 —— 18 个核心/子模块文件、
  版本标记 2017060201、许可证、完整 t/ 清单（14 顶层 + 7 子目录共 73 个 .t）、
  META.json 运行时/测试依赖。
- Test B/C（perl subprocess）: 安装后模块加载、版本断言、10 个子模块加载。
- Test D（perl TAP, 15 断言）: `test_regexp_common.pl` 功能验证
  （balanced/real/int/hex/list/delimited/URI/zip/IPv4 及负例）。
- Test E: 完整上游 TAP 套件 —— 73 个 .t（全部只用核心 Test::More），
  将打包的 lib + t/ 复制到可写目录后用 Test::Harness `runtests` 执行。

## 本机（Windows 构建机）验证结果

本机无 Perl 解释器（`perl` 不存在），perl Conan 包仅支持 Linux/OHOS 目标，
因此无法在本机执行上游测试与 test_package。已执行并全部通过:

- `python -m py_compile`: conanfile.py、test_package 两个脚本语法检查
- YAML 解析: manifest.yaml、test_package/MANIFEST.yml
- `conan export`: 配方导出成功（字段一致性、conanfile 语法由 Conan 校验）
- `conan source`: 源码下载、SHA256 校验、解压全部成功
- 静态打包清单断言: 用真实源码树模拟包布局实际运行 `test_perl_regexp_common.py`，
  38 项断言全部通过
- L1e 破坏性自测: 删除包内 Common.pm 并篡改版本后重跑，test 失败（exit=1），
  确认 test 真实依赖包产物
- `git diff --check`、目录边界检查（改动仅 `archives/p/perl-regexp-common/2017060201/`）

## 真机 shadow CI 结果（HarmonyOS PC, aarch64, perl 5.42.0）

隔离 job: `perl-regexp-common-2017060201-20261004`，入口
`run-conan-heavy.sh`（heavy 模式，设备全局锁排队）。

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir        (纯 Perl 库正常)
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
KC_RESULT=pass: no_graph
JC_RESULT=pass: empty
exit code: 0
```

- 上游 TAP 套件: `Files=73, Tests=149252, 17 wallclock secs, Result: PASS`（73/73）
- test_package Test A: 38/38 断言通过
- test_package Test B/C: 模块加载 + 版本 2017060201 + 10 子模块 OK
- test_package Test D: 功能 TAP 15/15 断言通过
- test_package Test E: 即上方上游套件（消费侧执行）

### 迭代记录

| 轮次 | 报错原文 | 根因 | 解法 |
|---|---|---|---|
| r1 | `'a,,c' matches $RE{list}`；`Can't create unknown regex: $RE{zip}{American}` | 功能脚本断言与 2017060201 模式语义不符（list 默认允许空元素；US 邮编注册名是 `{US}`） | 删 list 负例断言；`{American}`→`{US}` |
| r2 | `Can't Regexp::Common::EXISTS` | `%RE` 为 tied hash，perl 5.42 下 EXISTS 方法未实现，`exists $RE{...}` 不可用 | 改为 `ok(eval { $RE{...}{...}; 1 }, ...)` 可用性检查 |
| r3 | — | — | 全绿（见上） |

## 注意事项

- **不要对工作区配方路径直接跑 `conan source`**: 直接 `conan source <工作区路径>`
  会把源码解压进配方目录（basic_layout 的 source_folder 即配方基目录），污染
  Git 工作区。CI 的 `conan create` 先 export 到缓存再在缓存内构建，不受影响。
  本机验证时如需解压验证，应复制配方到临时目录执行，或验证后立即清理。
- 设备共享存储 inode 紧张: 隔离 job 复制大仓库会报 `No space left on device`
  而 `df -h` 仍有余量（HMDFS inode 配额，见 DRAFT-nift-3.0.3-shadow-ci-inode-isolation）。
  本轮在清理本任务此前残留的半成品 job 后，标准 prepare 流程成功。
- 设备端无 git: `build_and_test.sh:164 permission denied: git`（分支名检查降级，
  非阻塞；L0 其余检查全部通过）。
- 已知环境差异风险: Conan 多 PERL5LIB 路径下 2024080801 曾出现 URI 子模式
  非致命 warning；本配方 test_package 的 PERL5LIB 只含本包 site_perl 路径，
  实测未触发。
