# bbe — OpenHarmony 编译档案

## 软件简介
bbe (binary block editor) 是类似 sed 的二进制文件编辑器，支持正则匹配和块操作。

## OHOS 适配要点
- 2006 版 config.guess/config.sub 需要更新（添加 aarch64 + HarmonyOS 支持）
- config.status 临时目录需使用 TMPDIR（HMDFS 不支持当前目录创建临时子目录）

## 依赖关系
- 无外部依赖

## 参考资料
- [bbe 官方](https://savannah.gnu.org/projects/bbe/)
