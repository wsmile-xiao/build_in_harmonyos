# 真机 shadow CI 中设备 bash/git 二进制间歇性不可执行导致 KC 假性失败：job 副本 `bash`→`sh` 降级

- **软件**: libltc 1.3.2（泛化到所有在该真机跑 shadow CI 的库）
- **阶段**: shadow CI（run-conan-heavy.sh → build_and_test.sh 门禁）
- **severity**: 2
- **状态**: DRAFT

## 现象

```
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L1/L2/L4/L5_RESULT=skip: blocked_by_KC
```

同时 stderr 出现 `build_and_test.sh:164: permission denied: git`（G0e 的
`git ls-files` 失败被容错，侥幸 pass）。交互登录后 `bash --version` 报
`inaccessible or not found`；`ls -l /usr/bin/bash` 也 Permission denied。

关键对照：**同日 10:02 的 libebur128 job（相同脚本）bash 正常、KC pass；
10:14 起我的 job 开始失败** —— 设备 bash 可用性随时间漂移，不是包或知识库问题。

## 根因

设备 `/usr/bin/bash`（及 `git`）为状态漂移的未确认 ELF：execve 被拒（对 bash 连
stat 都被拒）。`ci/conan/build_and_test.sh` 中 KC（980 行）与 JC（1002 行）两处
硬编码 `bash ci/scripts/xxx_check.sh`，bash 不可用即 `blocked_by_KC`，掩盖真实门禁结论。
这与 E054（外来二进制首次执行被安全确认弹窗阻止）同族：设备侧环境状态问题。

## 修复（实测通过）

KC/JC 检查脚本本身是 POSIX sh 兼容的（`sh ci/scripts/knowledge_check.sh .` 实测
KC_RC=0）。在 **job 隔离副本**（设备上非 git 的 repo 拷贝，不进 PR）把两处调用降级：

```python
# 本地写补丁脚本 -> scp 到 job 目录（/tmp 只读，E002）-> 远端 python3 执行
# 替换 'if bash "${REPO_ROOT}/ci/scripts/' -> 'if sh "${REPO_ROOT}/ci/scripts/'
# （共 2 处：knowledge_check.sh、junk_check.sh）
```

要点：
1. **`blocked_by_KC` 在真机上先看 stderr**：若有 `permission denied: bash`，是设备环境，
   不要去改 knowledge/（那会被误导进错误方向）。
2. 修复只改 job 副本：网站 CI 在 Linux worker 上有 bash，PR 内容保持原样，不违反
   "不改基础设施"边界。
3. 远端执行复杂命令（sed 多命令/引号嵌套）在 toybox sh + PowerShell 双重转义下极脆，
   统一走"本地写 python 补丁脚本 → scp 到 job 目录 → ssh python3 执行"。

## 证据

libltc 1.3.2 shadow CI（job libltc-1.3.2-20260929）：
- r1/r2：`permission denied: bash` → KC 假性失败；
- 副本降级后 r2'：KC/JC pass（Errors: 0），门禁推进到 conan create；
- r5：全绿 exit 0（上游 make check 全过 + test_package 6 断言过）。
- 同日 libebur128-1.2.6-20260929 run exit 0，佐证间歇性。

## 关联

- E054（外来二进制首次执行被弹窗阻止）、E087（HMDFS 无执行位）同族，但本条特征是
  **系统路径 ELF 间歇漂移** 且只影响 CI 内嵌 `bash` 调用点。
- 诊断口诀：真机 `blocked_by_*` ≠ 本机门禁问题，先比对同日成功 job + 读 stderr。
