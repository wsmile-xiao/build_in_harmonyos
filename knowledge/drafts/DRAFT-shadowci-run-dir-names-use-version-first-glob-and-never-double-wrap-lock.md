# DRAFT-shadowci-run-dir-names-use-version-first-glob-and-never-double-wrap-lock：真机 run 目录命名是 codex-<版本>-…（监控 glob 必按此写），且 run-conan-heavy.sh 勿再外包一层锁

> Status: **Draft**（待审核 promote）| severity: `P3` | category: `process` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-shadowci-run-dir-names-use-version-first-glob-and-never-double-wrap-lock.kv`

---

**匹配关键词**：ohos-test-runs 目录名, codex-<版本>, --lib basename, run-conan-heavy.sh 双层锁, 监控 glob, 排队监控

## 错误签名（error_signature）

```text
ls -dt "$HOME/ohos-test-runs"/codex-<库名>-*/   # 返回空 → 误判"runner 没建 run 目录就退了"
```

## 错误摘录（error_excerpt）

```text
# 实际目录名（--lib 拿到的是 basename(CI_PACKAGES)=版本号）：
codex-1.2.0-libshrinkwrap-1.2.0-20260927-conan-20260927-154804-51958
# 用 codex-libshrinkwrap-* 去匹配 → 匹配不到 → 误诊为"静默失败、无 run 目录"
```

## 根因（root_cause）

run-conan-heavy.sh 里 `--lib "$(basename "$CI_PACKAGES")"`：CI_PACKAGES 形如
`archives/l/libshrinkwrap/1.2.0`，basename 取到的是**版本号**。runner 拼出的
run 目录是 `codex-<版本>-<库名>-<task>-<时间戳>-<pid>`。排查时按"codex-<库名>-*"
glob 找目录会扑空，把一次正常启动（甚至失败原因明确的 run）误判成
"runner 未创建 run 目录"，浪费一轮诊断。

第二个相邻坑：run-conan-heavy.sh **已经内置** ohos-test-runner.sh（heavy 模式
默认拿全局锁）。若再按文档示例外面包一层 `ohos-test-runner.sh --lock -- sh
run-conan-heavy.sh`，外层 mkdir 锁目录成功后，内层再 mkdir 同一锁目录必然失败
——轻则排队语义错乱，重则互相等待。

## 推荐方案（rec_approach）

1. **直接执行** `sh "$JOB/run-conan-heavy.sh"`，不要再外包 runner/锁；
2. 监控/查日志的 glob 一律用 **`codex-*<库名>*`**（或先 `ls -dt
   "$HOME/ohos-test-runs"/ | grep <库名>`），不预设字段顺序；
3. 需要传 runner 级参数（--path/--python 等）时，改写 job 的 run-conan-heavy.sh
   或 env.sh（job 本地），而不是外面包层。

## 复用价值

所有做真机 shadow CI 监控/自动读数的会话都受用；一次误诊的直接代价是一轮
"假性失败"诊断。查重：nift 草稿讲 inode 隔离策略、zlib/E540 讲工具 PATH，
均未覆盖 run 目录命名与双层锁（2026-09-27 图谱 0 命中）。
