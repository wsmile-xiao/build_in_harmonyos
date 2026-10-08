# 原生构建与真实账户、认证、权限转换能力必须分阶段验证

状态：草稿。软件功能仍 FAIL；该知识是证据支持的新能力边界，不是豁免。

## 真部署安全拒绝与正向认证必须分开统计（2026-10-08）

不能把“预期权限能力不可用”混进解析消费者的失败，亦不能把任意非零冒称安全行为通过。明确只测实际受限部署的产品保护时，应先核对真实平台、UID/EUID、安装模式和真实NSS，再要求对应原控制流的精确退出码/诊断，保留正常认证和身份转换的独立缺口。

fresh r010 以正确官方6.8.2五补丁生产配方执行真实Conan create RC0，原CLI解析3/3；新增独立Harmony案例实际证明HarmonyOS、非root UID=EUID20020084、已安装0755签名ELF，并调用原普通`-n`执行接口。该域无self passwd，真实RC1与精确`doas: no passwd entry for self`相符，安全行为1/1。没有修改账户/权限/认证/系统服务，没有提供permit/nopass策略，也没有执行提升身份命令。

`doas-security-conan-observed-oct08-r010.json` SHA256 `8bf71e0e983ba1f43b8fc95f9b7f512f884a3959cd149d89974764f9dea52673` 绑定实际产品及消费者输入、唯一launch、完整原WAL/receipt和release/postrelease own0。Windows最低oracle检查拒绝RC126和不相干认证诊断；测试目标上的安全拒绝不能追认历史失败或替代正向认证、shadow后端、SUID及真实有效身份转换，它们仍未证明。

适用：本来会根据真实部署模式或NSS状态拒绝普通执行的权限敏感工具。只有“未授权不执行”的具体产品约束可以作为独立安全测试；不适用把命令没运行当成功认证、把虚构账户/逻辑OSAccount当内核身份、或把非预期signal/loader错误当预期拒绝。

## 现象与通用触发特征

程序已原生编译、签名并能够输出 usage，而配置检查报 `no passwd entry for self`。若使用“有二进制、能显示帮助、最后 shell 返回成功”作为统一结果，会把尚未到达解析器或认证后端的失败当成通过。这一模式适用于真实 UID→账户→认证→有效身份转换的工具，不依赖某个库名或路径。

## 精确根因

必须分别证明三种能力：当前进程 UID 能被真实 passwd/NSS 解析；实际后端能够正/负认证该账户；部署模式与系统策略允许受控有效身份切换。SSH/HDC 连接、数值 UID、进程 capabilities、配置 permit 行和 0755 非 setuid 二进制都不证明这些能力。

本次官方 OpenDoas 6.8.2 原生 configure 未指定 --target/--host，make -j1 RC0，签名 ELF 的 usage 真正通过；好/坏配置 `-C` 实际都 RC1，stderr 为 `doas: no passwd entry for self`。UID/EUID20020084 无命名账户，0755 程序未 setuid-root，因此解析、认证与权限转换均未达到，整个事务是 FAIL。

## 可复用修复与决策步骤

1. 读取真实 UID/EUID/GID、getpwuid 是否成功、部署模式与相关策略，不读取或传输凭据。
2. 对 parser、正/负认证、有效身份转换分别保存真实命令、RC 和输出，明确最深到达阶段。
3. 原生 OS 识别失败时修源码中的真实 OS 分支；不强制 Linux target、不从另一 libc 收割 config.h。
4. 环境能力不足时保持 fail-closed，不伪造 passwd、认证、UID 或 PASS。由环境所有者提供受控命名账户、真实认证后端和已授权的权限部署后，以全新事务补测。

## 验证与新增知识增量

`doas-native-observed-r001.json` SHA256 `f1a7b4ff301008cf74d262adc8f3318934b90feae7a67d74a26c4a044322c809` 独立复算同 r003 输入、命令 RC、日志哈希、完整 WAL/receipt 链、唯一 launch、真实 FAIL 与 release/postrelease own0。证据核算通过不代表软件通过。旧 PR HEAD `51aa67700a9889741ac8118b6606ff37e5876419` 仅身份上下文，探索源输入有独立哈希，不能追认为旧或新生产 tree 的 W3。

查重已覆盖 graph/drafts/doc/operations。只有 socket-wrapper 草稿的 NSS ABI/伴随库介绍命中，未覆盖本次“原生构建 PASS 与真实账户/解析/认证/权限转换 FAIL”的阶段到达性结论。新增的是可跨工具复用的证据决策，而非复述包介绍。

## 范围与安全边界

### 本轮新增消费者反例

共享 `/data/service/hnp/bin/bash` 硬编码并非程序运行需求。改用 Conan 实际 Python 启动探针、将已安装 ELF 解析为绝对路径并直接作为 subprocess argv 执行后，fresh r005 仍是实际 1/3：usage通过，但两项有效/无效配置都在账户查询处 RC1，未到 parser，认证与权限转换false。独立 `doas-native-observed-r005.json` SHA256 `49cdd0509c6eca76c38913be69dc8f2dafffde6329e3a61ced72facb19f14a66` 绑定真实二进制、各命令输出、唯一launch及release/postrelease own0。

这个反例把启动器缺陷与真正功能能力缺失分开：纠正 shell 依赖不能提供命名账户或 SUID。真实官方 refresh-patch 四补丁已逐文件重放35源码、与原生测试输入字节一致；源自包含成功也不能替代真实认证或权限转换。

进一步正式 Conan r006 已真实完成原 configure/build/sign/package，RREV/PID/PREV 和产品 ELF 已绑定，消费者仍仅真实1/3；有效和无效配置在 `no passwd entry for self` 处返回1，最终 create RC1。独立 `doas-formal-conan-observed-r006.json` SHA `55478cfd151c0ddcd9e8d72755ba29d7b1db80ce13c0b33e41b03cf2044506a5` 保存了这个反例：生产构建／打包可自包含，但功能、认证、权限转换仍不能宣称完成。官方 graph/doc 校验器输出0项不意味着 drafts 已被校验；实际 Pre-PR 的 draft路径、配对、draft:true、候选对象一致性才是对应入口，目前完整Pre-PR仍因真实功能失败而阻塞。

适用于真实使用 passwd/NSS 的权限工具、策略守护程序；不适用于把 numeric EXTERNAL 协议认证强行等同 NSS 的情况。不得自动改系统账户/权限/服务、自动 setuid 部署或绕过认证。不得跨 UID、boot、run、transport 拼证据。

## 执行拒绝不能冒充预期语法拒绝（2026-10-08）

新增真实反例：HDC UID2000具名shell域三命令均目标RC126/Operation not permitted，传输RC0不表示执行成功，0/3保留。仅检查invalid-parser非零，会错误接受这类前置拒执；未出现一个已知getpwuid错误也不能证明到达parser。

可变候选已将非法配置判定收紧为原parse.c yyerror真实`doas: syntax error at line N`及原配置失败RC1同时满足，并保留实际argv/输出记录。合法-C仅解析`permit 0`，不关闭密码认证、不执行提权。最小本地6/6 oracle检查和真实保存的HDC拒执判FAIL，证据`doas-consumer-oracle-directed-oct08-r001.json` SHA c9d81f71c0e3f9564a972915661296c1e196d141aa7840d59fa70b6110893d27。它不是新target执行或账户/认证/SUID PASS；旧r006等冻结输入和失败计数未改，当前新消费者仍待真正功能环境fresh验证。

通用步骤是按原被测接口要求同时绑定错误类别、退出码和参数；不能把任意nonzero当负例成功，也不能凭排除单一已知错误推断阶段到达。该签名只适用于此原parser，其他程序须读其真实错误接口。

## 纯语法模式不得初始化未使用的账户能力（2026-10-08）

精确源码显示getopt实际先于mygetpwuid_r；问题不是“getopt前查账户”，而是纯`-C file`也在进入checkconfig前初始化未使用的账户/groups。原checkconfig先真实setresuid(uid,uid,uid)降权，再原parseconfig；argc0直接exit0，未调用permit或使用groups。带命令的-C才真正使用账户/组和策略。

在Harmony/OHOS窄guard下，仅confpath且argc0提前调用同一原checkconfig，保留真实UID/drop失败、原语法错误和fail-safe出口。-s冲突、-u解析、带命令-C及普通执行均保留原检查；不模拟账户、不nopass、不改变密码或系统权限。这是模式所需能力的最小初始化边界，不是给认证路径降级。

新独立r008真实configure/build/sign0，当前production probe在同目标3/3：合法-C RC0、非法-C RC1且原syntax error、usage RC1。带命令-C及普通-n执行仍各RC1/no passwd entry for self；不是正负认证或身份转换PASS。完整原WAL/receipt、唯一launch1及release/postrelease own0：doas-native-pure-syntax-observed-r008.json SHA4958deb65de433b544be37d90c540346426734035ad6a0182df3730ef540b125。新的doas.c第五补丁原官方refresh+1/1精确字节回放已绑定r008源；a1d27c21dff204ddab9520456a7eeaa044c4bc6e4c4e5c96ea02143e465b1d8a是doas-official-refresh-oct08-r004/result.json的SHA。旧四补丁不重复，旧r006/HDC失败未追认。

可复用判据：先读原模式控制流，证明身份/权限状态在此模式不用，且必须保留原真实降权和参数拒绝。只延迟该独立纯解析路径的初始化；凡实际执行、权限检查或策略计算所需身份不得省略。模式仍需要真实账户时不适用；本结论不能泛化为doas全功能可用。
