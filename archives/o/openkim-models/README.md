# openkim-models — OpenHarmony 编译档案

## 软件简介
openkim-models 是 OpenKIM 项目的势模型集合（发行版本 2021-08-11）：
34 个模型驱动源码目录（`model-drivers/`，C++ 驱动，上游由 KIM-API 的
collections-management 编译）、445 个 portable-model 参数集
（`portable-models/`）、96 个 simulator-model 定义
（`simulator-models/`），共 4228 文件。**纯数据包**：无编译、无链接
（Debian 亦以 all 架构分发，安装到 `/usr/share/openkim-models/`）。
许可证为 CDDL-1.0。

## OHOS 适配要点
- 纯数据包（lebiniou-data/kicad-demos 同款范式）：`build()` 仅做防漂移
  清单校验（3 目录逐目录计数 + 根标记文件），`package()` 将集合树原样
  复制到 `share/openkim-models/`，`package_id` 清空
- 安装布局与 Debian `openkim-models 1:2021.08.11` 一致
- 消费者（KIM-API 或参数消费方）经 `KIM_MODELS_DIR` 环境变量指向本目录
- 模型驱动源码树随包分发：待 kim-api 适配 OHOS 后，消费者可按
  kim-api-collections-management 流程编译驱动插件

## 依赖关系
- 无编译/运行依赖（纯数据）
- 被依赖: kim-api 适配任务的模型数据来源（本任务为依赖项任务）

## 参考资料
- [OpenKIM 项目](https://openkim.org)
- [上游 GitHub 镜像](https://github.com/openkim/openkim-models)
- [Debian openkim-models 源码包](https://packages.debian.org/source/sid/openkim-models)
