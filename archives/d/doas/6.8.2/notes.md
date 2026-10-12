# OpenDoas 6.8.2 当前候选边界

版本、目录、配方和源码键均以官方 v6.8.2 为准，不沿用错误的 6.9.3 任务号。
官方归档 32430 字节，SHA-256：
`6da058a0e70b7543bc60624389b0b00b686189ec933828c522bf8b2600495a67`。
历史候选基于 main `b95978a4750e7aa9a3d49af148bb3bbedf81051d`；正式r017冻结基线HEAD为`90d463d02bf88e430970507d512159fca8a279ba`。

2026-10-06 只读目标诊断观察到 UID/EUID/GID 为 20020084，passwd
枚举中无该 UID 的命名账户。上游 doas.c 在 -C 配置解析前即要求
getpwuid_r 返回账户；普通执行还要求 effective UID 为 0。0755 文件和
doas.conf 规则不能创造这些权限。随后独立 native r005 和正式 Conan r006
均已真实构建／签名；r006 四个官方补丁重放、configure、完整 build、package
实际 RC0，消费者 usage 通过，而有效／无效 `-C` 均在解析前返回
`no passwd entry for self`，实际 1/3，整体 FAIL。没有认证或权限切换 PASS。
只读诊断、构建与打包不能替代功能测试、W3 完整通过或当前 HEAD 平台 CI。

正式独立证据：`doas-formal-conan-observed-r006.json`，SHA256
`55478cfd151c0ddcd9e8d72755ba29d7b1db80ce13c0b33e41b03cf2044506a5`。
该记录已验证完整 WAL／receipt chain、真实消费者命令及 release/postrelease own0。
当前元数据纠正仅表述这些真实终态，不变更配方、补丁、二进制或在途事务。

旧 probe 对缺账户返回成功 RC，但实际三个断言都未执行。当前候选已改为
真实失败，不伪造账户、不删除认证检查、不改变系统账户或系统服务。
保留旧 #14112 和分支证据，尚未创建新任务或 PR，也未提交、推送、提审。

2026-10-08 新mutable源只在Harmony/OHOS的纯-C/argc0路径提前原checkconfig：
真实setresuid降权、原parseconfig和exit保留，组/账户数据在该路径不用。
带命令的-C及普通执行仍执行原mygetpwuid/groups/策略/认证/SUID检查。
fresh r008原native build与当前生产probe真实3/3；带命令-C和普通-n仍
原no passwd entry RC1，认证/权限false。唯一launch和正常release/postrelease
own0已核算：doas-native-pure-syntax-observed-r008.json SHA
4958deb65de433b544be37d90c540346426734035ad6a0182df3730ef540b125。
它只证明解析修复，不追认原r006整体FAIL，也不是新正式Conan/完整功能PASS。
第五源补丁由原官方refresh生成并1/1精确字节回放；其他四补丁未重复：
doas-official-refresh-oct08-r004/result.json SHA
a1d27c21dff204ddab9520456a7eeaa044c4bc6e4c4e5c96ea02143e465b1d8a。
前次r003输入选择误猜归档根名的KeyError保留，官方生成未执行，未写生产patch。

当前conandata仅声明五项官方patch。目录另有Oct06 00:46早期三项未声明
历史patch，仍原字节保全、不删除/改写、不应用。新未消费formal r009
输入选择已从错误glob文件数改为精确声明集合5项，只冻结/传输这些patch；
它不是新的构建、消费者或认证结果。r009仍freeze/transfer/launch0。

## 当前实际结果与安全边界（2026-10-08，r010）

以上r009状态为历史记录，不代表当前终态。正确官方6.8.2五补丁候选在
独立r010真实执行Conan create RC0；已安装ELF的CLI合法纯-C、非法纯-C
和usage三项实际3/3。独立Harmony部署保护案例实际HarmonyOS、非root
UID=EUID20020084与0755部署，普通-n命令真实RC1，精确stderr为
`doas: no passwd entry for self`，安全拒绝1/1。产品检查合计4/4，不能
替代真实正向认证、shadow后端或SUID身份转换；原事务整体FAIL保留。

原字节日志：doas-security-conan-logs-oct08-r010/stderr，19021字节，SHA256
be32d27bf90451faaf7d97e9cb5a3308fecf05178dd9a231badbb35500082f1a。
日志实际包含HARMONY_TEST_COUNT=1与HARMONY_TEST_PASS=1/1。
独立观测doas-security-conan-observed-oct08-r010.json，SHA256
8bf71e0e983ba1f43b8fc95f9b7f512f884a3959cd149d89974764f9dea52673；
唯一launch1、release/postrelease own0，未修改账户、权限、系统或其他任务。

该候选已物化到正确版本工作树，未提交或推送。原官方finish/conan-verify
及自动.ci-result仍缺，不能手写marker或把旧CI绿绑定到本候选。
命名账户/认证/提权能力限制由主代理公开写入PR，不把不可执行项当PASS。

## 正式官方收尾与身份纠正（2026-10-08，r017）

正确版本任务14982已唯一领取，分支`feat/doas-6.8.2`，唯一OPEN Issue3656。
上文“尚未创建新任务”和“自动.ci-result仍缺”为历史阶段，并非当前结果。
新事务`doas-official-local-ci-682-20261008-r017`真实调用官方
FinishPipeline.step35_local_ci：setup0、build_and_test0、已安装消费者3/3、
OHOS安全拒绝1/1。官方成功路径自动产生marker，SHA256
3744ee4ad8f9aaacff3240e2d046d9548d8c886a52974c72a21f4398e7aae13d。
独立观察SHA256 9ffe8d34756be75a73f4fc1820a09bc672e0745a6aabd377a1565fdfb441ac92
验证唯一launch1、12回执/24WAL、release/postrelease及自有SID进程0。
这次真实成功不改写旧r010FAIL，不证明正向认证、SUID部署或权限转换。
正式原日志中的L2无version/help、L4危险函数提示及末尾cleanup裸git缺失
保持原字节和原最终RC0，不将非阻塞检查写成各项全面工具能力PASS。
提交前只更正这些描述性元数据，生产配方、五补丁、生成解析器及可执行
消费者/专项测试内容均与正式r017输入逐项SHA绑定，不重播已消费事务。
