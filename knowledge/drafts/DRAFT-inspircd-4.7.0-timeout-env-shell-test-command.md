# DRAFT-inspircd-4.7.0-timeout-env-shell-test-command
> timeout 包装带变量赋值的 shell 测试命令时经 env 传递
## 问题特征（真实日志片段/标记）
- 真机 test_package 阶段编译打包已过，同一日志中显示 `Package built`，失败下移到 test 启动行：

timeout: failed to run command 'INSPIRCD_BIN=/storage/.../inspircd.signed': No such file or directory

- 原代码组装为 `inner = timeout 300 + VAR=... /bin/sh test_inspircd.sh`，随后 `test()`因无 RESULT 行抛 harness broken，真机门禁报告为 `test()第191行无RESULT行`。
- 前几轮的 TMPDIR 构建副本、手抄兜底和日志降载与此无关且继续保留，本轮换到 harness 层修复。
## 根因
- `test_package/conanfile.py` 把 `VAR=val` 前缀直接拼在 `timeout` 之后，GNU `timeout` 直接 `exec` 首参而不理解 shell 变量赋值语义，故把 `INSPIRCD_BIN=...` 当可执行文件名执行，报 `No such file or directory`。
- 无 `timeout` 时由 `/bin/sh` 解析赋值所以本地不易复现，仅在真机存在 `timeout` 的包装路径下暴露。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `test_package/conanfile.py` 拆分 `env_prefix` 与 shell 命令，不再把 `VAR=val` 直接拼在 `timeout` 后。
2. 有 `timeout` 时拼为 `timeout 300 env VAR=... /bin/sh test_inspircd.sh`，经 `env` 传递变量，让 `timeout` 的首个 exec 目标为 `env`，由 `env` 再建立环境后执行 shell。
3. 无 `timeout` 时保持 `VAR=... /bin/sh` 原语义不变。
4. `timeout` 路径优先 `shutil.which("timeout")`，回退到 `/data/service/hnp/bin/timeout`，并对变量值与路径做 `shlex.quote`。
5. 仅改变命令转义方式，不改变测试用例计数与断言，不删除断言；验证以 `timeout` 报错行消失且出现 RESULT 行为准。
## 禁止策略
- 禁止 `timeout 300 [A-Z_]+=... /bin/sh` 写法：禁止把 `VAR=val` 赋值直接放在 `timeout` 之后。
- 原因：`timeout` 不理解 shell 赋值语义会把赋值当程序名 `exec`。
- 后果：报 `No such file or directory` 且无 RESULT 输出，`test()` 因无 RESULT 行抛 `harness broken`，任务退回修复循环。
## 与相近条目的边界（查重）
- 查重命中仅为 `HMBS_PLATFORM_CAPABILITIES`/`BUILD_TOOLS`/`HMBS_UPSTREAM_TEST_RESULT` 通用行及 E672/daw 编译器错误，与 `timeout+env` 和 TMPDIR 真实写探针场景无实质重叠。
- TMPDIR 构建副本加真实建文件/读/删探针并降级拷贝内 `-w` 误报是 compile 阶段针对 HMDFS 上 `perl -w` 误报的修复，与本条目 testing 阶段 `timeout` harness 转义修复正交，两者同时保留不互相替代。
## 适用判断
- 适用：用 `timeout` 包装带 `VAR=val` 前缀的 shell 命令且真机存在 `timeout` 时；`test harness` 报首个 VAR 赋值为 `No such file` 且无 RESULT 输出时。
- 可复用性：`timeout` 包装 `VAR=val` 命令经 `env` 传递的通用 harness 解法可复用于所有 `test_package`，非单库临时补丁。
- 谨慎：仅改变命令转义方式，不改变测试用例计数与断言；不因 harness 报错而删除测试断言或放宽 RESULT 校验。
