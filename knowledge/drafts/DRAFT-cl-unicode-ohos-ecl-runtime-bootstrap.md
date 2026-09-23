# ═══ Draft knowledge entry — OHOS 上 ECL 运行时落地:ECLDIR/SYS: 逻辑路径覆盖 + 模块符号链接 + include 软链 ═══
# Timestamp: 2026-09-08
# Software: cl-unicode 0.1.6.r12.g07e7ff5 (任何在 OHOS conan 体系下使用 ECL 的 Common Lisp 包)
# Gate: ECL 运行 / (require :asdf) / (asdf:load-system ...)
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-cl-unicode-ohos-ecl-runtime-bootstrap
severity: 3
category: platform|toolchain|lisp
trigger_tool: ecl / (require :asdf) / (asdf:load-system ...)
phase: runtime
approach: 三步落地:①LD_LIBRARY_PATH 指向 conan 包 $PREFIX/lib 与 gmp 包 lib;②ECLDIR 指向
  $PREFIX/lib/ecl-<ver>(SYS: 逻辑路径随即映射到 $PREFIX/lib/**,解决 REQUIRE 找不到模块与
  SYS:help.doc 打不开);③把 ecl-<ver>/ 下模块符号链接到 $PREFIX/lib/,并建 $PREFIX/lib/ecl ->
  ../include/ecl 软链(编译 Lisp→C 找 SYS:ecl;config.h);④ECL 编译 C 还需 gc/libffi/ncurses/
  readline 头文件,conan install 时须一并安装

keywords: ECL, ECLDIR, SYS: 逻辑路径, cmp.fas, asdf.fas, libecl.so, libgmp, include/ecl, config.h, 编译期前缀, 运行期前缀, REQUIRE

error_signature: Don't know how to REQUIRE (CMP|ASDF)|Cannot open "SYS:help\.doc"|Unable to find include directory|Error loading shared library libecl\.so
match_keywords: ECL,ECLDIR,SYS:,cmp.fas,asdf.fas,libecl.so,SYS:help.doc,Unable to find include directory,REQUIRE CMP

root_cause: conan 发布的 ECL 24.5.10 把 CI 编译机前缀(/devcloud/slavespace/.../out/sdk)烤死在
  二进制里;ECL 运行期用 ECLDIR 推导 SYS: 逻辑路径,模块(cmp.fas/asdf.fas)与头文件(SYS:ecl;config.h)
  均在推导路径之外 → REQUIRE 失败、SYS:help.doc 打不开、编译 Lisp 时 Unable to find include
  directory;另需 LD_LIBRARY_PATH 显式指定 libecl.so/libgmp
affected_scope: 所有在 OHOS conan 体系下运行/编译 Common Lisp 代码的包;任何 conan 构建的带编译期自定位路径的运行时同理

rec_priority: 1
rec_approach: ecl-runtime-bootstrap
rec_description: LD_LIBRARY_PATH + ECLDIR + 模块/头文件符号链接把 ECL 运行时"钉"到 conan 包前缀,使 REQUIRE/load-system 全链路可用
rec_command: export LD_LIBRARY_PATH="$PREFIX/lib:$GMP/lib"; export ECLDIR="$PREFIX/lib/ecl-24.5.10"; ln -sfn ../include/ecl "$PREFIX/lib/ecl"; for f in "$PREFIX/lib/ecl-24.5.10/"*; do b=$(basename "$f"); [ -e "$PREFIX/lib/$b" ] || ln -s "ecl-24.5.10/$b" "$PREFIX/lib/$b"; done
rec_auto_fix: false

fallback_priority: 2
fallback_approach: 直接 load 完整路径
fallback_description: (load "$PREFIX/lib/ecl-<ver>/cmp.fas") 再 (load ".../asdf.fas") 顺序加载可绕开 REQUIRE;编译 Lisp→C 仍需 include 软链
fallback_command: (load "$PREFIX/lib/ecl-24.5.10/cmp.fas") (load "$PREFIX/lib/ecl-24.5.10/asdf.fas")
fallback_auto_fix: false

principles: conan 构建的运行时包前缀由 CI 编译机决定,运行期必须显式覆盖;ECL 的 SYS: 逻辑路径由 ECLDIR 推导且落在 ECLDIR 的 lib 父级
caused_by: conan ECL 包编译期前缀在目标机不存在;模块/头文件位于 $PREFIX/lib/ecl-<ver>/ 而非 SYS: 推导根
causes: REQUIRE CMP/ASDF 失败、SYS:help.doc 打开失败、Unable to find include directory、libecl.so/libgmp 加载失败
similar_to: maxima 归档笔记(ECL 前缀烤死,出口 ECLDIR,2026-08-17)

verification_cmd: LD_LIBRARY_PATH=$PREFIX/lib:$GMP/lib ECLDIR=$PREFIX/lib/ecl-24.5.10 $PREFIX/bin/ecl -norc -eval '(require :asdf)'

last_updated: 2026-09-08
source_event: cl-unicode 0.1.6.r12.g07e7ff5 在 HarmonyOS 真机用 ECL 24.5.10 跑全量上游测试时逐层排障
authors: akajhsbnz
source_pr: (本 PR)
metrics_success_count: 0
metrics_fail_count: 0
metrics_confidence: 0.85
metrics_last_used: 2026-09-08
