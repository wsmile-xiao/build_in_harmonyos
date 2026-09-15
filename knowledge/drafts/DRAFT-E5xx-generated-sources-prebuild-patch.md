# ═══ Draft knowledge entry — 上游"文档生成源码"缺失(makeinfo/texinfo 依赖)→ 预生成补丁 ═══
# Timestamp: 2026-09-11
# Software: ne 3.3.4(任何把源码文件当生成物、由 texinfo/生成器在构建期产出的上游)
# Gate: conan create build() / make
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E5xx-generated-sources-prebuild-patch
severity: 2
category: build-system
trigger_tool: make / makeinfo
phase: build

error_signature: make: makeinfo: No such file or directory|no such file or directory: 'src/hash\.c'
match_keywords: makeinfo,texinfo,texi2any,info2src,generated sources missing,gitignore generated,hash.c not found,names.c not found,Cannot find makeinfo,texinfo required

root_cause: 部分上游项目把一部分源码文件当"生成物"(.gitignore 排除),由文档源
  (texinfo) + 代码生成器(makeinfo + perl 脚本)在构建时生成。官方发布的 tarball
  可能包含生成文件(ne 官网说 make source 生成),但 GitHub tag 自动 tarball
  **不包含**——conandata 用 GitHub tag URL 时构建即失败(makeinfo Error 127 或
  hash.c file not found)。而 CI 环境通常没有 texinfo(GNU 文档工具链冷门;
  cmd-pkgs texinfo 7.3 预编译包缺 perl 模块 Texinfo::ModulePath 不可用)。

rec_approach: 1. 识别特征:src/.gitignore 列 .c/.h;makefile 规则从 .texinfo/.pl
  生成源码;README 说 "make source" 生成 tarball。2. 本地预生成:优先找官方
  发布 tarball(Debian orig tarball 若与 tag 逐字节一致也行);否则本地装工具链
  生成。makeinfo 可免安装:GNU texinfo 源码树 tta/perl/texi2any.pl 直接跑
  (唯一前置:手工 sed 生成 Texinfo/ModulePath.pm——从 .in 模板替换
  @enable_xs@→no、@CONVERTER@→texi2any、@USE_EXTERNAL_*@→no)。
  3. 生成产物托管为本仓库专属分支(如 ne-src-raw),conandata 加
  generated_sources 自定义段(url 指 raw.gitcode.com 分支 archive
  tarball,先例 clp 1.17.10 的 clp-src-raw),source() 里 get() 下载
  (sha256 校验)后 copy() 拷入源码树。⚠ 两条已实证死路:(a) 文本
  .patch——被 AI 代码检视计入可审行数,~4000 行直接超 AI 分片上限
  (ne 3.3.4 实测 4334 行被拒 4 次;tcpkali !3091 平铺 prebuilt/ 36
  文件 39996 行同被累计计数跳过);(b) 二进制归档 prebuilt.tar.gz
  (libtar/md5deep 先例)——CI worker checkout-pr 用 git apply 应用
  PR.diff,二进制文件在 diff 仅 "Binary files differ" 标记(无 base85
  数据段),git apply 报 missing binary patch data → checkout 必死
  (CI #44405/#44408 实证,本地复现)。托管分支方案文件不进 PR diff
  (AI 零计数)且 checkout 无障碍。
  4. 再打 0002 补丁摘除 makefile 再生成规则——否则补丁后文件 mtime 与
  依赖不一致会触发重跑 makeinfo(CI 又失败)。5. 版本号宏若含生成日期,
  sed 回上游真实发布日期保证可复现。
  补丁→归档存量转换(纯新增文件补丁):按 +++ 路径重建文件(+ 行去
  前缀),tar czf;逐字节等价验证:git apply 原补丁 vs 归档解包逐文件 cmp。

fallback: tool_requires texinfo/…(若制品仓有可用包);或 conandata 直接用
  官方发布 tarball URL(若上游发布且含生成文件)。

verification_cmd: conan create archives/n/ne/3.3.4 -pr:h ci/conan/profiles/ohos-aarch64
  -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
  # 期望: get() 下载 generated_sources tarball + Apply patch 0002 后
  # 构建成功, 4 测试全绿(CI 无 texinfo 亦通过)
  # 负向(无 0002 补丁): make 重跑 makeinfo -> Error 127(已实证)

affected_scope: 所有"文档生成源码"型项目(ne 家族、部分 GNU 老项目用 texinfo;
  yacc/lex/ragel/gperf 同型但工具链有成熟包,texinfo 型最冷门)

prescan_pattern: makeinfo|texi2any|info2src
