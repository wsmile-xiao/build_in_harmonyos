# ═══ Draft knowledge entry — toybox sed 对非法 UTF-8 字节行正则匹配失败,autoconf AC_OUTPUT 假死 ═══
# Timestamp: 2026-09-05
# Software: boolstuff 0.1.16(任何上游配置源含 Latin-1/高位字节的 autotools 包)
# Gate: 原生 configure / conan create build()
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E549
severity: 3
category: platform|toolchain|autotools
trigger_tool: configure / config.status
phase: build
approach: configure 报 "could not make ./config.status" 且所有检测项均通过时,先对源码树执行
  `grep -rlP '[\x80-\xFF]' configure configure.ac` 找 Latin-1 文件;确认后用 python 将其从
  latin-1 转 UTF-8(语义无损),同时转其生成物;随后按 aclocal.m4 → configure → Makefile.in
  顺序 touch 固定时间戳,防止 make 触发 maintainer 重建覆盖补丁

keywords: toybox, sed, UTF-8, Latin-1, could not make, config.status, AC_OUTPUT, 高位字节,
  could not setup config files machinery, as_fn_error, ac_delim

error_signature: could not make \./config\.status|could not setup config files machinery
match_keywords: could not make,config.status,ac_delim,subs1.awk

root_cause: OHOS 的 /usr/bin/sed 指向 toybox;其正则引擎在 UTF-8 模式下把非法 UTF-8 序列
  首字节(如 Latin-1 的 0xE9)当作多字节字符开头并吞掉后续字节,导致含该字节的整行对任何
  ".*<字面量>" 正则匹配失败(锚定与非锚定均失败),而 grep 按字节处理不受影响。autoconf 2.69
  的 AC_OUTPUT 用 sed 逐行识别以 ac_delim 结尾的替换变量行,只要有一个变量值含高位字节
  (常见于上游 configure.ac 里的法语/德语摘要字符串),分隔符循环计数就永远少 1,五轮耗尽后
  as_fn_error "could not make ./config.status"。config.status 内部同款 sed 管线报
  "could not setup config files machinery" 是同一根因的下游表现。
affected_scope: 所有在 OHOS 设备上原生 autotools 构建、且上游配置源/生成物含 Latin-1 或其他
  非 UTF-8 高位字节的包;LC_ALL=C 不改变 toybox sed 行为,不能作为绕过手段

rec_priority: 1
