# OHOS 设备会话 getlogin_r(3)/LOGNAME 空成功语义导致身份类软件以空用户名继续运行，应显式拒绝空串并回退候选身份链（env → getlogin_r → getpwuid）

- **草稿 ID**: DRAFT-empty-login-identity-empty-success
- **来源**: rcs/5.10.1 适配（run `rcs-5.10.1`，分支 `feat/rcs-5.10.1`）；机理 1 条主线，其余三条机理（chmod no-op / /tmp 只读 / conan PWD-getcwd）已由 Curator 判定归 E046/E047、E002 家族、E386+DRAFT-autoconf269 及经验仓草稿，见"查重差异"。
- **分类**: 八分类之 **musl-libc 差异**；受控词表 category = libc, musl, posix, environment, runtime
- **门禁关联**: L1（上游 make check）——空用户名使 rcs 上游 63 项 shell 测试中 16+ 项群失败，直接阻塞 L1 门禁
- **状态**: 本地草稿（未创建 Issue/PR，未生成正式知识编号；编号由知识库主编确认，本稿不自占 E 编号）

## 问题 / 错误签名

设备实测探针（见 verification_cmd）输出：

```
getlogin_r=0 len=0 LOGNAME=[] pw_name=[(none)]
shell LOGNAME=[]
```

三个事实同时成立：`getlogin_r(3)` 返回 0（**成功**）但缓冲区为空串；`LOGNAME` 环境变量存在但为空串；`/etc/passwd` 无 HMDFS uid 条目（`getpwuid_r` 无 `pw_name`）。

软件侧表现（rcs/5.10.1 上游测试日志，证据路径 `build-manual/tests/t900.d/out` 等）：

- `co: invalid identifier` + 空名（`` `' ``）/ `ci: invalid identifier`（空串被当作标识符校验失败）
- `co aborted` / `ci aborted` → `PROBLEM: command failed: co -l $w`（t900）
- 上游 5.10.1 自带矛盾提示：`PFATAL ("Who are you?  Please setenv LOGNAME.")` —— 文案让用户设 LOGNAME，代码却不读 env
- 修复前中间态 `make check` 40/63（Builder 记录，未独立复核），修复链完成后门禁消息：`rcs/5.10.1: upstream make check: 60/63 passed; platform-known failures: t790, t900, t999`（conan-create-10.log / ci-run-final.log，Curator 已独立复核最终态）

## 根因

1. **"空成功"语义**：musl/OHOS libc 的 `getlogin_r` 在无 utmp/控制终端的会话（sshd 非交互、conan posix_spawn）里不报错，而是返回 0 + 空串；`getenv("LOGNAME")` 亦返回空串（设备会话默认 `LOGNAME=`）。
2. **身份解析链不拒绝空串**：rcs `src/b-excwho.c getusername()` 的 `#define JAM(x) (BE (username) = x)` 把 `cgetenv("LOGNAME")`/`cgetenv("USER")`/`getlogin_r` 的结果无条件缓存——空串非 NULL，即被视为"已解析"，回退链（env → getlogin_r → getpwuid_r）在第一步就提前终止。
3. **下游符号校验**：空用户名参与作者/锁字段与 `checkidentifier` 校验 → `invalid identifier \`'`，`ci`/`co` 直接中止；任何以用户名为主键的软件（VCS、mail 代理、构建记录）同理命中。

## 最小修复方案（推荐，双实例同 run 验证）

1. **源码层（P005，可上游提交）**：补丁 `0004-treat-empty-login-as-unset.patch`，一行宏语义修正——

   ```c
   /* OHOS: getlogin_r and the environment may yield an empty name;
      treat that the same as unset so that later candidates are tried.  */
   #define JAM(x)  (BE (username) = (x) && *(x) ? (x) : NULL)
   ```

   空串与未设置同义，回退链继续走 env 第二候选 → getlogin_r → getpwuid_r；全部为空时按上游原语义 PFATAL（设备上即 "no password entry"，诊断准确）。
2. **配方/会话层（P014）**：构建与测试环境注入非空 LOGNAME——conan recipe `build()` 内 `if not os.environ.get("LOGNAME"): os.environ["LOGNAME"] = "ohos-builder"`（注意 `setdefault` 不覆盖空串，必须判空值）；测试脚本亦显式 `export LOGNAME=<name>`。

## 方案空间（含诚实权衡与反模式）

- **fallback（priority 2）**：仅配方/会话层注入非空 LOGNAME，不改源码。权衡：只掩盖症状——库内"空串=有效身份"的缺陷仍在，锁/作者标识是注入的伪造名（多用户语义失真）；对不读 env 身份源的软件无效；换到无注入的交互会话即复发。
- **forbid_1（反模式）**：以空串继续/缓存空用户名。理由：空名写入 ,v 作者/锁属主字段后，锁归属判断与符号校验全部歧义（t900.d/out 的 `co: invalid identifier \`'` 连锁中止）。后果：仓库语义损坏、上游测试群失败。
- **forbid_2（反模式）**：`getlogin_r` 一处失败即 PFATAL、不尝试 env 回退。理由：回退链断裂即放弃，上游 5.10.1 原逻辑即反例（提示语要求 setenv LOGNAME，代码却不读）。后果：存在可用身份源时仍不可用。

## 自包含验证命令

任何人在设备 shell 直接执行（写 cwd，规避 /tmp 只读）：

```sh
cd "$(mktemp -d 2>/dev/null || pwd)" && printf '%s\n' \
'#include <unistd.h>' '#include <stdio.h>' '#include <string.h>' \
'#include <pwd.h>' '#include <stdlib.h>' \
'int main(void){char b[256];int r=getlogin_r(b,sizeof b);struct passwd*p=getpwuid(getuid());printf("getlogin_r=%d len=%d LOGNAME=[%s] pw_name=[%s]\n",r,r==0?(int)strnlen(b,sizeof b):-1,getenv("LOGNAME")?getenv("LOGNAME"):"(unset)",p&&p->pw_name?p->pw_name:"(none)");return 0;}' \
> idprobe.c && /data/service/hnp/bin/clang idprobe.c -o idprobe && ./idprobe \
&& echo "shell LOGNAME=[$LOGNAME]"
```

命中本模式时输出 `getlogin_r=0 len=0 LOGNAME=[] pw_name=[(none)]`。

## 实际验证结果（rcs/5.10.1 载体）

- 补丁 0004 + 非空 LOGNAME 注入后：t390–t632/t790–t999 中原 16+ 项空用户名失败全部转 PASS；最终门禁 `upstream make check: 60/63 passed; platform-known failures: t790, t900, t999`（剩余 3 项为 HMDFS chmod no-op 平台限制，属 E046/E047 面，与本条目无关）。
- 权威 CI：`ci/conan/build_and_test.sh archives/r/rcs/5.10.1` RC=0，L1_RESULT=pass（分支 `feat/rcs-5.10.1` 候选提交）。
- 修复前后对照的原始日志：`conan-create-*.log`、`build-manual/check.log`（run tmp 目录；中间态 40/63、59/63 为 Builder 记录，未独立复核）。

## 适用范围 / 非适用边界

- 适用：任何从 getlogin_r/LOGNAME/USER/getpwuid 派生用户身份、并对身份做符号校验或写入记录的软件，在 OHOS 设备会话与 conan spawn 环境的构建/测试/运行。
- 不适用：不使用用户身份的纯库；已在有 passwd 条目的环境（如常规 Linux CI）运行的情形；锁/作者字段损坏后的仓库修复（那是结果，不是本机理）。

## 查重差异（Curator §1.5 复核）

- **E338**（getpwuid 返回 NULL → homedir NULL → SIGSEGV）：同族身份源缺陷，但故障面不同——E338 是"NULL 即崩"，本条是"**空成功即继续**"（静默污染而非崩溃），修复点分别在"NULL 回退"与"空串拒绝"。
- **E046/E047**（HMDFS chmod no-op）：本 run 另一机理，已覆盖，不入本条。
- **E002 家族**（/tmp 只读、tmpfile/TMPDIR）与 **E386 + DRAFT-autoconf269**（conan spawn PWD/getcwd ENOTSUP）：本 run 机理 3/4，已覆盖，不入本条。
- **E007/E072**：同 run 同款 ohos 三元组平台适配先例（config.guess/sub），仅作 similar_to 关联。
- 经验仓 `experience-drafts/` 已承载其余机理条目（Curator 投递，不计 B 配额）。

## 关联交付

- 与 `archives/r/rcs/5.10.1/**`（补丁 0004、recipe LOGNAME 注入、notes.md）属同一交付范围（路径 A+B，同 PR 关联）。
- 本轮仅生成本地草稿；未创建/更新 Issue/PR，未触发远端 CI，未写 Conan 远端。
