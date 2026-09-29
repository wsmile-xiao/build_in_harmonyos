# jailkit 2.23 — 适配工作笔记（Windows 阶段 1，2026-09-26）

任务：ohpcd 平台 jailkit 2.23 · 分支 `feat/jailkit-2.23`（以平台实际显示
为准，提交前核对绑定与截止时间）。

## W0 依赖分析

**无外部 conan 库依赖**：iniparser、passwdparser、wordexp 全部随源码捆绑
（src/ 内）。可选依赖：libcap（AC_CHECK_LIB，未命中跳过）、procmail
（AC_PATH_PROG，未命中时 HAVEPROCMAIL 置 # 注释掉 jk_procmailwrapper，
BINARIES 相应减少）—— 均不 require。

构建/运行时工具：
- **python3 是 configure 硬依赖**：`AC_PATH_PROG([PYTHONINTERPRETER],
  [python], [no])`，找不到 `python` 即 AC_MSG_ERROR。上游只找 `python`
  不找 `python3` → 配方用 AC_ARG_VAR 传
  `PYTHONINTERPRETER=/data/service/hnp/bin/python3`（build() 里探测存在
  性，缺省回退 `python3`）。py/Makefile 用它重写 6 个脚本 shebang 并
  py_compile jk_lib → pyc。
- man 页需要 gzip（toybox 自带）。

R35 依赖检查为空集（无 conan 依赖）。

## W0b 历史知识核验

- 手写 Makefile（非 automake）+ 预生成 configure 先例：pspg 5.8.16 同批；
  env -u CONFIG_SHELL + 绝对路径先例：gtypist/2.10.1（§12.38①）。
- E114（umask 077→022 替换）先例：zzuf/0.15；E074（-j1）：tarsnap 等。
- 真机 python3 路径先例：loksh/7.9 的 `_HNP_BIN=/data/service/hnp/bin`。

## 源码要点（官方 tarball 2.23 实测）

- sha256 `490bbc2b955f0f03dc56789decd828287321b8ec234123cecf2fdf2aacce3f5a`
  （olivier.sessink.nl 官网 tarball；GitHub solbu/jailkit tag 归档 404）。
- 自带预生成 configure（autoconf 2.72）；configure.ac 无 AC_CANONICAL。
- src/：BINARIES = jk_socketd jk_lsh jk_chrootsh jk_chrootlaunch
  jk_uchroot（+jk_procmailwrapper 仅当有 procmail）。iniparsertester/
  passwdparsertester 有 make 规则但不在 all，无 check 目标。
- py/：6 个 .in 模板 → sed 替换 shebang/PREFIX/INIPREFIX/LIBDIR →
  sbin/jk_{init,cp,check,jailuser,list,update}；jk_lib.py →
  share/jailkit/（PYLIBDIR=${datadir}/${PACKAGE}）。
- ini/：7 个 *.ini → <prefix>/etc/jailkit/。
- **顶层 make install 含 /etc/shells 追加段**（`if test -w /etc/shells`
  守卫）→ package() 改用 ini 复制 + `make -C {src,py,man} install`，
  跳过系统路径写入。
- **setuid 4755**：jk_chrootsh、jk_uchroot（上游语义，保留）。
- 无 AC_CANONICAL → 无需 config.guess/--build；CFLAGS 走 env。
- jk_uchroot/jk_chrootlaunch 的 -h/-V：打印 "jailkit 2.23\nUsage:" 并
  exit(1)（上游语义）—— 消费者断言按 rc=1 校验。
- jk_lib.py 纯函数（fix_double_slashes/split_path/join_path）语义已
  实读确认，roundtrip 断言成立。

## 测试计划

- 上游（构建阶段，2 项）：iniparsertester（非空输出）+
  passwdparsertester（断言 `found user jaja!`，覆盖 uid 100 无换行行）。
- 消费者（test_jailkit.sh，6 项）：见 README。全部离线、确定性；
  chroot 主功能需 root，非交互面验证 CLI 与安装库 API。

## 留给 MateBook 的验证项

1. R35 依赖检查：空集（无 conan 依赖），记录即可。
2. conan create + conan test 完整跑通（configure → make -j1 → 上游
   自检 2 项 → 分段 install → 消费者测试）。
3. 关注点（失败时按下列顺序排查）：
   - jk_lib 断言依赖 POSIX 路径语义（os.path.normpath/dirname 终止于
     '/'）：设备 python3 天然满足；Windows 预验证发现 ntpath 语义下
     split_path 会死循环（'\\' != '/'），属 Windows 层现象，设备不会
     出现 —— 若 MateBook 意外经 Windows 层解释器跑消费者脚本才需处理。
   - PYTHONINTERPRETER：若 /data/service/hnp/bin/python3 不存在，确认
     `python3` 是否在 PATH；上游在两者皆无时报 "python not found"。
   - py_compile jk_lib.pyc：python 3.12 下 py_compile 应正常；若
     `python -c 'i=1;i+=1'` 检查失败（configure "too old"）说明 shebang
     指到了不兼容解释器。
   - man 页 gzip：toybox gzip -9 若行为差异导致 man all 失败，可
     MAKE 类似 MAKEINFO 占位（先记录首个真实错误再处理）。
   - make install -m 4755：toybox install 若不支持 4755 组合，记录
     错误；回退为 install 后 chmod（HMDFS 下 chmod 被忽略，属 E114 族）。
   - setuid 产物在审计中的定性：上游语义，非本配方引入。
4. `ohc-run.py finish jailkit 2.23 built` → W4 审计（不跑 submit）。

## 真机第 1 轮（SHA bbb3c2f…e67c45）补充修正：上游 iniparser 宏缺陷

主产品 5 个 jk_* 二进制构建全部成功，阻塞于上游自检程序编译：
`make -C src iniparsertester passwdparsertester` 中 iniparsertester.c
报 11 处 clang 硬错误 `too few arguments to function call`。根因是
2.23 官方 tarball 自带缺陷（非平台/配方引入，真机已核实：tarball
sha256 与 conandata 一致、conan 解包与纯净 tarball 逐文件一致）：

- `src/iniparser.h` 的便捷宏 `iniparser_get_int(ip,section,key)` 展开
  为 `iniparser_get_int_at_position(ip,section,key,0L)`（4 实参），而
  函数原型 5 形参（position + defaultval）——宏丢参；
- `src/iniparsertester.c:56` 另有 1 处 `iniparser_get_float_at_position`
  4 实参调用同病（原型 5 形参）；其余 10 处 get_int 调用经宏丢参。

修复（patches/0001-iniparser-macro-defaultval.patch，Windows 级实测
dry-run/apply 幂等、与手工修正树逐文件 diff 零残差）：
- 宏补中性默认值 0（`...,0L,0)`）；
- float 调用补缺省实参 0.0（`..., 0, 0.0)`）。

安全性论证：主线 jk_* 代码 0 处使用该便捷宏（grep 实测，均直接调用
`_at_position` 全参形式），行为零变化；自检查询的全部 key 均存在于
src/iniparsertester.ini（key10=10、keyfloat=0.1 等逐一核对），打印
输出不受默认值影响，配方断言（非空 / `found user jaja!`）不受影响。
上游 GitHub master 无对应修复可取（raw/API 404，真机实测），故以
bugfix 补丁形式携带并在 PR 说明。R35 依赖为空集，无联动变化。

### 第 2 轮（SHA fcd04c4c 验证中止后修正）：自检第 2 项漏 cd

真机实证利好：0001 补丁正常应用，5 个 jk_ 主产物全部编译链接成功，
iniparsertester 自检通过（输出 1..10 与 0.100000，无默认值泄漏——
第 1 轮 11 处宏缺陷已由补丁消除）。本轮止于自检第 2 项断言：
passwdparsertester unexpected output: 'found nothing'（期望
found user jaja!）。

根因（真机对比实测）：passwdparsertester 用相对路径读
passwdparsertester.test，配方却以绝对路径直接调用（第 142 行），
进程 cwd 不在 src/ → 读不到 .test 文件。配方缺陷，非平台/补丁问题。
修复：改为与 iniparsertester 同型写法 `cd "{src}/src" && ./...`。
新 SHA 需 MateBook 全量复验：create → test → finish → 审计
（消费者 6 项第 2 轮未执行——包未产出，不沿用任何旧结果）。

### 第 4 轮（SHA a8bf72b5 复验：自检两段全过；消费者 #1/#2 改按上游特权语义断言）

MateBook 对 a8bf72b5 复验：0001 补丁应用、5 个 jk_ 二进制编译链接、
install 四段落地（/etc/shells 段照常跳过）、R35 空依赖集全过；自检
两段首次全过——passwdparsertester 第 2 轮 found nothing 已消除，
cd 修复真机首次验证通过。

消费者 6 项首跑 4 过 2 败，#1/#2 根因（非编译/非平台/非补丁）：
jk_uchroot.c:144 在 #ifndef DEVELOPMENT 下 geteuid()!=0 → exit(11)，
错误走 syslog 不进 stdout，且先于参数解析（"No jail path specified"
在第 235 行 euid 门之后）→ 测试原断言（-h → rc=1+Usage；缺参 →
ERROR 提示）在非 setuid 消费者环境结构性不可达，属测试断言与上游
特权语义的冲突。jk_chrootlaunch 无此门故 #3 正常。

修复（test_jailkit.sh #1/#2）：改按上游语义双分支断言——非 root
（id -u ≠ 0，真机消费者环境）恒 rc=11 + stdout/stderr 零输出（错误
仅走 syslog），该断言本身即对特权门行为的真实验证；root 分支保留
rc=1+Usage（-h）与 rc≠0+ERROR（缺参）断言。Windows bash 模拟：非
root/root 两分支 + 特权门 exit(11) 静默原件 + 解析层 Usage/ERROR
原件 4 场景全过。新 SHA 需 MateBook 全量复验：create → test →
finish → 审计。
---

**编译结束**: 2026-09-28 18:50
**最终状态**: built
