【申请人账号】2301_80739235
【队伍名称】个人(2301_80739235)
【申请日期】2026/09/28（2026/10/05 更新实际验证）
【库名称】libevdev
【版本】1.13.4

## 关联 PR

- PR：!13633
- PR 链接：https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13633
- 分支信息：2301_80739235:feat/libevdev-1.13.4 → OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 当前状态：open

## 申请原因

沿用原路径 A 基础适配与路径 B 知识贡献申请。本次补充真实 SSH 原生测试、消费者以及签名 HMDFS 加载证据，纠正用源文件数量作为用例分母、把所有输入库测试当成需要设备、把通用消费者当成鸿蒙专属测试的统计错误。libinput 的实际测试还发现并修复 record --all 空设备列表崩溃，原上游参数断言不变，修复后该入口通过。

设备/VT 与可选GUI的未执行和原框架跳过如实保留。安全 CLI、构建成功和消费者检查不证明特权后台能力。

## 知识库查重情况

已检索 knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations。既有 Check TEMP 及 HMDFS projected-owner 机制直接复用，新增内容限定为当前真实失败的定位、原生框架计数、运行库闭包及平台证据分层的实质增量。完整命中和判断保存在任务证据中。

当前 PR 增量草稿：knowledge/drafts/E16331-draft-D310.kv 与同 stem .md，draft=true。保留原申请的旧式草稿作为历史，不以它代替当前草稿对。

## 可复用说明

Meson 标签与真实权限门禁、同 SONAME 发布依赖污染工具子进程、目录枚举 NULL 的错误路径，以及普通 CLI 和签名共享文件系统证据的不同分母均是跨 C/C++ 库及守护工具的机制。每个条目都给出触发条件、根因、修复方式、原断言验证和非适用边界，不承诺后台设备能力。

## 当前验证

具体计数、测试构建适配、日志哈希及限制见对应 PR 的最终测试表。r013 上游/平台、r014 独立规则检查与 r016 同源库消费者分别保全；不跨轮次拼成整套 W3 PASS。产品 NULL-list 补丁只属于 libinput。

## 高难度重判

HD1_PRIVATE_OS_INTERFACES、HD2_PRIVATE_TOOLCHAIN、HD3_COMPLEX_ARCHITECTURE、HD4_LARGE_DEPENDENCY_TEST_COST 均 matched=false：未实现私有 OS 接口或私有编译器、无复杂架构重构和大型递归依赖构建壁垒。数量、轮次及等待不作为高难依据。有效路径 A+B，保持【知识库扩展】前缀。

## 范围边界

本申请是当前软件贡献与知识扩展申请，复用现有 Issue，不创建新 Issue。consolation 的历史不可适配记录2158描述 VT 后台限制，本次没有把它视为已解决；真实后台集成未验证。
