# 【高难度挑战】libxext 1.3.7 HarmonyOS PC 适配申请

申请人：2301_80739235
队伍：天天开心
申请日期：2026-08-20
库名称：libxext
版本：1.3.7

## 申请原因

libxext/1.3.7 是 OpenJ9 0.59.0 的 OpenJDK Unix/AWT X11 构建闭包中的真实前置依赖。适配需要在不修改上游源码、不加入 OHOS 条件宏的前提下，解决 HMDFS 上 Autotools 临时探针权限、编译器目标三元组识别，以及已发布 X11 依赖中历史 Libtool `.la` 绝对路径的完整传递闭包。配方还必须保持 `libXext.so.6` ABI，并在一台 OHOS/arm64 真机上完成 normal 与 forced-static 两组 installed-package consumers。源码、依赖和门禁证据均绑定精确 candidate tree。

## 知识库查重情况

已在 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations` 检索 XSync subtraction overflow、Libtool transitive `.la` shadow、Autotools config.guess writable temporary directory，以及 finish W3 substep / post-W3 readiness boundary。Libtool shadow与 finish 边界复用现有知识；`XSyncValueSubtract` 对精确结果和 overflow 输出的独立验证没有语义等价条目，因此随本 PR 提交 `E331-draft-2301.kv` 与同 stem Markdown 草稿。

## 可复用说明

新增知识适用于安装包消费者验证 XSync 固定宽度算术 API 的场景：普通运算应单独断言精确结果，overflow 输出应由真实边界运算独立验证，不能把历史实现对符号转换的 overflow 位直接当作结果无效。该知识不允许忽略所有 overflow，也不允许删除公共 API 调用、跳过目标测试或用源码扫描替代运行验证。复核方式是在安装后链接实际 libxext，并分别执行普通减法和最大值加一边界测试。
