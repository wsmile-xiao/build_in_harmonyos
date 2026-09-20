# libmodi 0-20251121 适配笔记（鸿蒙 PC / OHOS）

任务：为 OpenHarmony PC（aarch64）新增 libmodi 0-20251121 Conan 包。
分支：feat/libmodi-0-20251121；上游基线：build_in_harmonyos upstream/main
7a34c9f8e。这是**全新包**（archives/l/libmodi 在 upstream/main 不存在，
task_init.sh 以 --allow-unpublished 放行）。

## 软件身份（防望文生义）

libmodi（libyal）是 **Mac OS 磁盘镜像格式访问库**，支持 sparse bundle disk image、
sparse disk image、UDIF（uncompressed / ADC / bzip2 / LZFSE/LZVN / LZMA /
zlib-DEFLATE 压缩；不支持加密镜像、Disk Copy、NDIF、多段 UDIF）。与名字容易
联想的 Microsoft Office Document Imaging (.mdi) **无关**。README 自述
`Status: experimental`——这直接决定了 release 资产命名（见下）。

## 源码溯源

- 上游 tag `20251121` 存在（`git ls-remote --tags https://github.com/libyal/libmodi`，
  e7fb86b1…），但 release 资产 `libmodi-20251121.tar.gz`、`libmodi-alpha-20251121.tar.gz`
  及 `.tar.xz` 变体实测全部 **404**（curl -I -L）。
- 实际资产：**`libmodi-experimental-20251121.tar.gz`**（HTTP 200，2,029,302 字节），
  URL：`https://github.com/libyal/libmodi/releases/download/20251121/libmodi-experimental-20251121.tar.gz`
- sha256（设备现场计算）：`b3c6783c908480711957d9e0e14227c90821be9e90c10f6abe7af1f86ed4bccb`
- 闭包核对：tar 顶层目录 `libmodi-20251121`，1001 个条目；gzip magic 正常；
  `configure` 已随发布包预生成（无需 autoreconf，规避了 harmonybrew automake
  假绿面与 CI worker 缺 automake 的差异）。
- 下载于 2026-09-20，任务私有目录（非 /tmp）；GitHub API 域名在本设备解析受限，
  资产探测用 curl / git 协议完成。

## 依赖结论（W0）

**零外部 Conan 依赖**：19 个 libyal 组件以 standalone 形式内嵌在发布包顶层目录
（libbfio、libcaes、libcdata、libcdirectory、libcerror、libcfile、libclocale、
libcnotify、libcpath、libcsplit、libcthreads、libfcache、libfdata、libfguid、
libfmos、libfplist、libfvalue、libhmac、libuna），configure 的
`--with-libbfio`（默认 auto-detect）在无系统 libbfio 的环境自动回落内嵌副本，
设备与 CI 同为该形态。压缩实现（bzip2/deflate/LZMA/LZFSE/ADC）均为库内自带，
不引入外部 zlib/bzip2。因此 W0 无需依赖 binary 安装验证，无拓扑序前置。

## 平台适配（全部内联在 conanfile.py build()，无 patches/ 文件）

1. **E011（HMDFS umask）**：随包 configure 含 2 处 `umask 077`，在 HMDFS 上
   建出的 0700 临时目录连创建者都不可写。OHOS 构建期把这两处替换为 `umask 022`
   （只在 Conan 缓存副本上改，随包内容不变），并全程保持 umask 022。
2. **三元组**：随包 config.sub 原生接受 `linux-ohos`；OHOS 下显式传
   `--build/--host=aarch64-unknown-linux-ohos`（update_configure_args 覆盖语义，
   避免与 AutotoolsToolchain 生成的重复），libtool 正常走共享库 PIC 分支。
3. **CONFIG_SHELL**：HMDFS 上直接执行源码树脚本受限，OHOS 下用 profile
   [buildenv] 注入的 bash（`/data/service/hnp/bin/bash`）显式启动 configure；
   make check 经 `LOG_COMPILER` 指定同一解释器（上游 3 个 TESTS 入口都是 bash
   脚本；设备无 /bin/bash shebang，toybox sh 不执行 bashisms）。
4. **并发**：`tools.build:jobs` 缺省取 os.cpu_count()（本机 20，容器 affinity 8），
   配方内固定 jobs=2，调用方可显式覆盖。
5. 交付选项：`--disable-python`（不构建 pymodi 绑定，同时关闭 TESTS_PYMODI 测试段）、
   `--with-libfuse=no`（modimount 保留但走无 fuse 降级分支）、
   `--enable-static-executables=no`。

## R6 声明（不改上游文件）

未修改任何随包源文件、构建脚本或测试脚本入库。唯一的内容改写发生在 **OHOS
构建期的 Conan 缓存副本**上：configure 内 2 处 `umask 077` → `022`（HMDFS 必需，
见上）。conandata.yml 无 patches 段。

## R8 声明（无平台条件编译）

无 `__OHOS__` 等平台宏补丁、无空 stub、无固定成功返回。唯一的平台分支是配方层
的 `settings.os == "OHOS"`（构建方式选择，非源码改动）。

## 上游测试（真实计数）

- 口径：automake 两注册面 TESTS + check_PROGRAMS = **24**（3 个 shell 入口 +
  21 个 C 测试程序）；`tests/modi_test_*.c` 文件数 24 含 3 个 helper（非注册
  程序），不作为 N。
- 结果（2026-09-20 采信轮 conan-create.log，干净轮 run_make=9/calling_build=2）：
  **TOTAL 24 = PASS 23 + FAIL 0 + SKIP 1 + NOT_RUN 0**，通过率 23/24（95.8%）。
  - TESTS：PASS 2（test_library.sh、test_tools.sh）+ SKIP 1（test_modiinfo.sh）。
  - check_PROGRAMS：21/21 PASS，程序级证据在构建树 tests/test_library.sh.log
    （18 行）与 tests/test_tools.sh.log（3 行）的 `Testing: <program> (PASS)`。
- SKIP 归因：test_modiinfo.sh 依赖 `tests/input/` 夹具，上游发布 tarball 不含该
  目录（脚本原文 `Test input directory not found.` → `exit 77`，上游规则）。
  替代验证：工具单元测试 3 项 PASS；安装后 `bin/modiinfo -V` 真实输出
  `modiinfo 20251121`；test_package koly 合成夹具走通真实库调用链。
- 下界核对：上游 GitHub HEAD（8da3171）= check_AUTOTESTS 3 + check_PROGRAMS 21
  = 24，与声明 N 相等，无差额（HEAD 已从 shell TESTS 迁移到 autotest 套件，
  注册数同构）。

## test_package（鸿蒙特有，不计入上游分母）

- `test_libmodi.c`（11 项通用断言）：版本串（上游 20251121，非 Conan 版本）、
  访问标志位、codepage 设置/回环（ASCII=20127）、check_file_signature 三路径
  （NULL→-1、缺失→-1、无签名→0）、handle_open 错误路径。
- `test_ohos.c`（11 项鸿蒙专项断言）：`__OHOS__` 编译目标、TMPDIR 语义
  （已设置/非 /tmp/存在/可写）、在 TMPDIR 下合成 **512 字节 UDIF koly 尾块**
  并走完整真实链路：签名判定==1 → handle_initialize → open==1（UDIF 惰性
  解析）→ get_media_size==1 且 size==0 → close==0 → free==1。
- 公开 API 契约注意：2025+ libyal 的 error 类型是 `libmodi_error_t`
  （include/libmodi/error.h `typedef intptr_t`），内嵌 libcerror 类型不在安装面；
  getter 集是 get_media_size/get_image_type/get_offset（无 get_image_size）。
- 另有安装后 CLI 加载检查 `bin/modiinfo -V`（运行检查，不计断言）。
- 结果：22/22 断言全 PASS（conan-create.log:2047-2071 逐行可数）。

## 门禁补测（conan-verify 报告 L2/L4/L5 打「跳过」，按 SKIPPED 人工补测）

见 `reports/conan-verify-supplement.md`：G4 实物清单与 package_info() 互证；
L2 真跑（modiinfo -V / modimount 用法路径）；L4 消费者二进制与 modiinfo 的
DYN+PIE+GNU_STACK RW+GNU_RELRO+BIND_NOW 判据、库本体 DYN+RELRO+STACK；
L5 两条稳定聚合与逐产物 sha256 基线。G0 命中 E490（helper 可执行位）经实测
不成立（configure 显式解释器启动 + tar 模式保留 + G2 设备端到端通过）。

## 遗留边界

- modimount 在无 libfuse 环境是降级分支（可执行、可打印用法，不提供挂载），
  与上游 `--with-libfuse=no` 配置语义一致。
- pymodi（Python 绑定）未交付（--disable-python），不改变 C 库交付面。
- 上游 `Status: experimental`；发布包不带 tests/input/（见 SKIP 归因）。
- lang-preflight 的 mixed→env_unsupported 为假阳性，复核留证见
  `reports/lang-preflight-review.md`（与上游池既有条目
  DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect 同族形态）。

## 知识沉淀（路径 B）

新草稿：`knowledge/drafts/DRAFT-E594-libyal-2025-experimental-asset-error-type-koly-fixture`
（.md + .kv；复现脚本 `$HOME/tmp/libmodi-0-20251121/repro-e584.sh`）。lang-preflight
假阳性判据与上游池既有条目
DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect 同族；配方行为
引用既有正式条目 E007/E011（knowledge/graph/）；本条三处事实（资产命名、公开
error 类型契约、koly 合成夹具）为独立增量，与上述条目互不重叠。
---

**编译结束**: 2026-09-20 11:14
**最终状态**: built
