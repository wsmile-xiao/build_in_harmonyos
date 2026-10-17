# libgit2 1.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤（Conan 流程）

1. **下载源码**: 官方 GitHub archive v1.9.0 tarball
   `https://github.com/libgit2/libgit2/archive/refs/tags/v1.9.0.tar.gz`
   （sha256 75b27d4d6df44bd34e2f70663cfd998f5ec41e680e1e593238bbe517a84c7ed2，与独立下载核验一致）
2. **初始化**: `ohc-run.py init-build libgit2 1.9.0 --url=<官方 URL>`
3. **语言预检**: `ohc-run.py lang-preflight` → cpp 匹配（C 主体）
4. **Step2 探索性编译**: cmake + clang 构建 libgit2_tests/util_tests，ctest 运行（详见 reports/test-ledger.md）
5. **配方**: `ohc-run.py conan-init` 生成 conanfile.py + conandata.yml + test_package；修复
   file:// URL 为官方 HTTPS、移除执行端绝对路径、修正 cpp_info.libs（git2）
6. **验证**: `ohc-run.py conan-verify`（G0-G4/L2/L4/L5 全通过，conan create 干净构建成功）
7. **finish**: W2 结构 + R36 依赖 + W3 本地 CI 模拟（L0-L5 全 pass，JC_RESULT=pass）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create test 失败 `git_libgit2_init failed` | git_libgit2_init 成功返回初始化计数(>=1)，`!=0` 判断误判 | 改为 `<0` 判断 |
| 2 | `git_repository_init failed: ... is not owned by current user` | libgit2 1.9 属主安全校验（GIT_OPT_SET_OWNER_VALIDATION）与 HMDFS 共享属主 uid 冲突 | `git_libgit2_opts(GIT_OPT_SET_OWNER_VALIDATION, 0)`（知识草稿 DRAFT-libgit2-1.9.0-owner-validation-hmdfs） |
| 3 | `Asked for OpenSSL TLS backend, but it wasn't found` | CMakeDeps PREFER_CONFIG=ON 命中 conan config（小写 openssl_FOUND），上游检查大写 OPENSSL_FOUND | 配方关 PREFER_CONFIG + 注入 OPENSSL_ROOT_DIR/OPENSSL_INCLUDE_DIR 回退模块模式（知识草稿 DRAFT-libgit2-1.9.0-cmakedeps-uppercase-found） |
| 4 | W3 JC 拦截 origin/main 既有 cloog 基线 junk | 无 commit 时 junk_check full 模式扫描全部 tracked 文件 | 提交本库文件后进入 incremental 模式（只查本库 diff），基线文件原样保留（隔离自检 SHA 前后一致 e3b0c442） |

## 源码修改

无补丁，使用原始源码编译。

## 依赖版本（ohpcd 已发布，W0 核验）

- openssl/1.1.1w
- zlib/1.3.1

## 验证结果

```bash
# Step2 ctest（12 入口）：6 通过 / 3 失败（HMDFS 平台差异）/ 3 网络阻塞
# conan-verify：G0-G4 + L2/L4/L5 全通过（G2 conan create 干净构建成功）
# W3 本地 CI：L0-L5 全 pass（含 test_package 消费者测试 1/1 Passed、git2 --version OK）
```

### R02 上游测试全量复验（2026-09-19，任务 libgit2-1.9.0-r02-pc4-30）

复验日志目录：/storage/Users/currentUser/oh-logs/libgit2-1.9.0-r02-pc4-30/
复验 TMPDIR（0700 语义合格，stat 实测 drwx------ 700）：/data/storage/el2/base/cache

```bash
# 12 入口重跑（ctest -R '^<name>$'，TMPDIR=0700 合格目录）：8 通过 / 2 失败 / 2 超时
#  - invasive / online_customcert / gitdaemon / gitdaemon_namespace /
#    gitdaemon_sha256 / ssh / auth_clone_and_push / proxy（CA 注入 SSL_CERT_FILE=/etc/ssl/certs/cacert.pem）通过
#  - offline：135s 完整跑完（R01 462s 超时）；5 项失败隔离复测 3 项为级联污染（隔离即通过），
#    2 项 HMDFS 真失败（clone::local::hardlinks st_nlink、iterator::index::case_folding 大小写语义，E079/E193 覆盖）
#  - util：9 项 → 4 项（0700 TMPDIR 恢复 umask/chmod/owner-validation 5 项；剩硬链接/根目录 E079 族）
#  - online / auth_clone：外网间歇不可达（github 超时），子套件 badssl/fetchhead/remotes/shallow/httpproxy 等通过
# conan-verify：G0-G4 + L2/L4/L5 全通过（R01 报告，配方本轮零修改）
# W3 本地 CI：.ci-result.json exit_code=0 在档；消费者 test_libgit2 二进制实跑 exit 0
#    （libgit2 version 1.9.0 / git_repository_init OK / consumer test OK）
# 知识路径：两对草稿沿用（owner-validation-hmdfs、cmakedeps-uppercase-found）；
#   R02 新观察 N1 case_folding→E193、N2 hardlinks→E079 均 exact_duplicate，不建新草稿
```

### R03 上游测试全量复验（2026-09-20，任务 libgit2-1.9.0-r03-pc4-30）

复验日志目录：/storage/Users/currentUser/oh-logs/libgit2-1.9.0-r03-pc4-30/

```bash
# 12 入口重跑（0700 合格目录 /data/storage/el2/base/cache + HMDFS 语义）：9/12 入口级通过（R02 8/12）
#  - case_folding 转绿：HMDFS（大小写不敏感，本设备运行时语义）TMPDIR 下 exit 0
#    （Clar 沙箱按 TMPDIR 选目录，测试按 fs 大小写语义自适应选择期望排序）
#  - invasive / online_customcert / gitdaemon / gitdaemon_namespace / gitdaemon_sha256 /
#    ssh / auth_clone_and_push / proxy（CA 注入）通过
#  - offline：143.78s 完整跑完；3 项级联污染隔离复测全部通过（exit 0），
#    1 项真失败 clone::local::hardlinks（link() 全设备受限：HMDFS EPERM / el1·el2 EACCES，
#    136 挂载点全枚举无 link() 支持挂载点，E079 覆盖）
#  - util：4 项 HMDFS 平台差异（硬链接 EPERM ×3 + '/' 根目录访问 errno=13 沙箱拒绝，E079 族）
#  - online/auth_clone：双时间点网络核验一致可达（首次 T15:04:56Z / 最终 T15:19:51Z 均 github 200）；
#    online 子套件 badssl/fetchhead/remotes/shallow/httpproxy + clone 核心网络用例 12 项全部实跑通过；
#    auth_clone（cred）仅缺外部凭据 GITTEST_* 挂起（恢复条件=提供凭据）
# 门禁：conan-verify G0-G4/L2/L4/L5 全通过（R01 报告，配方三轮零修改）；W2 结构完整；
#   W3 .ci-result.json exit_code=0；消费者 test_libgit2 实跑 exit 0（R03 11-consumer-test.log）
# 知识路径：两对草稿继续沿用；R03 恢复项/残留项均 exact_duplicate（E193/E079）或无新知识价值，不建新草稿
```

### R04 函数级精确统计与最终复验（2026-09-20，任务 libgit2-1.9.0-r04-pc4-30）

复验日志目录：/storage/Users/currentUser/oh-logs/libgit2-1.9.0-r04-pc4-30/

```bash
# 函数级精确统计（Clar 字符流按函数名汇总，替代入口级/声明数混搭口径）：
#   source_declared_total=4097、function_level_passed_total=3343、failed=9、skip=113、not_run=632
#   函数级通过率 = 3343/4097 = 81.60%（配置可执行集合 3343/3465 = 96.48%）
#   统计规则与 SHA-256 见 12-function-level-stats.log
# 失败 9 项明细：clone::local::hardlinks 真失败 + 3 项级联（隔离复测通过）、case_folding（HMDFS 语义下已转绿）、
#   util copy/link ×3 硬链接 EPERM + dirent '/' errno=13（全设备 link() 不可用，R03 136 挂载点枚举 + R04 复测一致）
# 剩余项最终复验：hardlinks/util 4 项如实保留为函数级失败（恢复条件=POSIX 硬链接挂载点+沙箱放行）；
#   auth_clone（cred）缺 GITTEST_* 凭据 + github 不可达，如实保留
# 门禁：conan-verify G0-G4/L2/L4/L5 全通过（配方四轮零修改）；W2 结构完整；W3 .ci-result.json exit_code=0；
#   消费者 test_libgit2 实跑 exit 0（R04 13-consumer-test.log）
# 知识路径：两对草稿继续沿用；R04 无新增候选（函数级统计为方法修正，非新平台模式）
```

### R05 平台约束核验与 not_run 归类（2026-09-20，任务 libgit2-1.9.0-r05-pc4-30）

复验日志目录：/storage/Users/currentUser/oh-logs/libgit2-1.9.0-r05-pc4-30/

```bash
# 6 条 OH 平台约束逐条核验（见 test-ledger R5.1）：/tmp 重定向（erofs ro→0700 合格目录）、
#   软链接守卫（symlink OK，硬链接 EPERM/EACCES 无替代）、ELF 签名、SELinux chmod、clang 15.0.4、
#   无受限 syscall 依赖（'/' diriter 为沙箱路径限制 errno=13）
# not_run 归类（R04 632 → R05 599）：修复 Clar "(with ...)" 后缀套件行解析，3 个套件约 33 个函数
#   实为已运行并通过；真正未执行套件仅 online::fetch/perf::merge/stress::diff（上游 -x 明确排除，
#   CMakeLists.txt:36 generate.py -xonline -xstress -xperf），其余为框架 init/cleanup 与平台未实例化
# 函数级统计（修复后）：passed=3376、failed=9、skipped=113、not_run=599；
#   通过率 3376/4097 = 82.40%（R04 81.60%，+0.80pp 系解析修正）；配置可执行集合 3376/3498 = 96.51%
# 剩余 6 项：hardlinks ×4（link() 全设备不可用，如实保留，恢复=POSIX 硬链接挂载点）、
#   '/' dirent（沙箱路径限制，精确记录）、auth_clone（GITTEST_* 凭据未提供，恢复=凭据+外网）
# 门禁：conan-verify G0-G4/L2/L4/L5 全通过（配方五轮零修改）；W2 结构完整；W3 .ci-result.json exit_code=0；
#   消费者 test_libgit2 实跑 exit 0（R05 27-consumer-test.log）
# 知识路径：两对草稿继续沿用；R05 无新增候选（统计修正 + 既有平台约束确认）
```

## 交付物

- conanfile.py + conandata.yml（官方源 + 真实 sha256）
- test_package/（消费者真实 API 测试）
- commands.json（git2 CLI，R38）
- 知识草稿两对（DRAFT-libgit2-1.9.0-owner-validation-hmdfs / DRAFT-libgit2-1.9.0-cmakedeps-uppercase-found）

## 注意事项

1. 消费者（test_package / 上层应用）在 HMDFS 上须关闭 libgit2 属主校验
2. 配方中 OPENSSL 检测需回退模块模式（PREFER_CONFIG=OFF + OPENSSL_ROOT_DIR）
3. 上游网络类测试（online/auth_clone/proxy）在沙箱外网证书受限环境不可运行，非当前库缺陷
4. util 套件 9 项失败均为 HMDFS 平台差异（E046 chmod/E079 硬链接/E047 umask），不影响库交付

---

**编译结束**: 2026-09-18
**最终状态**: built