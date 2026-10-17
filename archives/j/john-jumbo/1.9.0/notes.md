# john-jumbo 1.9.0 — 鸿蒙 PC 适配 notes

> 平台任务卡指定包名 john-jumbo、版本 1.9.0，对应上游 **1.9.0-jumbo-1**（2019-05-14 发布）。
> 官方 main archives/j/john/1.9.0-jumbo-1 仅含 manifest/notes 与两条 README/CONTRIBUTING
> 装饰补丁（无 conanfile.py / test_package，从未进入 CI、从未发布制品仓），本 MR 按
> ARCHIVE-SPEC v2.0 补全适配（包名以平台任务卡口径为准）。

## 定位
- 上游：openwall/john 1.9.0-jumbo-1（GPL-2.0-or-later，Makefile.legacy 构建）
- 产物：john 主二进制（17 个 run/ 工具中 unshadow/zip2john 等 8 个为 argv[0] 别名，
  由 ln -s 生成——OHOS 禁 symlink，适配后以 cp 复制；conan 包仅导出 john 本体 +
  11 个 .conf/password.lst/14 个 .chr 增量模式字符集/rules/ 等运行时数据）
- 消费方：口令安全审计场景（--test 自检 / --wordlist 破解 / --show 展示）

## 关键适配点
1. **跳过 configure，直接 Makefile.legacy linux-arm64le**：config.guess 无法识别
   HarmonyOS 且 config.status 临时文件权限问题（官方 main john 旧适配笔记同款结论），
   linux-arm64le 是上游官方为不受支持系统提供的构建路径。
2. **-DJOHN_NO_SIMD**：NEON vroti_epi32 宏在 OHOS clang 下编译失败（官方 main 旧适配
   笔记实测结论），arm64le.h 有 `#if !JOHN_NO_SIMD` 纯 C 回退。
3. **symlink → cp（0001 补丁）**：OHOS 全盘禁 symlink()（EPERM）。linux-arm64le 目标
   用 `$(LN) arm64le.h arch.h`，且 PROJ 内含 8 个 `ln -s john ../run/X` 工具别名
   （unshadow/unafs/undrop/zip2john/gpg2john/rar2john/base64conv/unique），直接链接
   必中断构建；统一改 cp（john 按 argv[0] 分派，复制后语义不变）。其中 8 条
   `../run/<alias>` 规则位于 Makefile.legacy 全局区段（非 arm64le 目标专属，其它
   legacy 目标同样引用），影响面已随补丁在 conandata.yml patch_description 申报。
4. **0002 补丁 = linux-arm64le 目标三处上游缺口修复**（上游 arm64le 目标长期无 CI
   验证，三个缺口同源）：
   - 移除硬编码 -DHAVE_CRYPT/-lcrypt：OHOS musl 无 libcrypt（crypt(3) 位于 libxcrypt，
     设备不存在），保留必致链接失败；john 自带 DES 等自有实现，不依赖 libcrypt。
   - 目标开头 @echo 生成 john_build_rule.h：发行 tarball 不含该生成文件，arm64le
     目标既未定义 -DNO_JOHN_BLD 也不生成（x86 老目标有 -DNO_JOHN_BLD、arm32 目标有
     @echo 生成），而 john.c/listconf.c/options.c/opencl_common.c 非 NO_JOHN_BLD 路径
     无条件 include → 编译必挂；仿 arm32le 同款补生成。
   - 子 make `$(MAKE)` → `$(MAKE_ORIG)`（= `+$(MAKE) -f Makefile.legacy`，第 31 行）：
     全文件唯一不带 -f 的子 make，发行 tarball 不含 configure 生成的 Makefile，
     子 make 读不到 makefile → 对 .PHONY find_version 报 "No rule to make target"
     （真机实测，version.h 生成链断裂）。
5. **JOHN_CFLAGS/JOHN_LDFLAGS 扩展点注入 conan 依赖**：Makefile 默认值已含
   -DHAVE_LIBSSL/-lssl/-lcrypto/-lm/-lz，只需追加 openssl/zlib 的 include/lib 搜索
   路径；HAVE_LIBGMP/GMP_LDFLAGS/REXGEN_FLAGS/REXGEN_LDFLAGS 命令行置空压过
   Makefile 内反引号自动探测（设备无 gmp.h/librexgen，探测本身无害但需确定性构建）。
6. **-j8 并行**：真机进程配额有限（约 550），并行度过高会 fork EAGAIN（知识库记录）。
7. **运行时数据与二进制同目录打包**：1.9.0-jumbo-1 的 path.c 不读 JOHN 环境变量
   （该支持为后续 jumbo 版本引入），john_home_path = dirname(argv[0])，
   $JOHN/... 一律从二进制所在目录解析 → 全部 11 个 run/*.conf +
   password.lst/14 个 .chr/rules/ 与 john 同进 bin/（上游 run/ 布局即如此）。
   john.conf 的 .include 链引用全部 .conf（540 dynamic_disabled、1162
   korelogic、3929-3947 hybrid/dumb16/dumb32/repeats16/repeats32/dynamic/
   regex_alphabets；dynamic.conf 再引 dynamic_flat_sse_formats.conf），真机
   实测三轮依次暴露：放进 share/ → fopen bin/john.conf 失败；补 john.conf
   与 dynamic_disabled.conf → fopen bin/rules/best64.rule；补 rules/ →
   fopen bin/korelogic.conf。缺任一 .conf 配置加载即失败，故全部随二进制
   打包；relbench/mailer/makechr/genmkvpwd/benchmark-unify、108 个 *2john
   提取脚本、dns/ 进 share/john；ztex/opencl（19MB 固件/内核，与 OHOS
   无关）与 8 个 argv[0] 别名副本不打包。

## test_package（T1–T5，见 test.sh）
- T1：john 合法 aarch64 ELF（magic + e_machine，免 readelf）+ john.conf/password.lst
  + 11 个 .conf include 链 + rules/ 打包完整
- T2：--list=build-info 版本校验（Version: 1.9.0-jumbo-1 / Build: linux-arm64le
  目标行；1.9.0-jumbo-1 的 build-info 无 Arch/位宽行）
- T3：--list=formats 格式注册表规模校验（≥100；输出为逗号分隔清单而非每格式
  一行，按逗号计名，真机实测 259 个）
- T4：--test 自检 7 格式（基础 5：Raw-MD5/md5crypt/sha256crypt/sha512crypt/NT；
  依赖路径 2：PKZIP→zlib、openssl-enc→OpenSSL "enc" AES-128/MD5，libcrypto——
  openssl/zlib 制品仓包为纯静态库、静态链入，此两例使依赖功能路径有真实覆盖）。
  校验无 "Self test failed" 且逐格式 Benchmarking 行存在；--format 仅收单个
  格式名（FLG_FORMAT 无 OPT_FMT_ADD_LIST，逗号列表报 "Unknown ciphertext
  format name requested"，真机实测）→ 逐格式循环自检；每格式 1 条具名 PASS，
  无汇总 PASS 行（计数口径=具名用例数）
- T5：5 组哈希 E2E 破解闭环（向量由 PC 端 openssl 3.5.5 生成；NT = MD4(UTF-16LE)，
  经 RFC 1320 全部公开向量校验），--wordlist 破解后校验 pot 文件含明文
- 交叉编译环境（CI worker）产物不可执行 → 执行类用例按 SKIP 计（仅 T1 ELF 校验真实）；
  真机"能执行但失败"是硬 FAIL
- 测试用例数：真机全绿 19 条 / SKIP 0 条（T1×4+T2×2+T3×1+T4×7+T5×5，计数口径=
  具名用例，见 reports/conan-create.log 实测）
- 执行器结构：逐例独立 TEST PASS/FAIL + 末行 TEST SUMMARY: N passed, M failed，
  任一失败 exit(1)（输出无 "assertions passed" 字样）

## 上游测试（R51 三步）
- 上游正式测试套件 = `src/Makefile.legacy` 的 `test:` 目标 → `cd ../test && perl
  jtrts.pl -q`（John Test Suite，perl 驱动）。发行 tarball 不含 test/（jtrts 为
  独立仓库；git tag 1.9.0-Jumbo-1 递归计数同样无 test/ 目录，`src/tests/` 共 24
  个文件 = unit-tests.c + NESSIE 11 + NIST_CAVS 12 向量数据），且 OHOS 设备无
  perl → 平台受限（RESTRICTED），无法执行。
- 上游随 tarball 分发的 `unit-tests:` 目标（tests/unit-tests.c + misc/common/
  memory/sha2，纯 C）**真机全量执行通过**：37 测试函数 / 43,067,484 次检查 /
  退出码 0（reports/upstream-test-run.md）。三处环境适配不涉测试逻辑：CPATH
  注入 openssl include（目标硬编码 CFLAGS 而 sha2.h 含 opensslv.h）、/tmp 临时
  文件 sed 重定向 cwd（OHOS /tmp 只读，E002）、cwd=src 供 NIST_CAVS 相对数据
  路径（缺数据时上游直接崩溃，无防护——上游 Linux 假设）。三处适配已固化为
  复现脚本 reports/run-upstream-tests.sh（真机实测，幂等，测试逻辑零改动）。
- test_package 的 T4 以 --test 内置自检向量（NESSIE/NIST_CAVS 编译进二进制，
  上游相同向量机制）承接 jtrts 无法覆盖的部分；另有 5 组 E2E 破解（T5）与
  --show 取证（reports/manual-runtime-evidence.md）。

## 遇到的问题与解决方案
- configure 不可用（config.guess 不识别 HarmonyOS + config.status 临时文件权限）
  → Makefile.legacy linux-arm64le（官方 main 旧适配笔记同款结论）
- NEON vroti_epi32 宏 OHOS clang 编译失败 → -DJOHN_NO_SIMD（官方 main 旧适配笔记结论）
- OHOS 禁 symlink → 9 处 ln -s 改 cp（0001）；musl 无 libcrypt → 移除 crypt 标志（0002）
- john_build_rule.h 缺失 + 子 make 无 makefile（find_version 报错）→ 0002 补生成 +
  $(MAKE_ORIG)（详见「关键适配点 4」，两处均为上游 arm64le 目标真实缺口）
- 发行 tarball 与 git tag 树唯一字节差异 = JTR_ARCHIVE_VERSION_STRING 占位符替换为
  -a16c8a7625 2019-05-14（1:1 换行）；补丁必须基于 tarball 解包字节生成，且 Windows
  下须以 LF 写出（text 模式 CRLF 补丁打在 LF 源文件上 context 失配，pit #45）
- 真机镜像下载：设备直连 openwall ~5KB/s（33.6MB ≈ 2h）→ 验证期设备侧 conandata
  首条 URL 临时指向 PC 端 python http.server（同热点 LAN，秒级完成且 sha256 校验
  通过）；仓库侧 conandata 保持官方双 URL（openwall 主站 + download.openwall.net
  镜像，两者 sha256 f5d123f8… 逐字节一致）
- openssl/zlib 依赖走制品仓已有版本（openssl/1.1.1w、zlib/1.3.1.1），Makefile
  默认已链 -lssl/-lcrypto/-lz，配方只经 JOHN_CFLAGS/JOHN_LDFLAGS 注入搜索路径
- 打包布局三轮 fopen 实测（share/ 缺 john.conf → 缺 rules/best64.rule → 缺
  korelogic.conf）：john.conf 的 .include 链引用全部 11 个 run/*.conf，结论 =
  全部 .conf + rules/ 整目录随二进制进 bin/（见「关键适配点 7」）
