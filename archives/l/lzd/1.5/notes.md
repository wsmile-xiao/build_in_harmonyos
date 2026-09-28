# lzd 1.5 适配笔记

## 软件信息

- 上游: <https://www.nongnu.org/lzip/lzd.html>（Antonio Diaz Diaz；
  lzip 格式教学解压器，492 行单文件 C++98）
- 版本: 1.5（Savannah 官方发布）
- 任务: ohpcd（领取时无人认领、无 PR 记录、仓库未收录）

## 编译环境

- 真机: 10.195.180.238（隔离 job `device-b/lzd-kb-20260920`）
- 构建系统: 自研 configure + Makefile.in（非 autoconf，无 libtool）
- 状态: built

## 上游测试清点（R51 第 1 步）

| 清点项 | 结果 | 依据 |
|---|---|---|
| testsuite/check.sh | 真实上游测试 | 解压 fox.lz 10 个变体 + em.lz 与 test.txt 比对 |
| 运行方式 | make check（build() 内执行，L1c） | Makefile.in check 目标 |

## 验证结果（真机实测后回填）

- conan create: 退出码 0
- 上游: make check 在 build() 内执行（L1c）
- 消费者: **3/3 通过**（fox-decode OK / em-decode OK / negative-control OK）

## 注意事项

- PR 前缀【知识库扩展】；分支 feat/lzd-1.5
- CLI 工具：软件级 commands.json（archives/l/lzd/commands.json）已按 R38 声明
