# ═══ Draft knowledge entry — CONFIG_SHELL=bash 下老 ltmain.sh 生成的 libtool 丢引号转义 ═══
# Timestamp: 2026-09-05
# Software: boolstuff 0.1.16(所有分发物自带 libtool 2.4.x 时代 ltmain.sh 的 autotools 包)
# Gate: conan create build() / 原生 make
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E551
severity: 3
category: platform|toolchain|autotools
trigger_tool: libtool / make
phase: build
approach: make 阶段 libtool 报 "syntax error near unexpected token `}'" 且出错行是版本脚本
  字符串(如 echo "local: *; };" >> ...ver)时,diff 对比成功环境同文件:若 archive_expsym_cmds
  等值内引号缺 \" 转义,则为 config shell 解析方言问题;在 conanfile build() 内用命令行前缀赋值
  `CONFIG_SHELL=/bin/sh <src>/configure <args>` 重新生成(前缀赋值优先于聚合 env,可胜过
  profile buildenv 的 CONFIG_SHELL 覆盖),make 阶段 SHELL 随 configure 检测自动回正

keywords: libtool, CONFIG_SHELL, bash, syntax error, archive_expsym_cmds, ver~, 版本脚本,
  quote escaping, ltmain.sh, near unexpected token

error_signature: libtool: line \d+: syntax error near unexpected token `\}'|local: \*; \};.*ver
match_keywords: libtool,syntax error,unexpected token,CONFIG_SHELL,archive_expsym_cmds

root_cause: OHOS 的 conan profile buildenv 将 CONFIG_SHELL 指向 hnp bash 并在 env 聚合顺序中
  覆盖配方注入;同一 libtool 生成代码在 bash 下与 mksh(/bin/sh)下的引号处理路径不同,configure
  从 ltmain.sh(2.4.2,2016)生成 libtool 时 archive_expsym_cmds 等多行命令值的内部双引号丢失
  \" 转义,产物 libtool 文件本身成为非法 sh,bash/mksh 执行均在版本脚本行报 syntax error。
  对照成功环境同文件可见差异只在转义层,证明非 libtool 内容缺失。
affected_scope: 所有经 conan(profile buildenv CONFIG_SHELL=bash)在 OHOS 设备构建、分发物自带
  老 ltmain.sh 的 autotools 包;原生探索在 /bin/sh 下跑同一 configure 不复现,极易造成
  "探索成功、conan 失败" 的错觉

rec_priority: 1
