# xsct 2.3 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-10-09
- 编译器: clang 15
- 状态: built

## 编译步骤

```bash
make -C $SOURCE_DIR -j1 CC=clang \
  CFLAGS="-Wall -Wextra -std=c99 -O2 -I$LIBX11_INC -I$LIBXRANDR_INC -I$XORGPROTO_INC -I$LIBXRENDER_INC" \
  LDFLAGS="-L$LIBX11_LIB -L$LIBXRANDR_LIB"
```

## 对话记录

### 对话 #1 [2026-10-09]

- 问题: 编译期 `X11/Xatom.h` / `X11/extensions/Xrender.h` 未找到
- 操作: 显式加入 xorgproto/2025.1 与 libxrender/0.9.12 传递依赖并加入 include 路径
- 结果: 编译通过

### 对话 #2 [2026-10-09]

- 问题: libx11/1.8.13 与 libxrandr/1.5.5.1 强制的 libx11/6.4.0 版本冲突
- 操作: 统一依赖到 libx11/6.4.0
- 结果: 依赖图解析通过

### 对话 #3 [2026-10-09]

- 问题: xsct 无 DISPLAY 时 `XOpenDisplay(NULL)` 失败导致无法执行业务；旧 test_package 仅有静态字符串断言，不满足「鸿蒙特有测试须非断言」
- 操作: 重写 test_package 为 `consumer_test.sh`：A 节闭包真实 dlopen 加载（非断言），B 节原生真实执行并校验上游 `EXIT_FAILURE` 语义
- 结果: `ALL CONSUMER TESTS PASSED`，conan create / W3 全绿

### 对话 #4 [2026-10-10]（CI 失败修复）

- 问题: CI（PR #15143 build #80198）test_package A3 失败：`OSError: Error loading shared library libX11.so.6: Permission denied` → `FAIL: A3: 依赖闭包在本机真实加载失败`
- 根因: A3 用 `python3 ctypes dlopen` 验证闭包，而 conan 宿主 python 因环境而异——本地为 `usr/local/bin/python3`（不受限，dlopen 成功），CI worker 为 HNP 安装的 `/data/service/hnp/bin/python3`（受限 linker namespace，dlopen 缓存路径的库被拒 EACCES）。exec 时按 DT_NEEDED 加载不受此限，故本地绿、CI 红
- 操作: 移除对宿主 python 的依赖——A 节改为 readelf 静态闭包校验（并打印 DT_NEEDED 清单），「闭包真实加载」由 B1/B2 原生执行强制校验（上游 `main()` 首行即 `XOpenDisplay(NULL)`，加载器必须完整解析整个闭包含传递依赖与重定位才能进入 main；缺库时加载器以 127 退出并输出 shared library 错误，均硬失败）；conanfile.py 不再传 `sys.executable`
- 结果: 本地 `conan create --build='xsct/*'` 全绿（A/B1/B2 PASS，`ALL CONSUMER TESTS PASSED`），测试结果不随「哪个 python3 运行 conan」而变化

## 上游测试清点（R51 三步法）

xsct 为纯 Makefile 项目，**无上游自动化测试**：
- 源码树无 `tests/` / `test/` 目录
- `Makefile` 无 `check` / `test` 目标
- 上游仓库无 CI 测试配置

→ `upstream_tests: []`；test_package 不替代上游测试统计。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `X11/Xatom.h` 未找到 | Xatom.h 在 xorgproto 包中，非 libx11 | 显式添加 xorgproto/2025.1 依赖并添加到 include 路径 |
| 2 | `X11/extensions/Xrender.h` 未找到 | Xrender.h 在 libxrender 包中 | 显式添加 libxrender/0.9.12 依赖并添加到 include 路径 |
| 3 | xsct 无 DISPLAY 无法完成色温设置 | `XOpenDisplay(NULL)` 失败 | 消费者用例改为：A 节**闭包真实 dlopen 加载**（非断言）+ B 节**原生真实执行**并校验上游 `EXIT_FAILURE` 语义 |
| 4 | 版本冲突 libx11/1.8.13 vs 6.4.0 | libxrandr/1.5.5.1 强制依赖 libx11/6.4.0 | 统一使用 libx11/6.4.0 |
| 5 | 鸿蒙特有测试须为非断言 | test() 曾仅有静态字符串断言 | 新增 `consumer_test.sh`：闭包真实加载 + 原生执行，全部以退出码判定 |
| 6 | CI A3 `dlopen libX11.so.6: Permission denied` | HNP python3（CI worker 宿主）受限 linker namespace 拒绝对缓存路径的库 dlopen；本地 usr/local python 不受限故本地绿 CI 红 | 移除 python dlopen：A 节 readelf 静态闭包校验，真实加载由 B1/B2 原生执行强制校验（加载器须完整解析闭包才能进 main） |

## 源码修改

无修改 — 纯 Makefile 参数覆盖构建。

## 依赖版本

| 依赖 | 版本 |
|------|------|
| libx11 | 6.4.0 |
| libxrandr | 1.5.5.1 |
| libxrender | 0.9.12 |
| xorgproto | 2025.1 |

## 消费者用例（鸿蒙特有非断言测试）

`test_package/consumer_test.sh`（由 conanfile.py 以 `sh` 调用）：

- **A. 鸿蒙特有非断言测试（静态）**
  - A1 `readelf -h`：xsct 为 ELF / AArch64 原生可执行文件
  - A2 `readelf -d`：DT_NEEDED 闭包含 libX11.so.6 / libXrandr.so.2（并打印闭包清单）
- **B. 端到端消费者用例（原生进程真实执行，承担闭包真实加载证明）**
  - B1 无 DISPLAY 执行 xsct → 加载器完整解析闭包进入 main → 运行到 X11 运行时路径 → 上游语义返回 `EXIT_FAILURE(1)`（缺库时 exit=127 + shared library 错误，硬失败）
  - B2 `DISPLAY=:9999` 执行 xsct → 优雅失败（非信号终止 / 非加载失败）
  - 设计约束：不依赖 conan 宿主 python3（HNP python3 受限 namespace 的 dlopen 会被 EACCES 拒绝，exec 按 DT_NEEDED 加载不受限）

## 验证结果

```bash
# conan create（强制重建 --build='xsct/*'）
# recipe: xsct/2.3@ohpcd/stable#5324f0d6596da4ea9ea1ef34dd7eca7a
# binary: efeb3e23e6902c9f5d6f13aee70025936e533fde
# result: PASS
# test_package: consumer_test.sh -> ALL CONSUMER TESTS PASSED

# W3 本地 CI
# Success: 1/1 (100%)
# L0/L1/L2/L4/L5: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/xsct-2.3-ohos-aarch64.tar.gz | 38KB | 发布包 |

## 注意事项

- xsct 需要 X 显示器才能完成色温设置（`XOpenDisplay`）；无头环境下消费者用例改以**闭包真实加载 + 原生执行到 X11 路径**验证
- 构建通过 make 命令行参数覆盖，不修改上游 Makefile
---

**编译结束**: 2026-10-09 16:47
**最终状态**: built
