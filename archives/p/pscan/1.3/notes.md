# pscan 1.3 适配笔记

## 任务
- contrib 9780,分支 feat/pscan-1.3,认领 2026-09-25
- 上游:Alan DeKok pscan 1.3(C,flex 词法,零依赖);上游官网
  (dwheeler.com/pscan、deployingradius.com/pscan)均已失效,
  源码取 Debian pool 未修改 orig.tar

## 交付物
- bin/pscan(静态扫描器)+ bin/test.c(上游自带演示输入)

## 配方机制
- tool_requires flex/2.6.4 生成 scanner.yy.c;手写编译两文件
- 平铺 tarball(strip_root=False);VirtualBuildEnv 供 flex
- 不做 strip;不做签名

## 上游测试
- 无测试套件(README 自述);消费者测试以上游自带 test.c 为扫描输入,
  断言 test.c:64/75 两处 problematic 检出 + 干净文件零告警(2/2)

## 编译结束
（设备 conan create + 消费者测试结果见 reports/）
