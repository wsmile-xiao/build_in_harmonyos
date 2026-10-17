# deltarpm — OpenHarmony 编译档案

## 软件简介
deltarpm 是创建与应用 delta RPM / delta ISO 的工具集 (makedeltarpm、applydeltarpm、
combinedeltarpm、makedeltaiso、applydeltaiso、fragiso)，用于 RPM 生态的增量更新。

## 功能概述
- makedeltarpm：由新旧两个 RPM 生成 delta RPM
- applydeltarpm：由 delta RPM 还原新 RPM
- combinedeltarpm：合并多个 delta RPM
- makedeltaiso / applydeltaiso：ISO 镜像的增量生成与还原
- fragiso：ISO 镜像分片 / 组装 / 校验

## OHOS 适配要点
- 纯 Makefile 项目，无 configure；显式构建 6 个不依赖 librpm 的工具
- rpmdumpheader 需链接 librpm（rpm/6.0.2 未发布），本配方跳过该二进制
- lzma/5.6.2 由 Conan 依赖提供（包名仅 ohpcd 有，解析确定，自带完整头文件与静态库）；bzip2 1.0.8 / zstd 1.5.6 改从官方源码树内静态构建（双远端下其普通版本号会被解析到 conancenter 的 CMake 配方，在 OHOS 上无法配置）；zlib 使用上游自带的 rsyncable 副本树内静态构建
- 上游无测试套件；test_package 以 2 个行为冒烟脚本对 6 个二进制做 usage/诊断断言

## 依赖关系
- lzma/5.6.2（Conan，已发布）＋ 树内构建的 bzip2 1.0.8、zstd 1.5.6（官方源码，sha256 校验）

## 参考资料
- [deltarpm 上游仓库](https://github.com/rpm-software-management/deltarpm)
- [deltarpm README](https://github.com/rpm-software-management/deltarpm/blob/master/README)
