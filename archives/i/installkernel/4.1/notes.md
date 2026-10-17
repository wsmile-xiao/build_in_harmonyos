# installkernel 4.1 适配笔记

## 上游识别

- 任务卡仅给「installkernel 4.1 / C++」,url 字段为 null。全网排查结论:
  **Alpine aports main/installkernel pkgver=4.1** 是唯一对得上 4.1 的
  候选(Gentoo 版 projg2/installkernel-gentoo 标签为 v70/v69 系;
  Debian debianutils 版为 v2;GitHub 无任何 C++ installkernel 项目)。
- 任务卡 lang 标 C++ 与上游实际不符:上游为 **POSIX sh 脚本(noarch)**,
  平台 lang 字段不可靠(fabric-completion 纯 bash 同款)。
- 上游:https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/installkernel
  (Maintainer: Natanael Copa,GPL-2.0-only,`options="!check"` 无测试套件)。

## 来源与钉死

- 脚本**直接内嵌于 aports 树**(APKBUILD `source="installkernel"`,
  无独立 tarball/tag/release)。
- 以 aports commit `69a2ca2b`(2023-12-21,该文件最近一次修改)钉死,
  主源取 gitlab 官方 raw,备源取 GitHub 镜像同 commit(raw 双源
  sha256 实测一致:`20bb0e31…`)。conan get() 通过无归档扩展名的
  `filename` 直接下载裸文件。
- tarball 式发行不适用 → manifest `tar_format: none`。
- **裸文件下载必须用 `download()`(真机实证,踩了两次)**:conan 2.29 的
  `get()` 源码为 `download → unzip → os.unlink` **无条件解压**,裸文件
  报 `BadZipFile: File is not a zip file`,与 strip_root 无关(G2 两连败
  后读设备端 conan 源码确认)。修复:`download(self, url, filename=...,
  sha256=...)` 纯下载,hash 校验与多 URL 回退原生支持,不碰解压。

## 脚本行为(探针锚点依据)

- 用法:`installkernel <version> <image> <System.map> <directory>`
  (3 或 4 参,第 4 参缺省 `/boot`),否则打印 Usage 退出 1。
- 复制 `$bootimage` → `vmlinuz[${suffix}]`、`$mapfile` →
  `System.map-${kernelrelease}`、同目录 `.config` →
  `config-${kernelrelease}`;已存在文件先留 `.old` 备份。
- flavor 后缀取自 `${kernelrelease##*[0-9]-}`(如 `-lts`);
  destdir 以 `/boot` 结尾时,写 `lib/modules/<release>/kernel-suffix`
  (已存在则跳过)。
- 纯复制脚本,无网络/无特权依赖(消费者执行时才需目标目录写权限)。

## OHOS 适配

纯脚本工具包,无编译无链接(kicad-demos/inform6-library/ldraw-parts/
fabric-completion 范式):

- `build()` 防漂移:1 文件在位 + 全树总数 == 1 + 918 字节/45 行精确;
- `package()` 显式复制单文件 → `sbin/installkernel`(Alpine 上游同款
  安装路径);`cpp_info.bindirs = ["sbin"]`;
- `package_id` 清空;无 runenv(消费者按需调用脚本);
- commands.json 按 R38 配置(software 级,type=tool,
  commands=["installkernel"],binary=false)。

## 测试口径

上游无测试套件(APKBUILD `options="!check"`)。适配后消费者探针
(`test_package/installkernel_probe.cpp`)5 组断言:

1. 包内清单:sbin/installkernel 在位非空,sbin/ 恰 1 文件,全树恰 1
   文件(排除 conan 簿记,真机实证口径);
2. 内容锚点:shebang `#!/bin/sh`、`set -e`、Usage 行精确、`/boot`
   缺省、`.old` 备份、vmlinuz/System.map-/config- 复制行、
   kernel-suffix 写入逻辑;
3. 静态完整性:918 字节 + 45 行精确、无 CR、首行 shebang + 末行
   `exit 0`;
4. 行为烟测:`sh -n` 语法零告警;0 参数干跑 → Usage + exit 1(上游
   实际行为);
5. 截断/坏 Usage 注入负向(写入→校验拒绝→清理)。

## 许可

- **GPL-2.0-only**(APKBUILD license 字段声明)。
- 脚本本体无内嵌许可文本 → 本包**不设 licenses/ 目录**(保持上游
  发行原样),许可随 manifest/notes 声明,探针逐字断言脚本内容防
  替换。

## 真机实录(2026-09-26, ohos-aarch64, conan 2.29.1, 通道2)

八门禁全绿:`配方验证通过: installkernel 4.1`(G0-G4/L2/L4/L5,
EXIT=0;G0 构建系统 unknown 跳过预查询,G3 无同名库冲突,L2/L4/L5
无 cache 路径跳过——纯脚本包与 fabric-completion 同口径)。消费者
探针 5 组断言真机实跑全过(含行为烟测,非 SKIP)。

G2 六连修战(全部真机实证,详见 reports/):

1. `get()` 裸文件 BadZipFile → 读设备端 conan 源码(get() 无条件
   unzip)→ 改 `download()`(详见路径B草稿 DRAFT-installkernel-
   conan-get-unzip);
2. build() 全树计数 7≠1:默认 layout 下 source_folder==build 文件夹,
   6 个 conan env .sh 混入 → 计数排除 .sh(fabric 同款);
3. 行为烟测 3 断言全挂:`/tmp` 真机只读 → 探针临时目录
   pick_temp_dir() 写权限实测(TMPDIR/TMP/TEMP→cwd 回落,详见路径B
   草稿 DRAFT-installkernel-ohos-tmp-readonly);
4. 真机 clang 报 `::rmdir` 未声明 → POSIX 分支补 `<unistd.h>`。

下载链路:conandata 官方双源 URL 在真机被 E017 注入 ghfast(已挂),
本地 http.server 镜像(192.168.43.12:8899)sed 替换绕过,918 字节
sha256 与钉死值一致(20bb0e31…)。

## 参考

- 上游:https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/installkernel
- APKBUILD:https://gitlab.alpinelinux.org/alpine/aports/-/blob/master/main/installkernel/APKBUILD
- Gentoo 对照(排除):https://github.com/projg2/installkernel-gentoo
