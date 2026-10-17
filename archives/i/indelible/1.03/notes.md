# indelible 1.03 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-27
- 编译器: clang/clang++
- 状态: built（待 HMBS 真机 rule4 门禁验证后更新为 published）

## 上游信息
- 上游仓库: https://github.com/evolbioinfo/indelible（Debian 已将 Homepage/Source 指向该地址；原始官网 http://abacus.gene.ucl.ac.uk/software/indelible/）
- 源码包: http://abacus.gene.ucl.ac.uk/software/indelible/EFBKqHdv0v7qir6CyeHgqaz/INDELibleV1.03.tar.gz
- sha256: 6b74cbe0d3ce202e99d04282a87b564449ab935c66480f20665f1fb4102721a6（引自 brewsci/homebrew-bio Formula/indelible.rb，与官方 tarball 同源）
- 源码形式: configure.ac + Makefile.am + src/（标准 C++，约 10000 行），help/ 手册与 control.txt 示例，indelible.1 man 页
- 许可证: GPL-3.0-or-later（src/indelible.cpp 文件头声明）
- 申请人: Bingggooo，队伍名称: 来都来了

## 编译步骤

Autotools 标准三步，OHOS 下追加 --build/--host（与 a52dec 0.7.4 同式）：
```bash
sh ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j1
make install
```
conanfile.py 通过 AutotoolsToolchain/Autotools 完成上述步骤，不裸用 ${CC} 等 shell 变量（R33），平台判断用 `in ("Linux", "OHOS")`（R32）。

源码 URL 仅保留官方 http 单地址的原因：上游只提供 http（不支持 https，属代码规范第 13 条例外）；CI 的通用镜像改写仅覆盖 github/gnu 等域名，对 abacus 域无等价镜像；Debian 的 orig.tar.xz 是重打包（不同 sha），不可混作 fallback。保留原 URL 并如实报告，符合任务守则下载可靠性条款。

## 上游测试审计结论（no_tests）

解压官方 tarball 并审计（详见 test_package/MANIFEST.yml upstream_test_audit）：
- 无 tests/、test/ 目录；无 gtest/pytest/ctest 接线；Makefile.am 无 check/TESTS 目标
- control.txt 是运行示例输入（非断言套件）；help/ 为手册教程；Debian 的 debian/tests/* 系打包层 autopkgtest，非上游套件
- 因此 build() 未调用 make check（无目标可调），test_package 以 2 项真实二进制功能验证覆盖（R34 合规）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 本机 `git checkout main` 报 `invalid path 'archives/g/gama/...patch??'` | 上游某文件名尾带 `\r\r`，Windows NTFS 非法 | `git config core.protectNTFS false` + 稀疏检出排除该文件及大小写碰撞的 libXext/libxext 后检出成功；属本机环境 workaround，不进配方 |
| 2 | `archives/l/libXext` 与 `archives/l/libxext` 在 Windows 同目录碰撞致工作树恒脏 | Windows 文件系统大小写不敏感 | 稀疏检出排除两者，工作树恢复干净；同为本机 workaround，不进配方 |
| 3 | 真机 `source()` 对官方 http 单地址报 `AuthenticationException: 403 Forbidden` | abacus 旧站对真机网络回 403；全网无可信同字节镜像（web.archive.org 仅 404 快照，Debian/Ubuntu orig.tar.xz 系重打包、sha 不同不可混用） | `conandata.yml` 的 url 改为同一官方路径 https 优先、http 保留回退的有序列表（同归档同 sha256，不改校验值、不引入第三方源）；`source()` 的 `get(**sources[0])` 原生支持 url 列表逐个尝试；但真机复测 https 仍报 SSL Hostname mismatch、http 仍报 403（本机 urllib 复现一致），故本轮改用 kloetzl 提交锁定包为主源、官方原归档为回退，source() 按条目逐个 try/except（各用自有 sha） |

## 依赖版本

无 Conan 依赖（requirements 为空）。构建仅需系统 clang/make/autotools，由真机工具链与 Conan buildenv 提供。

## 验证结果

待 HMBS 真机预检（conan create）返回后填写：
- `HMBS_TEST_PACKAGE_RESULT`（2 项功能验证：空目录示例生成 + 最小 control.txt 仿真产出非空）
- `HMBS_UPSTREAM_TEST_RESULT`（status no_tests，discovered/executed 均为 0，附 reason）
- 退出码为 0 不等于真跑：测试脚本断言输出文件非空且含 `_TRUE.phy`/`FAST` 标记，避免空文件比空文件式误报

## 注意事项

- 本包为 application（产出 bin/indelible 单二进制），package_info 仅声明 bindirs，libdirs/includedirs 置空；软件级 commands.json type 为 tool
- test_package 用 TMPDIR 下独立临时目录运行，避免污染；indelible 无 control.txt 时会自动生成示例文件，该行为即用例 1 的断言依据（man 页明确记载）
- 任何配方/测试改动后旧验证即失效，需重新走真机全部门禁；本轮未提交，等待 HMBS 后台验证
