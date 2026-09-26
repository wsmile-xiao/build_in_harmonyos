# minlzma 1.1.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (aarch64-linux-ohos / OHOS armv8)
- 状态: published

## 编译步骤

1. 官方源码：GitHub ionescu007/minlzma 官方 tag `v1.1.5`（codeload 官方 tarball），
   SHA-256 = 49811637b6ad9e555a9e75b4a048cf3d1a92029de07e6b7bb360004eb61e655d
   （注意：tag 名带 `v` 前缀，`refs/tags/1.1.5` 会 404）。
2. `init-build`（--no-download 使用预下载官方 tarball）→ lang-preflight（detected=c，c↔cpp 兼容族不迁移）。
3. `conan-init` 生成配方后手工改写：模板误判为 autotools，实际是 CMake 工程
   （minlzlib 静态库 + minlz 共享库 + minlzdec CLI）。
4. 重写 `conanfile.py` 为 CMake 配方；上游无 install() 规则，package() 手动 copy
   头文件（minlzma.h）、库（minlzlib/ 子目录产物，keep_path=False）、CLI（minlzdec/）。
5. `conan-verify`（ohos-aarch64 profile）G1-G5 全 PASS；test_package 内
   test_minlzma（消费者 API 冒烟）+ test_ohos（鸿蒙专项测试）CTest 2/2 通过。
6. 独立消费者用例：仅用已安装公开头文件 minlzma.h + 公共 API XzDecode，编译运行 OK。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连 tarball 下载超时 | 网络对 github.com codeload 直连不通 | 走 ghfast.top 镜像下载官方 tarball，SHA-256 实测核验 |
| 2 | conan create source() 404 | conandata.yml URL 用了 `refs/tags/1.1.5`（无 v 前缀），上游 tag 实为 `v1.1.5` | URL 改为 `refs/tags/v1.1.5.tar.gz` |
| 3 | G2 test_package 报 `Library 'minlzlib' not found` | 上游在 build 目录 `minlzlib/` 子目录产出库，copy 保留相对路径后 CMakeDeps 在 lib/ 根找不到 | package() 显式指定源子目录 + keep_path=False |
| 4 | 鸿蒙专项测试损坏流断言失败 | 上游默认未定义 MINLZ_INTEGRITY_CHECKS，payload 损坏不触发失败 | 依据字节扫掠实验改损坏 LZMA2 块控制字节（偏移 24），确定性失败 |

## 源码修改

无补丁（patches/ 为空）。上游纯 C11，OHOS armv8 直接编译通过。

## 依赖版本

- 无外部依赖（requires 为空）
- 工具链：clang 15.0.4、CMake 4.1.2、conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# conan-verify G1-G5 全 PASS（ohos-aarch64 profile）
# test_package: ctest 2/2 (test_minlzma, test_ohos) PASS
# 独立消费者：consumer.c 编译链接运行 OK，XzDecode 解压 73 字节内容校验通过
# 上游 README 验证流程（Python LZMA 路径）：4MB noise/whitespace 解压 SHA-256 一致 2/2
```

## 上游测试台账（双口径）

- 官方 tag v1.1.5 全量枚举：26 文件，无 tests/ 目录、无测试框架、无 CTest 注册
  （ctest -N = 0）、无样例/基准/fixture/测试脚本。
- 源码声明独立用例数（source_declared_total）= 0；配置可执行数（configured_executable_total）= 0。
- README 文档化 Linux 验证流程实际执行 4 项：
  - Python LZMA 压缩 noise → minlzdec 解压 → SHA-256 一致：PASS
  - Python LZMA 压缩 whitespace → minlzdec 解压 → SHA-256 一致：PASS
  - xzutils 压缩 noise → minlzdec 解压：FAIL（README 记载的上游限制：minlzlib 不支持块头可选
    压缩/解压大小 VLI 元数据，现代 xz 5.8.2 默认 20 字节块头；xz -0/preset=6 变体复验同 FAIL）
  - xzutils 压缩 whitespace → minlzdec 解压：FAIL（同上；0 字节输出）
- 通过率口径：0/0（官方源码无独立注册用例）；README 流程 2/4，Python LZMA 路径 2/2。
- 上游限制恢复条件：使用 Python lzma / 7-zip / 无可选块头大小字段的编码器输出，即可被
  minlzlib 完整解压（不阻塞本库交付）。
---

**编译结束**: 2026-09-23 04:17
**最终状态**: published
