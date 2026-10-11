# fabric-completion/1.0.1 当前候选目标验证

## 源码与测试清单

上游仓库 n0740/fabric-completion 的固定 commit 为 5b5910492046e6335af0e88550176d2583d9a510。官方归档 SHA-256 为 34db5a8b207a66170580fc5c9d7521e76f3c3ee85471fa19a27718dca9a934a7。仅脚本与 README，无上游自动测试套件；上游计数 0、不适用，不能写 0/0 PASS。

新增消费者四场景：真实官方动态加载器加载 fab 后的任务补全、缓存复用、mtime 变化后缓存失效、选项补全。外部 fab 命令使用确定性业务夹具，真实产品、stat 和 bash-completion 加载器不替换。

独立鸿蒙专项一个场景：HMDFS 中文带空格任务路径、投影文件属主与进程 UID 差异下的真实缓存读写与刷新。专项与消费者分别记账，不因重复执行增加分母。

## 历史 r006 真实结果（保留原绑定）

| 项目 | 实际执行 | 结果 |
|---|---:|---|
| 上游 suite | 0 | 无套件，不适用 |
| 新增消费者 | 4 | 4/4 PASS |
| 鸿蒙专项 | 1 | 1/1 PASS |
| 官方本地 CI setup/build_and_test | 2 阶段 | 均 RC0，L0/L1 通过 |
| 独立事务 validator / release / postrelease | 完整 receipt chain | PASS，所属运行进程 0 |
| 官方 finish 聚合 | 1 | RC1，不能声明整个 finish 成功 |
| 平台 CI、AI Review、提审 | PR #14830 | 由当前 HEAD 的远端证据另行判定 |

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

## 当前 r008：真实默认 Bash 入口修复验证

- 平台原失败：build96648/request110009，conan-build-test log502403 的真实
  `FileNotFoundError: bash`；不是 Worker 桥接失败。
- 新 run：fabric-completion-formal-1.0.1-20261011-r008，endpoint 10.62.201.39:2222，
  boot c8f5a02e-8cae-45cd-b01e-16e605736c45，UID20020084。
- 被测 tree：9fc400a7a87436a6b30034e6a07bc47a4d22a4dd；配置 SHA-256
  cf3731ab26d51325ad80720b3d8881d1d936557c2aebe7e2082c3a2219f342bf。
- 无显式 Bash conf，真实 buildenv CONFIG_SHELL 进入生产和消费者的
  VirtualBuildEnv 上下文。原 Conan create RC0，消费者4/4、Harmony1/1。
- 原官方 setup/build_and_test RC0；官方生成 marker SHA-256
  324584847b84ae087e9fc50ad4e57b4830797ec849e97d2247674977d496b02b，
  对应原日志 SHA-256 989b5f6ccb33aac393766ebb9814a7bb337c0d1d45bf2be4b773b4ff7da11eca。
- 独立完整输入、WAL/receipt-chain、唯一launch、own0与release/postrelease核验，
  observed.json SHA-256 d1f25087f6e9fb91e3f7d625c3de0283e42c79236de23258eae57f74fca1507f。
  原日志位于 fabric-default-bash-evidence-oct11-r648，完整索引在独立观察对象。
- 整体 finish 聚合 RC1 保留（全局知识字段与既有归档收尾要求），不声明其全部通过；
  软件配对草稿和 Pre-PR 单独核验。上游仍无自动套件；新增默认入口控制未增加产品分母。
- 预启动 r007 已只读确认 launch0/prepare0、没有 work/runner/receipt；因冻结 profile
  哈希计算顺序错误退役。输入和本地历史保留，r008 fresh transfer/readback后唯一启动，
  未追认 r007 为通过。本地目标结果不能代替新提交后的平台 CI 或提审。
