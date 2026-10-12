# DRAFT-tag-archive-git-version-gen-version-pin — tag archive + git-version-gen 上游的 version 文件钉版法

> 来源:onion 0.8 适配(task onion/0.8,自导入依赖任务)
> 环境:build_in_harmonyos 配方仓库;源为 GitHub tag archive;上游构建期以 git-version-gen 脚本推导版本

## 场景特征

```
上游构建脚本(git-version-gen 同款逻辑)按优先级取版本:
  ① 源根 version 文件 → ② git describe(需 .git)→ ③ DEF_VER 默认值
tag archive 无 .git:②不可用,③回退出脏版本(如 "0.8.0.GIT"),
直接弄脏 ONION_VERSION、soname 与 pkg-config Version 字段。
```

## 触发条件

- 上游用 git-version-gen(或同款"version 文件→git→默认值"三级逻辑,
  git/gnulib 系项目常见)
- 源为 tag archive(无 .git),构建期才推导版本

## 根因分析

git-version-gen 的第一优先级就是读源根 `version` 文件——这是发布
工程自带的"钉版"接口,只是 tag archive 打包时没带上。构建前写一个
单行 version 文件,即可把版本精确钉到任务号,零补丁。

## 解决方案

### 推荐方案
1. 读上游 git-version-gen 脚本头 40 行,确认取版优先级与 version
   文件文件名(一般就叫 `version`,个别项目用 `.tarball-version`)。
2. conanfile build() 在 cmake/configure 前写 `version` 文件,内容=
   任务版本号(不带 v 前缀,脚本自行剥 v)。
3. 核对构建产物:soname/pkg-config Version 字段应为干净任务号
   (WSL 预验证时 ls lib/ + cat *.pc 一步验证)。
4. 该写文件属"构建输入"而非"改上游源"(与 doas parse.c/libdbusmenu
   内嵌 shim 同类:配方资产注入,不动上游文件字节)。

### 禁止做法
- ❌ patch 掉 git-version-gen 调用(为版本号动上游构建脚本,漂移面大)
- ❌ 接受 DEF_VER 脏版本(soname 带 .GIT 后缀,消费者无法依赖)
- ❌ 事后改名 .so(破坏与安装面的对应关系)

## 验证

```bash
echo "0.8" > "$SRC/version"   # build() 内执行
cmake -S "$SRC" -B build ...  # configure 日志打印 "Onion version is 0.8"
ls inst/lib                    # libonion.so.0.8 干净命名
```

## 关联条目

- 相关:DRAFT-upstream-native-cmake-minimal-wrap(第四形态;本条是其
  在 git-version-gen 系上游的一个钉版补丁点)
- 相关:DRAFT-rolling-master-snapshot-version-and-self-soname(无版本
  上游的快照号+自定 soname;本条是有版本意图但推导链断的钉版)
- 冲突:无
