# iwnet 1.3.1 适配笔记

## 编译环境
- 构建系统: makefile（Autark build.sh 包装的 Makefile 驱动，非 autotools/cmake）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

```bash
# 探索编译（本机 OHOS aarch64）
AUTARK_HOME=<绝对路径>/autark-cache/.autark-dist ./build.sh --prefix=<stage>
# 关键环境注入：
#   - AUTARK_HOME 必须绝对路径（嵌套 iowow 外部项目构建时相对路径 execve 失败）
#   - PATH 需含 busybox 提供的 install（toybox 无 install，E098）
#   - 测试构建/运行：IWNET_RUN_TESTS=1 ./build.sh；cunit.pc 放入 autark-cache/lib/pkgconfig
# Conan 配方构建
python3 scripts/ohc-run.py conan-init iwnet 1.3.1
python3 scripts/ohc-run.py conan-verify iwnet 1.3.1   # G1-G4 全过
python3 scripts/ohc-run.py finish iwnet 1.3.1 built    # W3 本地 CI 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 嵌套 iowow 构建 `execve: Permission denied` | build.sh 默认 AUTARK_HOME 相对路径，extern 项目 cwd 切换后子进程 autark 解析失败 | 注入绝对路径 AUTARK_HOME + PATH 提供 autark 入口（DRAFT-autark-absolute-autark-home） |
| 2 | `sed: bad pattern ... /Id` | 上游测试 harness 用 GNU sed `I` 修饰符，toybox sed 0.8.12 不支持 | 改写为大小写字符类 `/[dD][aA][tT][eE]|...|^\*/d`（3 个 run 脚本补丁，DRAFT-toybox-sed-i-flag-char-class） |
| 3 | `curl: option --data-urlencode: out of memory` | OHOS curl 8.8.0-DEV 对 --data-urlencode @15MB 文件编码缓冲有内存上限（1MB 可、5MB 起 OOM） | **r02 已恢复**：python3 预计算 URL 编码表单体 + `--data-binary @bigparam-enc.dat` 原样发送（服务器 `_handle_post_bigparam` 原样回写，语义等价）；server2 plain/ssl 与 proxy1 复跑均 rc=0（DRAFT-curl-data-urlencode-memory-limit） |
| 4 | ws socket 变体 `Operation not permitted` | /tmp 只读 + HMDFS 不支持 unix domain socket bind | 记录为真实平台限制（E461/E024 已覆盖），恢复条件=ext4/tmpfs 挂载点 |
| 5 | `required tool 'install' not found` | OHOS toybox 无 install 命令 | PATH 垫片 busybox（E098 已覆盖） |
| 6 | cunit 未找到 | 测试链接需 `pkg-config --libs cunit`，ohpcd 有 cunit/2.1.3 | conan install cunit/2.1.3 并导出 cunit.pc |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-src-http-tests-proxy1-tests-run.sh.patch | FILTER sed `I` 修饰符 → 大小写字符类 |
| 0002-src-http-tests-server1-tests-run.sh.patch | 同上 |
| 0003-src-http-tests-server2-tests-run.sh.patch | 同上 |

## 依赖版本

- iowow：上游 build.sh 经 iowow.autark 自拉取 GitHub master（1.5.3-dev），in-source 构建
- cunit/2.1.3（ohpcd 制品仓，测试链接用）
- libhive：仅 ENABLE_GRPC=1 需要，默认 0 不启用

## 验证结果

- 上游测试（r02 最终）：source_declared_total=15，configured_executable_total=11，executed_passed=**11**，
  失败 0、未实例化 4（ws_client_test3×1 + grpc×3，均有 r02 最小纳入尝试证据）
  全量通过率 11/15=73.3%；当前配置可执行集合 **11/11=100%**（明细见 reports/upstream-tests-ledger.md）
- r02 恢复：server2/proxy1 两入口由失败转通过（python 预编码 + --data-binary，证据 evidence-r02/）
- 鸿蒙专项测试：iwnet-ohos-test（公开 API HTTP 服务器 + 真实 socket 客户端）编译链接运行 rc=0，
  HTTP 200 + 期望 body 确认（task #7）
- 消费者用例：test_package/test.c 经 conan create 实测 1/1 Passed
- conan-verify：G1-G4 全过；finish W3 本地 CI exit_code=0（.ci-result.json log_sha256=945c0a6d...）
- W3 基线隔离复验：cloog/kics 3 个空基线文件（SHA-256 e3b0c44...）隔离后 JC 通过、
  原样恢复 SHA-256 一致、git status 干净（未进 diff/PR）

## 交付物

- archives/i/iwnet/1.3.1/：conanfile.py + conandata.yml + test_package/ + patches/ + manifest.yaml + notes.md + reports/
- knowledge/drafts/DRAFT-iwnet-1.3.1-*.kv/.md ×3（路径 B 知识库扩展草稿）
- 无二进制打包产物（status=built，未 upload）

## 注意事项

- 配方内联 `BUILD_TYPE=Release AUTARK_HOME=<abs> ./build.sh --prefix=...` 兼容 Conan 2.x
  多版本（本机 Environment(self) 构造签名差异，改用 shell 内联前缀）
- 测试运行需在支持 unix socket 的挂载点；本设备 HMDFS 限制下 ws socket 变体不可运行
