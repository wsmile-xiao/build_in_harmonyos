# libaesgm 2013.1.1 适配笔记

## 编译环境
- 构建系统: 无（纯 C 源码库，无 Makefile/configure/CMake）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（ohos-aarch64 Conan profile）
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤

libaesgm 2013.1.1 上游为 Brian Gladman AES 纯 C 源码（13 个文件，无构建系统），
因此 recipe 采用直接编译方式（R47 语言预检 detected=c）：

1. `init-build libaesgm 2013.1.1 --url=<官方标签 tarball>` 下载解压
2. `lang-preflight`：c，通过
3. 手动验证：clang -O2 编译 aes_modes.c/aescrypt.c/aeskey.c/aestab.c → llvm-ar 打包
   libaesgm.a → smoke roundtrip 通过
4. 编写 conanfile.py：source() 下载 + build() 直接 clang 编译打包（无构建系统库），
   package() 收头文件 + 静态库，cpp_info.libs=["aesgm"]
5. `conan-verify`：G0-G4/L2/L4/L5 全 PASS
6. `finish` published/built：W2 结构 + R36 依赖 + W3 本地 CI 模拟通过
   （.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直接给仓库 URL 下载返回 HTML | URL 指向仓库主页而非发布包 | 改用官方标签 tarball `archive/refs/tags/2013.1.1.tar.gz` |
| 2 | 自动生成的 Autotools 模板配方不适用 | 上游无构建系统 | 重写为直接编译 recipe（_compiler 按 settings 确定性选择，R33） |
| 3 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | main 基线自带未登记隐藏文件，本分支无 commit 时 junk_check 回退 full 模式全仓扫描 | 按无关历史基线规则临时 index 隔离（记录 blob/hash）→ 复验通过 → 无条件恢复（index 与 HEAD blob 一致 e69de29b） |
| 4 | conanfile.py 模板 sha256 占位符 | 模板未填 | 官方独立下载校验 sha256=102353a4... 后填入 conandata.yml |

## 源码修改

无源码修改，无 patches（上游源码零改动，直接编译打包）。

## 依赖版本

无第三方依赖（纯标准库 C 代码，requirements 为空）。

## 验证结果

```bash
# AES-128 roundtrip 消费者测试（test_package）
clang -O2 -I <src> test.c libaesgm.a && ./test → "libaesgm AES-128 roundtrip: OK"
# conan-verify
python3 scripts/ohc-run.py conan-verify libaesgm 2013.1.1 → G0-G4/L2/L4/L5 全 PASS
# W3 本地 CI 模拟
python3 scripts/ohc-run.py finish libaesgm 2013.1.1 built → exit 0，.ci-result.json exit_code=0
```

## 注意事项

- 上游无构建系统、无测试套件：MANIFEST.yml 中 upstream_tests 为空并附清点证据（R51）
- 库名 aesgm：静态库文件 libaesgm.a，cpp_info.libs=["aesgm"]
- 上游许可证：BSD-2-Clause（Brian Gladman AES 声明）
- 版本 2013.1.1 为上游正式标签（xmake-mirror 镜像仓库）

## R02 (rule12 鸿蒙特有测试补齐, 2026-09-26)

- 起因：外部审查 VERDICT=FAIL，rule12「鸿蒙特有测试」N=0 < 1；PR 标题前缀误用【依赖项】应改【积分赛】
- 新增 `test_package/harmony_test.c`：鸿蒙特有测试，独立于既有 test.c——
  - AES-CBC 块模式（aes_cbc_encrypt/aes_cbc_decrypt）加密 64 字节消息
  - 密文写入可写临时目录（$TMPDIR，核验 OHOS /tmp EROFS 只读回退策略），重新读取后解密
  - uname() 平台标识（sysname/release/version，实测 HarmonyOS / HongMeng Kernel 1.12.0 / aarch64）派生 IV，round-trip 校验平台相关派生
  - 反对既有 test.c：不同模式（CBC vs ECB）、不同数据路径（文件 I/O vs 内存）、不同验证点
- 实际运行：exit 0，日志 `reports/harmony-test-run.log`，SHA-256=f8ed6a12962fcebb8fb3db177d73dd1ade9c5e8054933cef65d9ebb1e10d8e73
- test_package/MANIFEST.yml 增列 harmony_specific_tests 声明
- 复验不回退：上游零入口台账成立、test.c AES-128 roundtrip 继续通过、conan-verify G0-G4/L2/L4/L5 全 PASS、finish/W2/W3 通过（.ci-result.json exit_code=0）
- 交付：更新既有 PR #11942（标题前缀【积分赛】），不新建 PR、不关闭重建、不改历史
---

**编译结束**: 2026-09-26 18:44
**最终状态**: built
