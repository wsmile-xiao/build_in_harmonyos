# libxar 1.8.0.498 上游测试实跑记录（R51）

- 实测日期：2026-09-19；设备：hm（OHOS aarch64，python 3.12.8，pytest 不需要——上游为独立脚本）
- 被测二进制：本轮 W3 私有 conan 缓存产出的 xar CLI（apple-oss-distributions xar-498 源码 + 8 补丁，--disable-shared --enable-static 静态口径）
- 上游测试原件：xar-498 tarball test/ 目录 7 脚本 57 用例（原件 sha256 见 task-data/libxar-1.8.0.498/upstream-tests-py3/ORIGINAL-HASHES.txt）
- 实跑形式：python3 最小适配副本（修改逐条申报于 PR「上游测试用例修改说明」，生成器 make-adapted-tests.py 可复现）
- fixture：运行目录内相对路径 fixture/（flat：empty/hello.txt/big-zero.bin/xar-copy，mtime 归整整秒——/bin 在设备不可读、man1 不存在，且 xar 按给定路径入档）

## 结果总览

| 脚本 | PASS | SKIP | FAIL | 合计 |
|------|------|------|------|------|
| compression.py | 6 | 2 | 0 | 8 |
| checksums.py | 16 | 0 | 0 | 16 |
| data.py | 0 | 2 | 8 | 10 |
| hardlink.py | 0 | 0 | 3 | 3 |
| heap.py | 2 | 0 | 0 | 2 |
| integrity.py | 8 | 2 | 0 | 10 |
| attr.py | 0 | 8 | 0 | 8 |
| **合计** | **32** | **14** | **11** | **57** |

## SKIP/FAIL 逐项原因

| 类别 | 数量 | 技术原因 |
|------|------|----------|
| SKIP lzma | 6 | 本包按上游 498 默认不启用 lzma（lzmaxar.c 依赖 2006 年 LZMA SDK API）；上游 skip 守卫经 XAR_NO_LZMA=1 触发 |
| SKIP xattr | 8 | 设备无 python xattr 模块（util.py 顶层 import xattr）；适配副本对 xattr 依赖用例抛 TestCaseSkipError |
| FAIL data.py 8 例 | 8 | xar-498 TOC 的 mtime 仅存整秒（证据：xar --dump-toc 输出 <mtime>2026-09-18T18:43:21Z</mtime> 整秒），而测试先以 os.utime(None) 设微秒 mtime 再断言提取前后 st_mtime 精确相等——HFS+ 整秒粒度时代的设计，现代 ns 粒度文件系统必挂 |
| FAIL hardlink.py 3 例 | 3 | HMDFS 不支持硬链接：2 例建档阶段 os.link 即 EPERM；1 例（--link-same）提取阶段 xar 建链失败 exit 2 |

## 原件日志

- stdout（PASSED/SKIPPED/FAILED 逐行 + 分脚本 RC）：evidence/upstream-tests-stdout.log
  - sha256: 621c847b3acedc969e8ea72db4db11dc68d58427a825abfa1b5064da780811f4
  - 字节数: 2969；行数: 84
- stderr（运行traceback/报错明细）：evidence/upstream-tests-stderr.log
  - sha256: 2c6ff819bcd245451309e0f6fbf919dddd99dee16d95c7ad429e2b36c639f674
  - 字节数: 16884；行数: 218
- 执行命令：sh run-upstream-tests.sh <xar-bin-dir> <run-root>（内容含 fixture 构建与环境变量，已存 task-data/libxar-1.8.0.498/run-upstream-tests.sh）
