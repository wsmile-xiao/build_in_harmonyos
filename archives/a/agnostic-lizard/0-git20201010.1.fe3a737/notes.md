# agnostic-lizard 0~git20201010.1.fe3a737 — HarmonyOS PC (aarch64) 适配笔记

## 任务

- 平台任务:`agnostic-lizard/0~git20201010.1.fe3a737`(10 火种,分支 `feat/agnostic-lizard-0-git20201010.1.fe3a737`)
- 源包:Debian `agnostic-lizard_0~git20201010.1.fe3a737-2`(orig tar.xz 28,700 B,27 个纯文本文件)
- 结论:**纯源码 Common Lisp 库,零编译**。Debian 二进制包 `cl-agnostic-lizard`(19.5 KB,
  all 架构)只是把源码树装到 `/usr/share/common-lisp/source/agnostic-lizard`。
  本适配按 `pari-seadata-big` 确立的"数据/源码包豁免"模式 conan 化:
  noarch(`package_id` 清空)、`build()` 以逐文件 sha256 + 清单全等的确定性校验替代编译冒烟。

## 包内容与验证

- 27 个文件全部钉死 sha256(`test_package/verify_agnostic_lizard.py`,27/27 PASS):
  2 个 ASDF 系统定义(`agnostic-lizard.asd`、`agnostic-lizard-debugger-prototype.asd`)、
  16 个 `.lisp` 源文件、doc/、AUTHORS/README、COPYING + gpl-3.0.txt(GPL-3.0-or-later)。
- orig tarball sha256 `4426d661…cddb0` 与 snapshot.debian.org 包页一致;
  dsc `542f3b8d…` / debian.tar `5f627c31…` 同批取证。

## 消费方式(HarmonyOS PC)

任意带 ASDF 的 CL 实现(SBCL/CCL/CLISP 等,平台后续落地)注册包路径即可加载:

```
export CL_SOURCE_REGISTRY="<pkg>/share/common-lisp/source/agnostic-lizard//"
(asdf:load-system "agnostic-lizard")
```

配方同时导出 `AGNOSTIC_LIZARD_SRC_DIR` 与 `ASDF_SOURCE_REGISTRY_ADDITIONAL`
(`(<dir>//**/*.*r*)` 注册表项)。前置依赖:无(包本身零依赖;
真正调用 macroexpand-all 需要一个 CL 实现,属于平台前置任务,与本包无关)。

## 版本号说明

Debian/上游版本 `0~git20201010.1.fe3a737` 中的 `~` 在 conan 版本与 git 分支名中
不合法,统一替换为 `-` → conan 版本/目录/分支 `0-git20201010.1.fe3a737`
(与平台任务分支一致);snapshot 下载 URL 中以 `%7E` 编码。

## 运行时可用性说明

agnostic-lizard 是 CL 源码库(宏展开/代码游走工具),其"运行"发生在宿主 CL
实现内。当前平台生态尚无 CL 实现,本包先行落地源码资产,不阻塞、不被阻塞——
与 fenics 元包"先行落地,前置后置"同型。
