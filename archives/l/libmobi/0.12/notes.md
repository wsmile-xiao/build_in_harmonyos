# libmobi 0.12 适配笔记

## 元信息

- 上游：bfabiszewski/libmobi（GitHub），tag `v0.12`，tarball URL
  `https://github.com/bfabiszewski/libmobi/archive/refs/tags/v0.12.tar.gz`
- SHA256：`78826d161c02ce93ff1cd62838b4d749df754f52185474b82e4093badf4689c1`
- License：LGPL-3.0-or-later（仓库根 COPYING 为 LGPLv3 全文，README 声明 or later）
- 构建系统：autotools。GitHub tag tarball 仅含 configure.ac + autogen.sh，
  无 configure；配方内先 `autoreconf --force --install -I m4` 引导
  （与上游 autogen.sh 等效，参照 abiword-plugin-clarisworks 先例）。
  config.guess 识别设备为 aarch64-unknown-linux-ohos，无需 E007 补丁。
- 产物（已核验）：`lib/libmobi.so{,.0,.0.0.0}`（仅共享库，无 .a）、
  `include/mobi.h`、`lib/pkgconfig/libmobi.pc`、
  `bin/mobitool|mobimeta|mobidrm`（3 个 CLI，ELF64 AArch64 PIE）、man1 页。

## 配置决策

- `--with-zlib=no --with-libxml2=no`：使用内置 miniz 与内置 xmlwriter。
  设备（HarmonyOS PC AArch64）上没有 zlib/libxml2 开发头文件，且上游 CI
  实测覆盖该组合；Conan 依赖为零，最稳。
- 共享库默认开启；静态构建走 `--enable-static --disable-shared`。

## 上游测试（已真实执行）

- 命令：`make check`（tests/Makefile.am → tests/test.sh.in，bash 驱动）
- 样本：12 个 `tests/samples/*.mobi`，16 对 md5 基线（samples_md5.txt）
- **陷阱 1**：configure 探测 md5 程序后拼 `-t` 参数（GNU md5sum 风格），
  设备是 toybox md5sum（无 `-t`）→ 首跑全部 SKIP。解法：`MD5PROG=md5sum`
  环境变量覆盖（configure.ac 的 `AC_ARG_VAR`），不再拼 `-t`。
- **陷阱 2**：test.sh 依赖真 bash（`${BASH_PATH-...}` 探测），设备 bash 位于
  `bash（通过 PATH 动态发现）`。
- 结果：**11 PASS + 1 XFAIL**（sample-invalid-indx.fail，上游已知失败，
  exit status 1）+ 0 SKIP。

## test_package 设计

- fixture 程序化生成：构造最小合法 KF7 MOBI（PDB 头 + record0 三层头 +
  EXTH title/author + record1 无压缩文本），不提交任何二进制样本文件。
- 字段布局依据：上游 `src/util.h` 长度宏 + `src/read.c` 解析顺序（见
  test.c 头部注释）。
- 正向：load → EXTH title/author → fullname → fileversion/is_mobipocket →
  mobi_get_rawml 文本解压逐字节比对 → record1 数据比对 → 越界 seqnumber NULL。
- 负向：10 类坏输入断言具体返回码（MOBI_FILE_NOT_FOUND / MOBI_DATA_CORRUPT /
  MOBI_FILE_UNSUPPORTED / MOBI_PARAM_ERR），非仅“不崩溃”。
  第 9 项（EXTH 越界长度）上游容忍 exth 解析失败继续 load，断言为
  “load 成功则 title 必为 NULL（元数据缺失）”或 DATA_CORRUPT。
- 资源释放：每个分支 mobi_free 收尾。

## 格式考证（fixture 构造依据，源码 + ground truth 双重验证）

- 字节序：libmobi 全大端读取（mobi_buffer_get32 = data[0]<<24 | …），
  fixture 所有多字节字段须大端写入；首版小端写入曾致 outb.len 越界污染。
- PDB 头 78 字节（PALMDB_HEADER_LEN）：name32 + attr2 + ver2 + 9×4 + count2；
  记录表起于 78，每项 offset(4) + attr(1) + uid(3)。
- MOBI 头 header_length 语义：自 magic 起算、含 8 字节 magic+length 自身；
  mobi_parse_mobiheader 进入时 offset=24，将 buf->maxlen 截断为
  `header_length + offset - 8`。header_length=0xe4(228) 时截断点 =
  record0+244 → **EXTH 必须紧随 record0+244**，错位即被 sanity 丢弃
  （Debug 版 libmobi 实测确证）。
- MOBI 头索引类字段共 10 个（非 12），字段读取终止于 record0+280；
  full_name_offset 是 record0 内偏移（非文件偏移）。
- EXTH：tag 99=EXTH_TITLE、100=EXTH_AUTHOR；mobi_meta_get_title 先查
  EXTH_UPDATEDTITLE(503) 再 fallback fullname，author 走纯 EXTH tag 100。
- 坏 MOBI magic：mobi_parse_record0 吞掉 mobi_parse_mobiheader 的错误返回，
  且 mobi_is_mobipocket 只查 PDB type/creator → load 仍成功但 `m->mh == NULL`，
  负向断言按此语义写（不能断言 load 失败）。
- ground truth：`samples/sample-ncx.mobi`（28999B，type=BOOK creator=MOBI，
  rec_count=26，rec[0] offset=288 size=8744，compression=2，text_length=1032），
  与 mobitool dump（"Title: libmobi ncx test"）交叉验证。

## 其他

- `make -j1`：上游 tools 编译在并行下偶发竞态（configure 检测的 INCS/LIBS
  依赖顺序），保险起见串行。
- XPM 签名：libmobi.so.0.0.0 与 mobitool/mobimeta/mobidrm 需
  `binary-sign-tool sign -selfSign 1`（前置 `llvm-objcopy
  --remove-section .codesign`），否则运行时 Permission denied。
  签名工具和 Bash 均通过 `PATH` 动态发现，缺失时明确终止。
  探测 + 显式回退（先例：adbtuifm/akamai）。
- 设备离线：github.com 不可达，conan create 源码获取走
  `core.sources:download_cache`（`~/.conan2/d/s/<sha256>` 布局，
  无 json 元数据时直接命中），本地已验证 SHA256 的 tarball 播种即可。
- config.guess 识别 HarmonyOS（E007 命题，非 E604）：conan automake/1.18
  经 autoreconf --install 注入的 config.guess 为 vanilla 2024-07-27 版，
  无 HarmonyOS 分支（uname -s = HarmonyOS 不命中任何 case，configure 报
  cannot guess build type）。修复：patches/0001-config.guess-ohos.patch
  （LIBC 探测 __OHOS__ 分支 + *:HarmonyOS:*:* case，输出
  aarch64-unknown-linux-ohos），必须在 autoreconf 之后应用（E604 同款
  时序：早打会被 automake share 模板覆盖），build() 内 fuzz=False 严格
  应用 + configure 前四重断言（guess 三元组/sub 接受/双分支存在/无
  umask 077 残留）。幂等守卫：OHOS 适配版 autotools（宿主
  automake 1.16.5 share/config.guess）注入的 config.guess 已含分支，
  跳过补丁直接断言。config.sub（automake/1.18 自带）已原生接受
  *-linux-ohos 无需补丁。

## 路径 B 申报

本库适配过程中新增 1 个通用问题知识条目草稿：
- E604-draft-BAF9：autoreconf --install 在引导阶段重新安装带 umask 077 的
  config.guess，因此仅修补 configure 不足；必须在 autoreconf 后、configure 前
  同时处理 configure 与 config.guess，并用残留检查 fail closed
  - 适用软件：上游源码包不含 configure/config.guess、需配方内 autoreconf
    --install 引导的所有 autotools 软件包（libmobi 0.12 GitHub tag tarball 系）
  - 查重区别：与 DRAFT-6048（babeltrace，make 阶段 automake maintainer 规则
    重跑 autoconf 覆盖已修补 configure，修复靠时间戳回拨）触发阶段、被覆盖
    文件、修复边界均不同，仅在查重区别中引用，不合并
  - 知识图谱草稿：knowledge/drafts/E604-draft-BAF9.md +
    knowledge/drafts/E604-draft-BAF9.kv（draft: true，contributor_id: BAF9，
    正式条目由主编合并 PR 时自动生成）
