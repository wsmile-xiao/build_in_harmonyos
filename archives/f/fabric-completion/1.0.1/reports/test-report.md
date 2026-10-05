# fabric-completion/1.0.1 当前候选目标验证

## 源码与测试清单

上游仓库 n0740/fabric-completion 的固定 commit 为 5b5910492046e6335af0e88550176d2583d9a510。官方归档 SHA-256 为 34db5a8b207a66170580fc5c9d7521e76f3c3ee85471fa19a27718dca9a934a7。仅脚本与 README，无上游自动测试套件；上游计数 0、不适用，不能写 0/0 PASS。

新增消费者四场景：真实官方动态加载器加载 fab 后的任务补全、缓存复用、mtime 变化后缓存失效、选项补全。外部 fab 命令使用确定性业务夹具，真实产品、stat 和 bash-completion 加载器不替换。

独立鸿蒙专项一个场景：HMDFS 中文带空格任务路径、投影文件属主与进程 UID 差异下的真实缓存读写与刷新。专项与消费者分别记账，不因重复执行增加分母。

## 当前真实结果

| 项目 | 实际执行 | 结果 |
|---|---:|---|
| 上游 suite | 0 | 无套件，不适用 |
| 新增消费者 | 4 | 4/4 PASS |
| 鸿蒙专项 | 1 | 1/1 PASS |
| 官方本地 CI setup/build_and_test | 2 阶段 | 均 RC0，L0/L1 通过 |
| 独立事务 validator / release / postrelease | 完整 receipt chain | PASS，所属运行进程 0 |
| 官方 finish 聚合 | 1 | RC1，不能声明整个 finish 成功 |
| 平台 CI、AI Review、提审 | 尚无新 PR | 未完成 |

## 哈希绑定和范围

- run_id：fabric-completion-formal-1.0.1-20261006-r006；唯一 launch，未重放。
- 端点：10.62.201.39:2222；boot_id：847be69b-cf79-4dd3-be21-ae24c000e93a；UID：20020084。
- 配置 SHA-256：95937a335a165346f4c76f83f5abfe4f92348c0e37a991dae5e6ca312189ce2e。
- 测试时 candidate tree：4e57ddf52fd478981e8e6902089625b86df880dc。后续本文及知识说明属于元数据，不能把旧 tree 当作未来提交 tree。
- snapshot-009 SHA-256：315b225331df7c3260a4ab83b8dfc769415c8fc07bb1ce6a21961027c8efad03。
- 当前 RREV：0bac9ea68058a305c4089cce0645cf90；PID：6b129b068851896169fae42d399fa922d239ce8a；PREV：04d6d1522ce0e10f0e217f89d0877088。未上传制品仓。
- 原始证据根：F:/HarmonyPC/pr-review-closure-20261004-r1/w3-fabric-formal-r006。
- 已独立哈希核验的导出索引：F:/HarmonyPC/pr-review-closure-20261004-r1/fabric-official-finish-evidence-r006/provenance.json。
- 官方生成 CI result 原始 SHA-256：f7ac113965c817025fe2fdb4806568e998bd839706803527d5a658f7ca974169；其日志 SHA-256：bcc9124e9b076466774952254b9891c2b202ec7bae87639e4dfb5f8fce1a5d0b。

原始运行日志保存在候选之外，不把 `.log` 或改扩展名的日志放进 PR。失败 r001/r003/r004/r005 全部保留，各 successor 独立输入、根、receipt 和唯一 launch。聚合 RC1 中主线知识字段及旧收尾目录要求不能通过空 marker 或伪打包解决；当前修复任务身份、最终知识查重、两阶段 Pre-PR 仍需完成。
