# PostgreSQL 18.3 构建进度

## 当前状态

构建完成，测试通过，安装成功。

## 构建流程

### Prepare (2026-06-12 12:15)
- 解压源码完成
- 补丁应用成功（11个文件）
- 补丁内容：SysV共享内存跳过、hmdfs权限放宽、getpwuid fallback、Unix socket禁用等

### Build (2026-06-12 12:21)
- Configure 成功
- Make 成功（无错误）
- 编译产物完整

### Install (2026-06-12 12:22)
- 安装到 $HOME/usr/local
- pg_config: /storage/Users/currentUser/usr/local/bin/pg_config (PostgreSQL 18.3)
- libpq: /storage/Users/currentUser/usr/local/lib/libpq.so.5.18
- headers: libpq-fe.h, pg_config.h

### Check (2026-06-12 12:23)
- 测试结果: 229/230 通过
- 失败测试: opr_sanity (utf8_and_uhc.so 权限问题，OHOS 签名机制限制)
- 跳过测试: 6个（并行相关）

## 修改记录

### 补丁文件
- postgresql_harmony.patch (11个源文件修改)

### 核心修改
1. **SysV 共享内存跳过**: src/backend/port/sysv_shmem.c
   - shmget/shmat/shmdt/shmctl syscall 不可用
   - 返回 fake header，依赖 mmap-based DSM

2. **hmdfs 权限放宽**: src/backend/utils/init/miscinit.c
   - 目录所有权检查放宽到 group 匹配
   - 权限检查只验证 owner rwx

3. **shm_open 强制 mmap**: src/include/storage/dsm_impl.h, src/bin/initdb/initdb.c
   - configure 检测成功但实际调用 SIGSYS
   - 强制使用 DSM_IMPL_MMAP

4. **getpwuid fallback**: src/common/username.c, src/interfaces/libpq/fe-auth.c
   - 用户不在 /etc/passwd 时使用数字 UID

5. **Unix socket 禁用**: src/include/pg_config_manual.h, src/test/regress/pg_regress.c
   - OHOS 不支持 Unix-domain socket
   - DEFAULT_PGSOCKET_DIR 设为空

6. **mkdir 权限修正**: src/bin/initdb/initdb.c, src/port/pgmkdirp.c
   - hmdfs 创建目录带异常 S-bit
   - mkdir 后 chmod 修正权限

## 构建总结 (2026-06-12)

### 成功要点
- PostgreSQL 在 OHOS 平台成功构建和安装
- 核心依赖库 libpq 和开发工具 pg_config 可用
- 测试通过率 99.6% (229/230)

### OHOS 平台适配要点
1. **System V IPC syscall 完全不可用**：shmget/shmat/shmdt/shmctl/shm_open 都返回 SIGSYS
   - 解决方案：全面跳过 SysV 共享内存，使用 mmap-based DSM

2. **configure 检测与实际调用不一致**：shm_open configure 检测成功但实际调用失败
   - 解决方案：条件编译强制覆盖检测结果

3. **hmdfs 文件系统限制**：目录所有权、权限、mkdir 异常
   - 解决方案：放宽检查、mkdir 后 chmod

4. **getpwuid 可能失败**：用户不在 /etc/passwd
   - 解决方案：fallback 使用数字 UID

5. **Unix-domain socket 不支持**：bind 返回 EPERM
   - 解决方案：禁用 Unix socket，使用 TCP/IP

### 测试失败分析
opr_sanity 测试失败原因是 utf8_and_uhc.so 共享库加载权限问题：
```
ERROR:  could not load library ".../utf8_and_uhc.so": Permission denied
```
这是 OHOS ELF 签名机制导致的限制，非源码 bug。实际运行 PostgreSQL 服务需确保所有 .so 文件已签名。

### 安装产物验证
- pg_config 功能正常（--version、--includedir、--libdir）
- libpq.so.5.18 存在且可链接
- libpq-fe.h 和 pg_config.h 头文件可用
- 满足 psycopg2-binary 构建需求

### 后续任务
TASK-100-psycopg2-binary 现在可以继续构建，依赖已满足。
## Conan 配方化 (2026-09-03)

### 转换概述
- 从手动构建归档（build.sh，commit 149f3b650 直提 main）升级为完整 Conan 配方
- 新增：conanfile.py、conandata.yml、test_package/（test_libpq.c + conanfile.py + MANIFEST.yml）、patches/（postgresql_harmony.patch 由版本目录根移入，重命名为 0001-ohos-platform-adaptation.patch 以满足 NNNN-*.patch 归档命名规范，内容零改动）
- 软件级三件套补齐：README.md、manifest.yaml、commands.json（R38，35 个命令全列）
- 补丁初始原样沿用（__OHOS__ 守卫 + miscinit.c 重复 hunk 段）；评审轮（MR #7992 R8 意见）重写为语义能力宏并以 git diff 从已验证树重新生成（见下方"评审轮补丁重写"）
- 源码 sha256 补全：d95663fbbf3a80f81a9d98d895266bdcb74ba274bcc04ef6d76630a72dee016f（与 ftp.postgresql.org 官方 .sha256 交叉验证一致）
- 原 manifest dependencies 列 icu/tzdb 与实际不符（configure 明确 --without-icu，tzdata 内嵌）→ 修正为空依赖列表

### 与历史构建配置的偏离点（W0b 记录）

1. **--build=aarch64-linux-ohos 替代外置 config.sub/config.guess 拷贝**
   - 历史 build.sh：从 $HOME/usr/local/share/config/ 拷贝 config.sub + config.guess 到源码树 config/
   - 偏离原因：该路径在当前环境已不存在（实测 ls 为空），CI 干净环境更不可依赖；实测 PG 18.3 自带 config.sub 已能识别 aarch64-linux-ohos；显式传 --build=aarch64-linux-ohos 后 configure 跳过 config.guess（其数据库无法识别 OHOS，且其临时文件探测受 hmdfs umask 077 破坏）
   - 验证证据：实测 configure --build=aarch64-linux-ohos 成功（2026-09-03，本机），产物 35 bin + 4 组库 + include 完整，二进制全部可执行
   - 模式不变：本机即 OHOS PC aarch64，仍为原生（非交叉）构建，与历史一致

2. **umask 077 → 022（历史为 067）**
   - 历史 build.sh：`sed 's|umask 077|umask 067|g'`，注释"修复 hmdfs 上 umask 077 导致临时目录不可写"
   - 偏离原因：社区配方（aspell，已合并 main）同场景用 022；本次实测 022 全流程通过（configure → make -j8 → install → 二进制运行）
   - 验证证据：实测 configure + make + install + psql/pg_config/postgres --version 全部成功

3. **make -j8 显式并行**
   - 历史 build.sh：make -j$(nproc)；实测本机 -j8 无 HMDFS FIFO jobserver 问题，全量构建约 3 分钟（远小于 W3/CI 默认 3600s 预算，无需 timeout override）

4. **make check 不在 conan build() 内执行**
   - 历史：手动 make check 229/230 通过（opr_sanity 失败=OHOS ELF 签名机制限制 .so 加载，非源码 bug，已知平台限制不阻塞）
   - 偏离原因：make check 需要完整服务端运行时（initdb 建数据目录、TCP 监听、大量子进程），conan create/CI 干净沙箱内风险高；test_package 以 libpq 真实 API（PQlibVersion）链接+运行替代（R34），不尝试加载服务端扩展 .so（规避签名限制）

5. **install 阶段 use_install_sh=yes（新发现的环境坑，非历史配置偏离）**
   - 现象：make install 时 PATH 首位的 $HOME/usr/local/bin/install（本机 shim，CI profile buildenv 同样将其前置）不支持分离参数形式：`install -c -m 755 src dst` → `cp: bad '755': No such file or directory`
   - 解法：PG 原生支持 `make install use_install_sh=yes` 切换到自带 config/install-sh（正确处理分离参数与所有 PG 安装模式）
   - 验证证据：实测 staging 安装产物完整（bin 35 / lib 21 / include / share），无 bad 模式报错

### 环境坑记录（工具链，非源码问题）
- **OHC_PROJECT_DIR 必须显式导出**：本机 SKILL_ROOT（~/.opendesk/apps/skills/resources/openharmony-compile-agent）被先前会话污染（内含 SKILL.md + archives 镜像），ohc-run.py 的 find_project_dir() 会将其误判为项目根（conan-init 曾把骨架写到 SKILL_ROOT/archives/p/postgresql/18.3/，已清理）。解决：所有 ohc-run.py 调用前 `export OHC_PROJECT_DIR=/storage/Users/currentUser/runner001/build_in_harmonyos`（仓库根含 SKILL.md，find_project_dir 第一优先级接受该环境变量）。框架层建议：find_project_dir 可增加 .git 目录探测或优先 cwd 向上查找，补丁另行移交维护者。
- **/tmp 只读**（E002 已知）：conanfile build() 内保障 TMPDIR 指向可写目录（默认 $HOME/tmp）

### 二轮修复（W3 首跑发现的两个问题）

6. **LDFLAGS_EX 追加 $ORIGIN 相对 rpath（configure 后改写 Makefile.global）**
   - 现象：W3 首跑 L2 smoke 21/35 命令失败（psql/pg_dump 等 21 个链接 libpq.so.5 的工具），根因是 PG --enable-rpath 生成的 RUNPATH 指向 configure 时 prefix（DESTDIR 打包后变为无效的 //lib），运行时找不到包内 libpq.so.5
   - 首选尝试（失败，已记录）：make 命令行传 `LDFLAGS_EX=-Wl,-rpath,'$$ORIGIN/../lib'` —— conan Autotools.make 的 args 纯拼接经 sh -c 执行，单引号被 shell 剥离、$ORIGIN 在子 shell 被展开为空串，链接器实际收到 /../lib（RUNPATH=[//lib:/../lib]，W3 二跑 L2 仍 21 失败）
   - 最终方案：configure 后用 replace_in_file 直接改写 build 树 src/Makefile.global 的 LDFLAGS_EX 行为 `-Wl,-rpath,'$$ORIGIN/../lib'`（确定性文本替换，不经 shell 解析链；make 展开为 $ORIGIN，配方 shell 的单引号保护字面量，链接器正确记录 $ORIGIN/../lib）
   - 验证：实测 psql RUNPATH = [<prefix>/lib:$ORIGIN/../lib]；psql 与 libpq.so.5 复制到任意 bin/ + lib/ 目录结构下，无 LD_LIBRARY_PATH 直接运行成功（psql (PostgreSQL) 18.3）
   - 收益：L2 全绿 + 下游使用体验（conan install 后 psql/pg_dump 等直接可用）

7. **L4 危险函数扫描命中为误报（不修改补丁）**
   - W3 L4 用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 扫 patches/，命中补丁（现 0001-ohos-platform-adaptation.patch）两处
   - 查证：英文注释里的 "gets mapped"；以及 psprintf（PostgreSQL 官方安全封装，内部 vsnprintf 定长分配）——正则无前置词边界导致子串误报
   - 结论：补丁无真实危险函数调用，L4=warn 不阻塞，维持原样（AI Review/审计引用本条说明）

### 评审轮补丁重写（MR #7992，R8 合规，2026-09-04）

8. **__OHOS__ 守卫 → 语义能力宏（AI Review P1 + High Priority 意见）**
   - 动因：R8（iron-rules 唯一权威口径）——patches/ 补丁默认禁止平台宏（#ifdef __OHOS__），例外须 PR 说明并获维护者确认；本 PR 选择改写而非申请豁免
   - 方案：守卫重命名为 5 个语义能力宏——HAVE_BROKEN_SHMGET（shmget SIGSYS）/ HAVE_BROKEN_SHM_OPEN（shm_open 探测过但运行时 SIGSYS）/ HAVE_BROKEN_GETPWUID（/etc/passwd 缺用户）/ HAVE_BROKEN_UMASK（hmdfs S-bit 与组权限怪癖）/ HAVE_NO_UNIX_SOCKETS（Unix 域 socket bind EPERM）；由 conanfile.py generate() 仅在 settings.os == OHOS 时经 tc.defines 注入 CPPFLAGS（-D 宏定义进 conanautotoolstoolchain.sh）
   - 平台无感：Linux 构建不定义这些宏，守卫分支全部编译剔除——与历史 __OHOS__ 未定义时的行为完全一致（对编译平台无感，评审建议的 POSIX 探测/运行时回退方向中，宏注入是 PG 代码结构下最小侵入的实现）
   - 代码语义零变化：以旧补丁（patch_ng 应用产出）树为基准做文件级改写后用 git diff 重新生成补丁；等价性审计（旧守卫树 vs 新守卫树 diff）确认全部差异仅为守卫名与注释文本，无代码逻辑变化
9. **补丁结构修复（顺带）**
   - 原手写补丁存在 miscinit.c 重复 hunk 段 + hunk 计数偏差：git apply --check 在干净树上必败（重复 hunk 语义冲突），仅 patch_ng/GNU patch 宽容通过；git diff 重新生成后双引擎（git apply -p1 严格模式 / patch_ng strip=0，即 conan 实际调用形态）均在干净树上验证通过
   - 补丁由 11 个文件段（miscinit 重复计 2）变为 10 个文件段，450 行 → 精确计数的标准 git 格式

10. **宏注入首跑失败：tc.defines 只读 property 陷阱 + clang 原生预定义 __OHOS__（2026-09-04 第三轮复验发现）**
    - 现象：重写补丁后首跑 W3，L2 34/35——唯 `pg_upgrade --version` 失败：`could not look up effective user ID 20020085: user does not exist`（pg_upgrade 在选项解析早期即调 getpwuid，其余 34 个命令的 --version 路径不触达平台守卫代码，故"几乎全绿"极具迷惑性）
    - 根因一（API 陷阱）：本仓 OHOS 适配版 conan 2.29.1 的 `AutotoolsToolchain.defines` 是**只读 property**（每次返回 `[ndebug, gcc_cxx11_abi] + extra_defines + conf_flags` 的新列表），`tc.defines.extend([...])` 是静默 no-op；正确公共可变属性是 `tc.extra_defines`。验证法：查 build 树 `conan/conanautotoolstoolchain.sh` 的 CPPFLAGS 是否含 -D 宏、`src/Makefile.global` 的 `CPPFLAGS =` 行、configure 日志 `configure: using CPPFLAGS=...`
    - 根因二（历史真相）：OHOS PC 系统 clang（/data/service/hnp/bin/clang）**原生预定义 `__OHOS__`**（`clang -dM -E -x c /dev/null` 可证：`#define __OHOS__ 1`）——历史 `__OHOS__` 守卫补丁从未依赖任何显式注入，这也解释了旧构建为何直接通过。宏改名的重写必须同步验证注入链路，否则守卫代码整体被编译剔除
    - 修复：`tc.defines.extend` → `tc.extra_defines.extend`；复验 configure 日志确认 `CPPFLAGS=... -DHAVE_BROKEN_SHMGET -DHAVE_BROKEN_SHM_OPEN -DHAVE_BROKEN_GETPWUID -DHAVE_BROKEN_UMASK -DHAVE_NO_UNIX_SOCKETS ...`，L2 恢复 35/35

## 问题与解决方案汇总
| 问题 | 根因 | 解决方案 |
|---|---|---|
| make install 报 cp: bad '755' | PATH 首位的本机 install shim 不支持 -c/-m 分离参数形式 | make install 加 use_install_sh=yes 改用源码树自带 config/install-sh |
| conan create 后 L2 21/35 命令失败（psql 等无法定位 libpq.so） | DESTDIR 打包安装后 configure 期 rpath //lib 失效 | configure 后改写 src/Makefile.global 注入 LDFLAGS_EX = -Wl,-rpath,$$ORIGIN/../lib |
| conan 命令行传含 $ORIGIN 的 LDFLAGS 失效（RUNPATH 变 /../lib） | conan 参数纯拼接经 sh -c 执行时单引号被剥离，$ORIGIN 在子 shell 展开 | 弃用命令行传参，改在 Makefile.global 内双写 $$ORIGIN |
| autoconf configure 探测报临时文件不可读或无执行权限 | hmdfs 环境 umask 077 使 configure 生成的探测脚本权限不足 | build() 中 umask 022 并保障 TMPDIR 指向可写目录 |

## 源码修改说明
适配对上游源码的修改全部在唯一补丁 patches/0001-ohos-platform-adaptation.patch 内（10 个文件，语义能力宏守卫，与 commit 149f3b650 的历史适配代码逐行等价——评审轮仅重命名守卫宏与注释、消除重复 hunk 段，代码逻辑零变化；宏由 conanfile.py 仅对 OHOS 构建注入，Linux 下守卫代码编译剔除）。test_package/test_libpq.c 为新增测试程序，不属于对上游代码的变更。

## 依赖说明
无 conan 依赖：configure 显式 --without-icu --without-readline --without-zlib --without-openssl，tzdata 内嵌源码树发布，manifest dependencies 为空列表。

## 验证结果（可复现命令）
```bash
zsh ci/conan/build_and_test.sh archives/p/postgresql/18.3
python3 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py conan-verify postgresql 18.3
```
- W3 ci/conan/build_and_test.sh：100% pass（L0/KC/JC/L2/L4/L5 全过；L2 35/35 命令 --version 免 LD_LIBRARY_PATH 直接运行通过）
- conan-verify 八门禁：全 PASS（G0-G4 + L2/L4/L5）
- test_package：PQlibVersion() = 180003，PASS: linked and executed against libpq 18.3

---

**编译结束**: 2026-09-03 20:52
**最终状态**: built
