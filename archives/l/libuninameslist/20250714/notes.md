# libuninameslist 20250714 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos toolchain)
- 状态: published

## 编译步骤

```bash
# tag 归档无预生成 configure，先自举（本机手工验证）
autoreconf -i
# config.guess/config.sub 打 HarmonyOS 补丁（E007/E122 方案，
# 配方内用纯 Python 内联等价实现，避免依赖 conan 环境外 perl）
./configure --prefix=/storage/Users/currentUser/usr/local --disable-shared --enable-static
make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libuninameslist-20250714
make check   # 4/4 PASS
# Conan 配方验证
ohc-run.py conan-verify libuninameslist 20250714   # 8 道门禁 PASS
# finish（含 W3 本地 CI）
ohc-run.py finish libuninameslist 20250714 published  # EXIT 0，W3 ✅
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档无 configure，conan create 首跑失败 | GitHub codeload 源码归档不含 autoreconf 产物；CI 干净沙箱(USER=100)看不到 $HOME/.local 手工工具 | 配方 build_requirements() tool_requires(automake/1.18 + libtool/2.5.4)，build() 先 self.run("autoreconf -i", env="conanbuild") 自举 |
| 2 | config.guess 不识别 HarmonyOS（UNAME_SYSTEM=HarmonyOS） | GNU config.guess 无 __OHOS__/HarmonyOS 分支 | 配方内纯 Python 内联补丁：__OHOS__ LIBC 检测 + HarmonyOS 系统分支（E007 方案） |
| 3 | config.sub 拒绝 aarch64-unknown-linux-ohos（kernel linux + os ohos） | config.sub kernel-os 校验列表无 linux-ohos | 配方内 Python 内联：ohos-linux 三元组 + OS 列表 ohos* + kernel 校验列表 linux-ohos*-（E122 方案） |
| 4 | 配方内 subprocess 调 perl 打 config.guess 补丁失败 | conan 构建环境 PATH 无 perl | 补丁逻辑纯 Python 内联实现（不再依赖外部 perl） |
| 5 | autoreconf 生成脚本无可执行位 | HMDFS 不保留权限位（E490） | source()/build() 对 configure/config.guess/config.sub/install-sh/missing 等 chmod 755 |
| 6 | lang-preflight 误判 mixed(setuptools) | 全树扫描命中 py/ 绑定目录 setup.py，优先级高于顶层 configure.ac | 按 R47 边界规则人工复核判 C（绑定/辅助脚本不算主体），继续适配（DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect） |
| 7 | conan-verify E017 镜像注入在 conandata.yml 残留 gh-proxy 前缀 | E017 临时注入镜像后恢复不完整 | 提交前恢复官方单一 HTTPS URL，清理 .ghfast-bak/.orig（R39/PF7） |

## 源码修改

无 patches/ 文件。OHOS 适配全部在配方内完成：
- conanfile.py：自举（tool_requires + autoreconf）、config.guess/config.sub 纯 Python 内联补丁、脚本 +x
- conandata.yml：官方 tag 归档 URL + SHA-256

## 依赖版本

- 无 runtime requires（纯 C 数据库，无依赖）
- tool_requires: automake/1.18, libtool/2.5.4（制品仓已发布）

## 验证结果

- make check: 4/4 PASS（tests/test-suite.log，sha256 1cdc890d0d70085b8a35b0d485043d42871f827dbf913a31ddff9ce4dcb4dc2a）
- conan-verify: G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS
- W3 本地 CI: L0/L1/L1a/L1b/L4/L5 全 PASS（无 bin/ 纯库，L2 跳过）
- HarmonyOS 专项测试 ohos_test.c: 7/7 断言 PASS（OHOS 交叉工具链编译实测）
- 消费者测试 test.c: 5/5 断言 PASS
- .ci-result.json: exit_code=0，log_sha256=1077aaaa0e08be42380af5de6859aafe5deada216b3e6e58d740ca3085621461

## 注意事项

- upstream test 双口径：源码声明 8（call-test0..7），当前配置实例化 4（call-test0/1/2/6），全量通过率 4/8=50%，当前可执行集合 4/4=100%；未实例化 4 个为 WANTLIBOFR（法语库）互斥分支，详见 reports/upstream-test-ledger.md
- libuninameslist 仅含 NamesList 表内名称；CJK 表意文字（U+4E00 等）不在名称表，uniNamesList_name 返回 NULL，属上游数据行为（ohos_test 已按此断言）
- 知识路径：任务类型「知识库扩展」，路径 B 成立（new_draft 两条），台账见 reports/knowledge-candidate-ledger.md