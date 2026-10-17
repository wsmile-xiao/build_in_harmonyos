申请人：2301_80739235
队伍：天天开心
申请日期：2026-08-08
库名称：libxfixes
版本：6.0.2

## 任务来源与适配范围

本库是 OpenJ9 0.59.0（Issue #1084）Unix/AWT X11 闭包的真实前置依赖。适配官方 X.Org 6.0.2 源码，保留 libXfixes.so.3 ABI，不修改上游源码；直接依赖为 libx11/1.8.13 与 xorgproto/2025.1。

## 分类判定

按高难库四项判据复核，本库不满足高难度挑战条件：没有强绑定的 Windows/Linux 私有系统接口，没有私有编译工具链，不含汇编、闭源二进制或特殊调度；当前远端依赖图为 8 个节点，上游注册测试为 0，不能据此认定依赖链庞大或全量测试成本极高。本次新增 E331 配对知识草稿，因此最高适用前缀为【知识库扩展】。

## 当前验证证据

- Fresh W0 r14：8/8 远端节点都有 RREV/PID/PREV，binary_remote=ohpcd，info_invalid=0。
- 真机 W3 r5：同一冻结输入的 static/shared conan create、两组已安装包消费者、官方 finish 与 .ci-result.json 回读均为 RC0。
- W5：319 KV、319 MD、319 索引行校验通过。
- 独立 W4（2026-08-19 r2）：P0/P1/P2/P3=0/0/1/0；唯一 P2 是实际 X Server 运行时集成需人工确认，不阻塞配方提交。

## 知识库查重情况

已检索 knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations。E236 仅覆盖静态依赖可使用的无 .la 私有归档目录；本次问题要求保留共享 Libtool 元数据并递归修复 dependency_libs 闭包，二者不语义等价。因此新增 E331-draft-2301-libtool-la-closure，结论为 NO_EQUIVALENT_REUSABLE_KNOWLEDGE。

## 可复用说明

E331 适用于 Conan 依赖发布 .la 元数据且其中保留旧缓存路径的 Autotools/Libtool 消费者。方案在当前构建目录建立递归 shadow，复制声明的库文件并重写完整 .la 闭包，禁止修改共享 Conan 包缓存。静态依赖不需要 Libtool 元数据时仍优先复用 E236。

## 远端查重与冲突边界

contrib 全状态存在三条相关记录：我方 libxfixes/6.0.2 已领取；大小写别名 libXfixes/6.0.2 待领取；他人 libxfixes/6.1.0 正在进行中。PR #5559 对应他人 6.1.0，当前仍开放且 CI 失败。不得重复领取或导入；#5559 冲突解除前不得 push 或创建新的 libxfixes PR。
