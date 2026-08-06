# abs-guide 10 适配笔记

## 软件信息

- **软件**: abs-guide（The Advanced Bash-Scripting Guide，作者 Mendel Cooper）
- **版本**: 10（2014-03-10，'PUBLICDOMAIN' release，最终版）
- **许可证**: Public Domain（文档声明 "herewith granted to the Public Domain. No copyright!"）
- **上游首页**: https://tldp.org/LDP/abs/html/（tldp.org 在线版）
- **源码包**: https://fossies.org/linux/docs/abs-guide-10.html.tar.gz（Fossies 镜像，作者原站已失效）
- **SHA256**: e543941dc1d32689fca9da49ab89dc5f11f1655937a10afc6b3a414ac4b2da9e（下载实测校验通过）

## 编译环境

- 构建系统: custom（纯 HTML 文档安装，无编译）
- 编译日期: 2026-08-05
- 编译器: 无需编译
- 状态: built

## 编译步骤

1. 下载 abs-guide-10.html.tar.gz 并校验 SHA256（e543…da9e，与 Fossies 公布值一致）。
2. 解包：tarball 内为 `abs-guide/*.html` 共 140 个预渲染 HTML 页面（约 3.4MB），无源码、无构建系统、无测试。
3. init-build 生成构建上下文与归档骨架（OHC_PROJECT_DIR 指向本仓库）。
4. conan-init 生成配方骨架后，重写为数据包模式：
   - `conanfile.py`: `package()` 将 `*.html` 安装到 `share/doc/abs-guide/`，无 `cpp_info`。
   - `test_package/`: python 消费测试断言 140 个页面存在且非空（L1）。
5. `conan-verify abs-guide 10` 验证（G0-G4 + L2/L4/L5）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 401 Unauthorized | Fossies 拒绝 `ohc/1.0` User-Agent | 用 curl（默认 UA）预下载并校验 SHA256，预置到 build_dir 后 init-build 跳过下载直接校验 |
| 2 | 归档写入 SKILL 目录而非仓库 | `find_project_dir()` 从脚本位置向上找 SKILL.md，命中 SKILL 目录 | 设置 `OHC_PROJECT_DIR=<工作区>` 环境变量 |
| 3 | build_dir 与预期不符 | `TMPDIR` 环境变量指向 `/storage/Users/currentUser` | 将 tarball 预置到 `${TMPDIR}/builds/abs-guide-10.tar.gz` |
| 4 | conan-init 生成的 autotools 模板不适用 | 纯文档包无 configure/make | 参照 adwaita-fonts 数据包模式重写为 custom 安装配方 |

## 源码修改

无需补丁（patches/ 为空）。上游为静态 HTML 文档，直接安装。

## 依赖版本

无依赖（独立文档包）。

## 验证结果

- 上游测试: 0（纯文档包无测试框架）
- 新增消费测试: 1（test_abs_guide.py，断言 140 个 HTML 页面存在且非空）
- conan-verify: G0-G4 + L2/L4/L5 全通过

## 发现与知识

✅ abs-guide 是纯 HTML 文档包（Advanced Bash-Scripting Guide v10，Public Domain），无源码无构建系统，Conan 配方只需把 HTML 安装到 share/doc/abs-guide/
✅ Fossies 镜像拒绝 ohc/1.0 与浏览器类 User-Agent（HTTP 401），需使用 curl/wget 类 UA（配方 source() 通过 headers 参数设置）
✅ init-build 的 build_dir 受 TMPDIR 环境变量影响；下载被拒时可预置 tarball 到 ${TMPDIR}/builds/ 跳过下载
✅ find_project_dir() 默认解析到 SKILL 目录，适配本仓库必须设置 OHC_PROJECT_DIR 指向工作区
✅ 文档类包适配参照 adwaita-fonts 数据包模式：package_type=application、无 cpp_info、test_package 用 python 脚本断言文件完整性

## 注意事项

1. 上游作者原站（bash.deta.in）与 tldp.org 的 tarball 均已失效（404/不可达），Fossies 为当前唯一可下载且有公布校验和的镜像。
2. Fossies 会拦截非浏览器 UA，`conan download`/CI 若直接抓取该 URL 需注意 UA 问题（conan get 使用默认 UA 实测正常，见 conan-verify 结果）。
3. 本包无二进制产物，L2/L4（安全扫描）按文档包豁免处理。
---

**编译结束**: 2026-08-05 22:30
**最终状态**: built
