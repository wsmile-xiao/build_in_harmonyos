# croncpp 2026.08.12 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (15.0.4, OHOS aarch64)
- 状态: built（conan-verify/W3 通过；制品发布在 PR 合入后由 release 流水线完成）

## 编译步骤

```
1. init-build croncpp 2026.08.12 --url=https://github.com/mariusbancila/croncpp/archive/refs/tags/v2026.08.12.tar.gz
   - 官方 GitHub tag v2026.08.12 tarball, sha256=14441a5f46607e5fce97558cf12505087a1e052d5f5b9a4474ee118fe3303ba2
2. lang-preflight: detected=cpp (C++17 header-only)
3. conanfile.py: package_type=header-library, no_copy_source, package() 仅拷贝 include/croncpp.h + LICENSE
   package_info: croncpp::croncpp target, cxxflags -std=c++17, package_id 清空（header-only 单包）
4. conan-verify: G0-G4 + L2/L4/L5 全 PASS（conan create 含 test_package）
5. 上游套件: cmake -DCRONCPP_BUILD_TESTS=ON → test_croncpp -r compact
   → Passed all 92 test cases with 44294 assertions (ctest 1/1 passed)
6. OHOS 专项消费者测试 test_package/test_croncpp_ohos.cpp: 13 checks, 0 failures
   （解析 / cron_next tm+time_t+chrono / cron_prev / quartz 方言 / 非法表达式 / 年份耗尽 / OHOS libc 时间函数, TZ=UTC）
7. finish published: W2 结构 + R36 依赖(无依赖) + W3 本地 CI
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub SSL 证书校验失败 | 系统 /etc/ssl/certs CA 包缺失 | 导出 SSL_CERT_FILE 指向 certifi cacert.pem（init-build 自身也安装了 CA 到 $HOME/usr/local/ssl/cert.pem） |
| 2 | init-build 下载根 URL 得到 HTML | GitHub 仓库根不是 tarball | 使用 tag tarball URL .../archive/refs/tags/v2026.08.12.tar.gz |
| 3 | conan create G2: package() TypeError: str / str | Conan 2 中 self.source_folder 是 str，不支持 / 拼接 | os.path.join(str(self.source_folder), ...) |
| 4 | test_package 编译错: 'expr' is a private member | cronexpr.expr 为私有成员 | 改用公开 operator== 比较 |
| 5 | test_package 运行崩溃: Cron field value is out of range | 7 字段表达式年份在第 7 位，"0 0 0 * * 2020" 是 6 字段（2020 被解析为 DOW 越界） | 改为 "0 0 0 * * * 2020" |
| 6 | cron_prev 期望值错误 | 语义是「给定时刻之前最近一次」（非之前一天的同刻） | 修正期望 2026-09-05 08:30（from 12:00） |
| 7 | W3 JC 门禁 fail: 9 个 junk 文件 | 分支无 commit → JC 回退 full 模式整仓 ls-files → 命中 main 基线中其他用户已合入的其他库状态文件（embree/flatcv/libmorton/goaccess/captagent/lsof/scudo-malloc/stb_image，均仍在 origin/main 上）；croncpp 自身归档零 junk | 提交 croncpp 归档后 JC 进入 incremental 模式（git diff origin/main...HEAD），只检查本 PR 新增/修改文件；resume finish 复验 |

## 源码修改

- 无（header-only 库源码零修改，无补丁）

## 测试统计口径

- 全目录枚举: 9 个用户测试源文件共 92 个独立 TEST_CASE（catch/catch.hpp 的 161 次宏命中为框架内部实现，benchmark/main.cpp 为基准驱动，均不计入）
- 实际运行: 1 个 ctest 套件，92/92 用例通过，44294 assertions
- 全量通过率 = 92/92 = 100%
- OHOS 专项消费者测试: 13/13 = 100%（独立于上游分母）
---

**编译结束**: 2026-09-03 02:51
**最终状态**: built
