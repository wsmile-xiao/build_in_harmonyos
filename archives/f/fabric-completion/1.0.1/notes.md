# fabric-completion 1.0.1 适配修复（未提审）

上游未发布 tag；1.0 是主线已有的规范版本，1.0.1 是同一官方 commit 的适配修复后缀，不宣称新上游 release。

主线 1.0 安装名 fabric-completion.bash 不是 fab 命令的自动加载候选。官方 bash-completion 2.16.0 实际加载器复现原安装无法加载；改为 fab 后任务/选项补全可执行。本版保留 1.0 全部文件，新增独立版本，消费者从静态字符串检查改为执行真实补全逻辑；外部 fab 命令用确定性测试双，不替换补全产品。

上游固定归档只有脚本和 README，测试入口数 0。当前正式 Conan 真机事务 fabric-completion-formal-1.0.1-20261006-r006 已完成：消费者四个场景 4/4，HMDFS 投影属主/中文带空格路径专项 1/1；release/postrelease 与冻结 validator 均 PASS。这不是平台 CI 或提审 PASS。

正式 r001 失败时产品打包成功，但 Conan 的 test_package 未执行 source()，导致真实官方加载器缺失。将哈希绑定的加载器获取移入 build() 后，用全新 r002、独立目录和 fresh transfer 重新验证；未修改或重放 r001。

正式 r006 RREV=0bac9ea68058a305c4089cce0645cf90，PID=6b129b068851896169fae42d399fa922d239ce8a，PREV=04d6d1522ce0e10f0e217f89d0877088。输入、原始日志、完整 WAL/receipt 和哈希回读保存在任务自有 w3-fabric-formal-r006；没有上传制品仓。历史 r002 证据不删除、不追认为当前输入。

官方本地 CI 的 setup.sh 与 build_and_test.sh 均 RC0，实际 L0/L1 通过；其再次运行相同消费者与专项，不重复计数。官方生成 `.ci-result.json` 的原始字节 SHA-256=f7ac113965c817025fe2fdb4806568e998bd839706803527d5a658f7ca974169，日志 SHA-256=bcc9124e9b076466774952254b9891c2b202ec7bae87639e4dfb5f8fce1a5d0b。完整 finish 聚合 RC1：主线 E219/E253/E305 缺字段、旧 packaging/staging/test-report 收尾要求尚未满足。没有手工制作成功 marker 或修改官方结果。

收尾中实际发现 export_sources 静态入口检查及 test_package 执行入口要求；当前配方使用实际 export_sources() 和 self.run(..., env="conanrun")，不通过豁免或空壳测试迎合检查。脚本与配置 CRLF 仅在哈希绑定的任务私有执行副本转为 LF；候选框架没有被修改。

源码修改清单：两个 stat 格式参数从字符串内嵌单引号改为无引号的单 token %Y/%m。W3 r004 的真实 OHOS 日志中，Toybox 管线保留 `'2000000010'`，导致 `[[ ... -gt ... ]]` 报 arithmetic syntax error，缓存不失效。变量展开不会重新解释 shell 引号；不能依赖后续 xargs 偶然剥掉引号。本轮直接修复源码，目标验证后由 refresh-patch --auto 生成补丁，不手写补丁。
