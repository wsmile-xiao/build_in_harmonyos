# mptp 0.2.5 原生测试报告

官方源码归档 SHA256：ffb3714abb9530c253593b4434c95a3ab6c818340f2f9c829c646ed26c52141d。
归档 Makefile.am 无 TESTS/check_PROGRAMS，无注册测试目录，上游分母 N=0。
新增安装消费者 8/8：版本、帮助、single ML、multi ML、SVG、重复界定、
MCMC、无效 Newick 拒绝；不是上游测试。

目标：OHOS 6 arm64 / Clang 15.0.4，10.62.201.39:2222。
原生事务 mptp-w3-20261011T071000Z，Conan create RC0，12 项回执与清理 PASS。
原始日志 SHA256：5e6df7232e6f2454fa9dc68caa437eeb21e14d37fc5549b227acd73147cef1c1。
官方 finish 子步骤 mptp-finish-w3-20261011T074000Z：setup/build_and_test RC0，
L1e 反向验证通过，日志 SHA256：0c9397a1712eb205dbdd0f5b741c44dd253ec7331804e931f6d07ff8e6b70fbc。

以上是此前候选的原生/官方 CI 模拟结果，不代表比赛 worker CI 或发布。
本轮追加标准 apply_conandata_patches 调用（当前无声明补丁）后，已完成
mptp-scoped-finish-20261011T090200Z：正式 Conan 验证通过，官方 W3 本地
CI 模拟通过，消费者 8/8，12 项事务回执与 release/postrelease PASS。
原始日志 SHA256：0a769e37827ec2690a15beb241a7fd27c0f72268314c51eb0810f9fe25c8d54e。
生产 ELF SHA256：5daa586726183e989f389e0ee46bc8028e00ead329ca2e0ecb122078ebf8272a。
新配方 RREV：44d455571f9fdd274a80da24e6ab7b67。

完整 finish 的原生 RC=1，状态 PARTIAL_POST_W3；仅 step5b/step8 失败。
step5b 指向仓库既有 E219/E253/E305 缺字段及 knowledge_gained 的旧数值解析；
step8 要求旧 packaging/.staging 标记。依据当前 Conan 归档规范，未生成假文件，
不修改仓库框架或他人知识。配套草稿另行通过当前 W5 和 Pre-PR 合同验证。
ConanVerifier 的 L2/L4/L5 因 cache ID 查找失败而跳过，不能当作实际执行；
独立官方 build_and_test 的 L2/L4/L5、L1e 实际执行结果以原始日志为准。
