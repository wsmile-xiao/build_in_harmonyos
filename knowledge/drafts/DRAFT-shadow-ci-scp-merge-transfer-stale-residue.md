# DRAFT：真机 shadow CI 的 scp -r 是"合并"不是"替换"——旧 job 残留会污染包目录

> 来源：simh/3.8.1 真机验证 2026-09-27（job `simh-3.8.1-shadow-20260927-134801`）

## 现象

scp 传输退出码 0、"传输成功"；但设备端 `find` 出来的文件数（14）大于本地（8）。
多出的是**上次运行**的产物，不是本次传输的内容。

## 根因

`scp -r local remote_dir/` 的语义是**逐条目合并**：同名文件覆盖，旧目录里多出来的
文件/子目录原样保留。真机 job 的 repo 常来自 `--repo-source` 复制的旧仓库或上轮
运行现场，包目录里早有东西。本次实测残留两类：

1. `3.8.1/__pycache__/conanfile.cpython-312.pyc` —— 本地导入配方（harness/静态检查）
   时 Python 生成，随 scp 一起带上去；
2. `test_package/build-release/conan/*.sh` —— 设备上**旧版草稿**此前跑 conan 留下的
   Conan 生成物（新 scp 只覆盖同名文件，不会删除这些目录）。

危害：a) junk_check/JC 门禁可能因包目录多文件而 fail；b) test_package 混入旧构建
产物，测试不可复现；c) 只看 scp 退出码会得到"传输成功"的错觉——缺文件同样不会报错。

## 处置（传输三步，缺一不可）

```sh
# 1) 清理：只对"当前 job 内精确包目录" rm -rf（展开绝对路径核对后再执行，
#    遵守避坑指南 9.2：绝不对计算出的上级目录递归删除）
ssh ... "rm -rf '$JOB/repo/build_in_harmonyos/archives/x/<pkg>/<ver>'"

# 2) 传输
scp -i ... -P 2222 -r "$LOCAL/<pkg>" "$H:$JOB/repo/build_in_harmonyos/archives/x/"

# 3) 核对：设备端清单与本地逐项一致（数量+路径）才允许跑 runner
ssh ... "find '$JOB/.../<pkg>/<ver>' -type f | sort"   # diff 本地清单
```

本地前置：任何 import 过 `conanfile.py` 的静态检查/单测之后，先删 `__pycache__`
再打包传输（或确认其被忽略且不进 scp 源目录）。

## 备选

单 tar 归档传输、解包到全新目录：tar 解包不具"合并残留"语义（目录是空的），
天然规避；但注意避坑指南 9.3 的文本管道破坏 tar 坑（用 scp 传 .tar 文件或 base64，
不要用 `tar -cf - | ssh` 文本管道）。

## 实测证据

- 首次传输后：设备端 14 个文件（本地 8 + 残留 6）；
- 清理两处残留后复传核对：8/8 逐项一致；
- runner 全绿（L0-L5 pass）；若未清理，JC/L0 有被污染的现实风险。

## 查重边界

- 避坑指南 9.3：文本管道**破坏 tar 字节流**（传输损坏）——失败面不同；
- 避坑指南 9.2：覆盖删除的**安全路径约束**——本条复用其约束，补"合并语义 + 清单核对"流程；
- 全库检索 `scp` / `残留` / `stale merge`：无既有条目覆盖此失效模式 → 独立新条目。
