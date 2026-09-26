# lebiniou-data — OpenHarmony 编译档案

## 软件简介
lebiniou-data 是 LEBINIOU（le biniou）音乐可视化程序的数据包：1415 个
GIMP 调色板 colormaps（`.gpl`，每文件 256 行 RGB）、图像主题 images（115
PNG + 8 JPEG，含 covid-19/oliv3/opale95/zebulon 四个主题目录）、8 个路径
轨迹 paths、15 个序列定义 sequences/json、Vue 前端资源 vue（index.html +
css/img/js/media/sequences 共 163 文件）与测试素材 test。**纯数据包**：
无编译、无链接（Debian 亦以 `all` 架构数据包分发，安装到
`/usr/share/lebiniou/`）。许可证为 GPL-2.0-only。

## OHOS 适配要点
- 纯数据包（kicad-demos 同款范式）：`build()` 仅做防漂移清单校验（六目录
  逐目录计数 + 根标记文件），`package()` 将六个数据目录复制到
  `share/lebiniou/`（排除上游不安装的 Makefile.am），`package_id` 清空
- 安装布局与上游 autotools `$(datadir)/lebiniou/` 及 Debian 包一致
- 消费者（lebiniou 主程序）经 `LEBINIOU_DATA_DIR` 环境变量或编译期
  datadir 指向本目录使用

## 依赖关系
- 无编译/运行依赖（纯数据）
- 被依赖: 无（由 lebiniou 主程序运行时按路径消费，非 conan 依赖）

## 参考资料
- [上游仓库（GitLab）](https://gitlab.com/lebiniou/lebiniou-data)
- [Debian lebiniou-data 源码包](https://packages.debian.org/source/sid/lebiniou-data)
