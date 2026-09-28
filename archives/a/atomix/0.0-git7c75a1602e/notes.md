# atomix 0.0-git7c75a1602e 适配笔记

## 编译环境
- 构建系统: header-only（无构建系统；上游仅单文件 atomix.h + 示例 test.c）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (OHOS SDK /data/service/hnp/bin/clang)
- 状态: built（conan create 全门禁本地验证通过，未 pubupload，待 CI 发布）

## 编译步骤

header-only 库，无 configure/make。配方 conanfile.py（v12.21 header-only 变体 A）：
1. source(): 下载官方 GitHub archive (7c75a1602e) 并核验 SHA-256
   `f39449fcd69e027f07a7c2776bc0ee25a04a6eb1d13566f741bd0d304233ed5c`
2. package(): 复制 atomix.h -> include/，LICENSE -> licenses/
3. build(): 空实现（R34：不伪造编译日志）
4. package_id(): info.clear()（单一 package_id）
5. test_package: CMake 消费者测试 test.c（真实调用公开 API 并断言输出）

```bash
python3 scripts/ohc-run.py conan-verify atomix 0.0-git7c75a1602e
# → G0-G5 + L2/L4/L5 全部 PASS
```

## 上游测试枚举台账（完整枚举）

上游源码树（tag 7c75a1602e）全部文件：
`LICENSE README.md atomix.h libs/README libs/miniaudio.h libs/stb_vorbis.h mu.ogg so.ogg test.c`

| 条目 | 类型 | 是否独立上游用例 | 说明 |
|------|------|------------------|------|
| test.c | 上游示例/基准 CLI（demo + benchmark 混合程序） | 否（示例，非断言型用例） | 无断言框架、无 TEST_CASE/宏注册；编译后由调用方手动观察输出，含 ALSA/音频后端 demo。README 明确其为 example。按规则"样例和基准不得误算为独立用例" |
| atomix.h | 库头文件（含实现，ATOMIX_IMPLEMENTATION/STATIC） | 否 | 单文件库本体 |
| libs/miniaudio.h、stb_vorbis.h | 可选后端聚合头（仅 test.c 使用） | 否 | 上游捆绑的第三方后端 |
| mu.ogg、so.ogg | 测试素材 | 否 | 音频素材 |
| libs/README | 说明 | 否 | 文档 |

**源码声明测试总数 source_declared_total = 0**（上游无可计数的独立用户测试用例；
test.c 属示例/基准，见上表逐项分类理由）
**configured_executable_total = 1**（当前 OHOS 配置实际实例化的可执行用例：
test_package 消费者可执行 test_atomix，由 CMake add_test 注册）
**executed_passed_total = 1**（test_atomix：7 项 CHECK 断言全部真实运行通过）
**失败数 = 0；未运行/未实例化 = 0**

### 上游示例 test.c 实跑记录（额外证据，不计入用例数）

- 命令：`clang -O2 -DATOMIX_NO_SSE -o atomix-test test.c`（aarch64 无 SSE，
  README 说明 SSE 为默认优化；arm64 须用文档化选项 ATOMIX_NO_SSE）
- cwd：上游源码根 `/storage/Users/currentUser/tmp/atomix-src`
- 编译退出码：0（仅 1 条 dangling-else 警告）
- 运行：`./atomix-test mu.ogg so.ogg` → `<BENCHMARK BEGIN>` 256/One 混音吞吐基准 + `<DEMO BEGIN/END>` 完成，退出码 0
- ALSA 后端不可用属预期（无音频设备/snd config），demo 段自动跳过，不影响基准段完成

> 说明：上游 SSE 路径（ATOMIX_NO_SSE 未定义）在 OHOS aarch64 上不可用——
> xmmintrin.h 仅 x86/x64，属架构事实而非当前库缺陷；消费者/示例均以
> ATOMIX_NO_SSE 编译运行，符合上游文档化配置。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 "Package type is 'library', but no 'shared' option" | 生成模板按编译型库声明 | package_type 改 header-library |
| 2 | test_package 引用 include 路径不存在 | copy(dst="include") 相对路径落入 build 目录 | dst 显式 join(package_folder,"include")（对齐 array-hash 成功配方） |
| 3 | 消费者测试 StopAll 断言失败 | 上游原子淡出语义：STOP 后 fade 帧内音量渐弱，非立即静音 | 先 mix 一窗耗尽 fade(64帧) 再断言后续输出全零（修正错误测试预期，非掩盖缺陷） |
| 4 | test.c 默认编译报 xmmintrin 仅 x86 | aarch64 无 SSE | 文档化 -DATOMIX_NO_SSE 编译运行 |

## 依赖版本

无第三方运行时依赖（header-only，仅标准库 + stdatomic.h；test.c 可选捆绑 miniaudio/stb_vorbis）。

## 验证结果

```bash
conan-verify atomix 0.0-git7c75a1602e   # G1-G5/L2/L4/L5 全 PASS
/root/tmp/atomix-test mu.ogg so.ogg     # 基准段完成，退出码 0
ctest test_atomix                       # 1/1 PASS（消费者 7 断言全过）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/a/atomix/0.0-git7c75a1602e/conanfile.py | header-only 配方 |
| archives/a/atomix/0.0-git7c75a1602e/conandata.yml | 官方 GitHub archive + SHA-256 |
| archives/a/atomix/0.0-git7c75a1602e/test_package/ | 消费者测试（真实 API 断言） |

## 注意事项

- header-only 库：消费者需自行 `#define ATOMIX_IMPLEMENTATION`（多 TU）或 `ATOMIX_STATIC`（单 TU）。
- OHOS arm64 必须用 `ATOMIX_NO_SSE`（无 SSE 内建）；不影响功能，仅混音性能约 4 倍差距（上游文档原文）。
- 非 CLI 库（无 bin 产物），不生成 commands.json。
---

**编译结束**: 2026-09-27 21:44
**最终状态**: built
