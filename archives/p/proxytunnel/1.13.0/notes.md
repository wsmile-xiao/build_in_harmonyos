# proxytunnel 1.13.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 GNU Makefile，无 configure）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（OHOS aarch64，/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

```bash
# 唯一依赖 openssl 从 conan 制品仓拉取（W0 已验证 ohpcd 有预编译包）
conan install --requires=openssl/3.5.6.1 -pr:h=ci/conan/profiles/ohos-aarch64 ...

# 源码: github archive tag v1.13.0 (commit 8327ac1c50)
tar xzf proxytunnel-1.13.0.tar.gz && cd proxytunnel-1.13.0

# 交叉编译（在 OHOS 设备上原生构建 aarch64）
make -j1 CC=clang \
  CFLAGS="-fPIC -O2 -I$OPENSSL/include" \
  LDFLAGS="-L$OPENSSL/lib -lssl -lcrypto"
```

产物为单一可执行文件 `proxytunnel`（PIE + GNU_RELRO，静态链接 conan openssl）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 内 `LDFLAGS += $(SSL_LIBS)`，pkg-config 找不到 openssl 时回退裸 `-lssl -lcrypto` | OHOS 无系统 openssl 开发库 | make 命令行显式传 LDFLAGS（命令行变量优先级高于 Makefile 内 += 赋值），指向 conan openssl 的 lib/libssl.a+libcrypto.a |
| 2 | `make install` 失败 | install 目标驱动 docs/ 生成 man 页，需 asciidoc+xmlto（CI 无此工具链） | conanfile package() 直接 copy 二进制与 LICENSE，跳过 man 页 |
| 3 | 隧道测试无回显 | 主循环 cpio() 在 stdin EOF 时立即退出，来不及读 socket 回包 | test.sh 中发送数据后保持 stdin 打开 2 秒（`{ printf 'PING'; sleep 2; } | proxytunnel ...`） |
| 4 | 制品仓查询 openssl 3.5.4 报错 | 版本号不存在（存在的版本为 1.1.1w/3.0.16/3.5.6/3.5.6.1/3.5.6.1.1/3.5.8.1） | 选用 openssl/3.5.6.1（W0 `conan download --only-recipe` + `conan install` 双重验证有预编译包） |

## 源码修改

无补丁。上游 v1.13.0 对 Linux/musl 兼容性良好：
- strlcpy/strlcat 自带实现（Makefile 按 uname 条件编入）
- readpassphrase 为 OpenBSD 移植版，直接可用
- setproctitle 用 SPT_REUSEARGV（SPT_TYPE=2）方案，musl 下可编译运行

## 依赖版本

- openssl/3.5.6.1（ohpcd 制品仓预编译静态库，package f23d5a9b1d537641c03c7814478a2fadb727650a）

## 验证结果

```bash
$ proxytunnel -V
proxytunnel 1.13.0 Copyright 2001-2026 Proxytunnel Project

$ proxytunnel --help          # 完整用法输出，EXIT=0

# 真实隧道回环（本地 mock 代理）
$ { printf 'PING'; sleep 2; } | proxytunnel -q -p 127.0.0.1:<port> -d example.org:443
MOCK-ECHO:PING                # CONNECT 请求格式正确 + 双向数据转发成功

$ proxytunnel -e -p 127.0.0.1:<port> -d example.org:443
SSL_connect failed            # 证明 libssl 真实链接并被调用

$ proxytunnel -p 127.0.0.1:1 -d example.org:443
error: failed to connect to local proxy: [111] Connection refused   (EXIT=1)
```

test_package/test.sh 共 8 项断言全部通过（PASS=8 FAIL=0）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/proxytunnel | ~190KB | 单一可执行文件（aarch64 PIE，静态链接 openssl） |

## 注意事项

- 上游无测试套件（Makefile 无 check 目标），test_package 为消费者视角功能测试（含真实 CONNECT 隧道回环）
- man 页未打包（需 asciidoc+xmlto）；用法可经 `proxytunnel --help` 获取
- R38：命令行工具，软件级已声明 commands.json
---

**编译结束**: 2026-09-07 16:33
**最终状态**: built

## finish 阶段观察（框架行为记录，按 R11 绕过未改框架）

1. **G0 clean-verify 假定 autotools**：`ohc-run.py finish` Step 3 的 G0 干净构建验证默认执行 `./configure`（proxytunnel 是纯 Makefile 项目无 configure），报 exit 127 后以非阻塞警告放行。真正的干净构建门禁由 Step 4 conan-verify 的 G2（`conan create` 干净构建）覆盖，已 PASS，故此警告不影响交付。
2. **gen_summary 崩溃（框架 bug）**：Step 8 `gen_summary` 报 `'str' object has no attribute 'append'`（框架脚本缺陷），不影响归档与验证结果。
3. **W2 PR 原子性检查基线偏差**：Step 9 以 origin（个人 fork）main 为基线对比，而 fork main 落后 upstream/main，导致误报"框架文件变更(.gitignore、ci/config/no_official_test.txt) + 817 个配方文件变更"。实际工作区 `git status` 干净（仅新增 archives/p/proxytunnel/），PR diff 以 upstream/main 为基线时只含本包文件，CI JC6 门禁以 PR 实际 diff 为准。
4. **Step 10 submit 预检 3 项未就绪**：reports/test-report.md、packaging/ 产物、.staging-verified 属 submit/upload 阶段产物，本任务边界为 finish（不执行 submit），按任务要求保持现状。

## 知识沉淀

- 知识草稿：`knowledge/drafts/E556-draft-DB80.{kv,md}`（纯 Makefile 项目 pkg-config 探测回退与 make 命令行 LDFLAGS 接管，L2 build-system 级模式，proxytunnel 1.13.0 为实证）

## 最终验证汇总（2026-09-07）

- conan-verify：G1/G2/G3/G4 全 PASS（G2 = 干净 conan create + test_package 8/8 断言 PASS）
- W3 本地 CI 模拟：setup.sh + build_and_test.sh 全 PASS
- finish：EXIT_CODE=0（finish_success），manifest status=built，.ci-result.json 已写入（integrity_hash=5ae788b2c6174d22）
