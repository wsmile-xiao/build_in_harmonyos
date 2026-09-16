# crazywa 测试报告

版本：0.0.0-git2019.06.13；程序自报版本 1.0.5。
官方源码：https://hgm.nubati.net/git/crazywa.git ，固定提交
`055bf038677d879e2bcccae8b6051f60af16b352`。

## 上游清单与计数单位

`git ls-tree --name-only 055bf038677d879e2bcccae8b6051f60af16b352`
输出仅为 `crazywa.pod`、`dropper.c`、`logo.png`。
无上游默认或可选测试入口。上游 N=0，PASS/FAIL/SKIP/NOT_RUN=0/0/0/0，
通过率 0/0（不适用）。没有删除、跳过或修改上游测试。

新增计数单位为 Python unittest case，N′=12。通用超时、进程退出检查和
同一 case 内多个断言不另计数。MANIFEST.yml 的 assertion_count=14 是
实质检查下界，不能与 test_case_count=12 混加。

## 新增消费者用例

| 用例 | 实际断言内容 |
| --- | --- |
| test_handshake | XBoard 协商完成、程序名称、setboard 和变体功能声明 |
| test_ping | pong 返回相同序号 |
| test_malformed_move | 格式错误输入产生 Illegal move，随后仍响应 ping |
| test_setboard | 设置初始棋子布局且黑方行棋，深度 1 搜索返回20个黑方合法走子之一；忽略 setboard 则失败 |
| test_variant_crazyhouse | 有限深度搜索完成，返回走子格式有效且无 Illegal move |
| test_variant_shogi | 同上 |
| test_variant_minishogi | 同上 |
| test_variant_judkinshogi | 同上 |
| test_variant_torishogi | 同上 |
| test_variant_euroshogi | 同上 |
| test_variant_crazywa | 同上 |
| test_variant_kyotoshogi | 同上 |

每个用例启动独立引擎进程，响应限时 15 秒；结束发送 quit 并检查退出码，
超时只回收该用例启动的进程。测试不修改 HOME 或共享配置。

## 执行方式及限制

Conan build() 在构建并签名后执行：
`python3 <exported protocol_test.py> <build_folder/crazywa>`。
Conan test_package 的 test() 在 conanrun 环境执行：
`python3 <test_package/protocol_test.py> <package_folder/bin/crazywa>`。
两阶段执行同一套 12 个用例，不重复计数为 24。

八种变体仅检查有限深度协议响应及输出格式，不等同于完整棋规、棋力或
长时间对局验证。未运行 XBoard 图形界面。最初的 e2e5 拒绝测试假设有误：
上游 ParseMove 解析走子编码，并非完整合法性检查；修正为 malformed input
用例，未更改上游行为。

正式验证结果由当前提交的 Conan/W3 原始日志、结构化报告和独立 W4 对账确认。
设备 W3 使用哈希绑定的工作目录工具副本；线上 CI 使用服务器脚本，分别报告。

## 实跑结果

2026-09-12 设备实跑：Conan 构建后、安装后的 test_package 以及 W3 中的
同一套测试均为 12/12（100%），每阶段 PASS/FAIL/SKIP/NOT_RUN=12/0/0/0。
重复执行不改变 N′=12。上游仍为 0/0（不适用），没有可运行但未执行的上游套件。
每轮具体 HEAD、Conan 完整包引用、日志原件及工具副本哈希由独立验证回执绑定；
设备验证通过不代表线上 CI 或赛事审核通过。
