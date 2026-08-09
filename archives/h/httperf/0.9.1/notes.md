# httperf 0.9.1 适配笔记

## 编译环境
- 构建系统: autotools (autoreconf + configure + make)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
autoreconf -i                      # GitHub tarball 无 configure，需先生成
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check                         # 上游无测试套件，空操作
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建 confXXXXXX 临时目录 Permission denied (E011) | HMDFS 上 umask 077 临时目录对当前进程不可写 | 配方 build() 中 autoreconf 后 `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | conan get 报 BadZipFile | codeload URL 无 `.tar.gz` 扩展名，conan 无法识别压缩格式 | conandata.yml 显式声明 `filename: httperf-0.9.1.tar.gz` |
| 3 | test_package 中 httperf 报 rc=127 not found | 直接 subprocess 调用未注入 conanrun 的 PATH | 改用 `self.run(..., env="conanrun")` 执行测试 |

## 源码修改

无补丁。所有适配处理均在 conanfile.py 配方内完成（E011 umask 修复、autoreconf）。

## 依赖版本

- 无第三方依赖（纯 C，仅链接系统 -lm）

## 验证结果

```bash
httperf --version    # httperf-0.9.1 compiled Aug 6 2026
# 对本地 http.server 执行 3 连接/6 请求基准测试，Total 行断言通过
conan create         # G2/G3/G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/httperf-0.9.1-ohos-aarch64.tar.gz | 40.6 KB | httperf 可执行文件 |

## 注意事项

- httperf 是命令行基准测试工具（R38 type=tool），已创建软件级 commands.json
- 运行时需要目标 HTTP 服务器，自身不提供服务
---

**编译结束**: 2026-08-06 23:04
**最终状态**: published
