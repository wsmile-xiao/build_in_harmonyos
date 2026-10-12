# OHOS NLS/gettext：libintl 空壳一类共性问题

> 知识库拓展条目（解决的是一类共性问题，不是单个库的补丁）。
> 适用对象：任何在 C/C++ 里调用 gettext 家族函数（`gettext`/`dgettext`/`ngettext`/…）的三方库。
> 交付物：本文档 + 检测脚本 `detect-libintl-stub.sh` + 样例演示库 `sample/`。

## 1. 问题定位

GNU/glibc 把 libintl 并进了 libc：`gettext`、`dgettext` 等符号就在 libc 里，于是历史代码常写成「不包含 `<libintl.h>` 直接调用」——C 语言靠隐式声明过编译，C++ 里若经由其它头间接可见也能过。这类源码在 GNU 平台能编能跑，迁到 OHOS(musl) 立刻变形：

| 写法 | GNU/glibc | OHOS/musl（sysroot 无 libintl） |
|---|---|---|
| 不 include 直接调用（.c） | 隐式声明告警，链接成功 | 隐式声明告警/失败，链接失败（符号不存在） |
| 不 include 直接调用（.cpp） | 视间接可见性 | `use of undeclared identifier 'dgettext'` 编译失败 |
| `#include <libintl.h>` | 有头有库 | sysroot 的头是**空壳**：存在但不声明，仍然失败 |
| 依赖 gettext 包 + include + `-lintl` | 可 | 可（策略①） |

关键点（最容易踩）：**OHOS sysroot 内的 `<libintl.h>` 是空壳**——`__has_include(<libintl.h>)` 判定为真，但头里没有 `dgettext` 的声明。因此「用 `__has_include` 做守卫」并不能解决问题，必须拿到**真实头**（gettext 包，或自带兜底头），并在链接期带上 libintl（或使用恒等实现）。

## 2. 典型报错特征（error_signature）

- `error: use of undeclared identifier 'dgettext'` —— C++ 最常见（schroot 1.6.13 实际命中）
- `error: implicit declaration of function 'gettext'` —— C 代码，`-Werror` 下直接硬失败
- `fatal error: 'libintl.h' file not found` —— 头完全缺失
- `undefined reference to 'dgettext'` / `cannot find -lintl` —— 编译过、链接失败

## 3. 检测脚本

```bash
bash knowledge/operations/ohos-nls-libintl/detect-libintl-stub.sh \
    --src <源码根> [--src <另一个根> ...] [--json] [--quiet] \
    [--clang <clang 路径>] [--sysroot <sysroot 路径>]
```

做两件事：

1. **环境探针**（默认目标 `aarch64-linux-ohos`，clang 从 `PATH`/`$HOME/usr/bin` 等候选位置探测，均可用参数覆盖）：`<libintl.h>` 是否真正可编译、`-lintl` 是否可链接、隐式声明写法是否可编译。结论决定扫描结果的定级（目标平台无可用头时，"未包含 libintl.h 的调用"直接判 `blocker`）。
2. **源码静态扫描**：找出「调用 gettext 家族函数但未包含 `<libintl.h>`」的位置，输出 `文件:行 | 符号 | 级别 | 同文件调用数 | 说明`，并在末尾给出三条策略。

退出码契约：

| 码 | 含义 |
|---|---|
| `0` | 无 blocker / warn（info 不阻断） |
| `2` | 用法错误（参数缺失等） |
| `10` | 存在 blocker 或 warn —— 可直接当预检闸用 |

实现细节：提供者文件（`libintl.h` 本体、自行声明或实现 gettext 家族的头）**不算调用方**；本地头一跳解析的候选根为「每个 `--src` 目录本身 + 其 `include/`」，因此兼容 `src/`、`include/` 两种布局。

## 4. 三条处理策略

| # | 策略 | 做法 | 适用 / 代价 |
|---|---|---|---|
| ① | 依赖 gettext 包 | 配方 `self.requires("gettext/<ver>")`；在调用 TU 或它的（包装）头补 `#include <libintl.h>`；链接期带上 `-lintl` | 需要真实 .mo 翻译目录时首选；代价是多一个依赖 |
| ② | 关闭 NLS | `--disable-nls` / `-DENABLE_NLS=OFF` / 置空 `HAVE_LIBINTL_H`（配方 `generate()` 里显式关掉） | 上游有开关且不要求本地化；代价是失去 i18n |
| ③ | 自带兜底头 | 提供最小 `libintl.h`（函数声明 + 恒等实现），不引入外部依赖 | 无本地化需求、平台无可用头；代价是自维护一份头 |

策略① 的落地要点：

- **补 include 的位置优先选封装头**，调用点不用改（schroot 1.6.13 即如此：`sbuild-auth-pam.cc`、`schroot-base-run.h` 各补一行）。
- 只加 `#include <libintl.h>` 还不够，**链接期必须有 libintl**：配方要注入 gettext 的 include 目录与 `-L<gettext libdir> -lintl`，否则报 `undefined reference to 'dgettext'`。
- 依赖的头/库目录若不被工具链自动带入（本项目实测：Conan 导出的绝对路径在干净 CI 上可能失效），应在 `generate()` 中显式注入；避免写死构建机绝对路径。

## 5. 样例演示库 `sample/`

```text
sample/
├── conanfile.py             # 选项 nls_mode=none|gettext|shim（默认 shim）
├── CMakeLists.txt           # 三种模式对应的编译/链接配置
├── include/i18n-demo/i18n.h # 修复态封装头（含 #include <libintl.h>）
├── src/i18n.cpp             # 调用 dgettext / dngettext
├── src/i18n-demo.cpp        # CLI：i18n-demo-cli <domain> <msgid> [n]
├── states/bad/i18n.h.in     # 缺陷态模板（缺 include）
├── states/good/i18n.h.in    # 修复态模板（补 include）
├── shim/include/libintl.h   # 策略③ 兜底头（声明 + 恒等实现）
├── test_package/            # 消费者用例（链接库 + 实跑 CLI 校验 gettext 语义）
└── demo.sh                  # 一键演示：缺陷态 → 修复态
```

用法：

```bash
cd knowledge/operations/ohos-nls-libintl/sample
bash demo.sh                      # 只跑检测（秒级）
bash demo.sh --create             # 追加 conan create：none 应失败 / shim 应成功
bash demo.sh --create --gettext   # 再追加策略① 对比（环境相关，仅信息展示）
```

`demo.sh` 三阶段：① 缺陷态（`states/bad`）检测器应报 `rc=10`，`-o nls_mode=none` 的 `conan create` 应失败且日志含 `dgettext`；② 修复态（`states/good`）检测器应报 `rc=0`，`-o nls_mode=shim` 的 `conan create` 应成功并跑通 `test_package`；③（可选）策略① `nls_mode=gettext` 的结果只作信息展示，不参与判定（是否可用取决于环境是否提供真实 `libintl.h` + `libintl`）。脚本通过 `OHOS_PROFILE` 覆盖 profile 路径、`TMPDIR` 覆盖日志目录，全程不使用 `head` 截断管道（避免 SIGPIPE 误判），过程输出重定向到 `$WORK/demo.log`。

## 6. 实测证据（本机环境，2026-10）

| 项目 | 命令 | 结果 |
|---|---|---|
| 缺陷态检测 | `detect-libintl-stub.sh --src sample`（`states/bad`） | `rc=10`，`summary {"blocker":0,"warn":1,"info":0}` |
| 修复态检测 | 同上（`states/good`） | `rc=0`，`summary {"blocker":0,"warn":0,"info":1}` |
| 缺陷态构建 | `conan create . -o nls_mode=none` | `rc=1`，日志含 `use of undeclared identifier 'dgettext'` |
| 修复态构建 | `conan create . -o nls_mode=shim` | `rc=0`，`test_package` 通过（链接库 + 实跑 CLI） |
| 端到端 | `bash demo.sh --create` | 结论 `PASS`（三处 ✓ / 零 ✗） |

环境探针的旁证：本机 Conan 缓存里唯一带 `dgettext` 声明的 `libintl.h` 来自 glibc 包，目标平台（`aarch64-linux-ohos`）侧没有可用头；这与 OHOS sysroot `<libintl.h>` 空壳的结论一致——因此策略①（依赖 gettext 包拿真实头）或策略③（自带兜底头）是必需动作，只补 `#include` 不够。

同类真实案例：schroot 1.6.13 采用策略①——补丁 0005/0006 在 `sbuild-auth-pam.cc`、`schroot-base-run.h` 补 `#include <libintl.h>`，配方侧注入 gettext 头目录与 `-L<gettext libdir>`、`-lintl`，之后编译与测试全绿。

## 7. 适配检查清单（复用前逐项核对）

1. 检测器在缺陷态给 `rc=10`、修复态给 `rc=0`，且修复态**无假阳性**（提供者头不算调用方）。
2. 脚本不写死绝对路径：clang / sysroot / 日志目录均可由参数或环境覆盖，默认走候选清单。
3. 脚本不使用 `head` 截断管道（避免 SIGPIPE 把成功判成失败），日志一律重定向到文件。
4. 样例库在干净缓存下可复现：`CCACHE_DISABLE=1` + `--build=missing`，不使用本地缓存产物。
5. `test_package` 实质依赖被测包：链接 `libi18n-demo` 并实际执行其安装的 CLI，而非空壳断言。
6. 三条策略中至少策略①、③给出可直接照抄的代码形态（include + 链接 / 兜底头）。
7. 文档中的示例命令可复制即用，路径相对仓库根（本文档示例 `--src sample` 即如此）。
8. 与既有知识条目互链：库侧实例见 schroot 1.6.13 的 `schroot-1.6.13-ohos-libintl-stub` 等草稿条目。

## 8. 关联知识与扩展维护

- **关联条目**：`knowledge/drafts/schroot-1.6.13-ohos-libintl-stub.*`（库侧实例：补 include 的必要性）、`schroot-1.6.13-conan-dep-binary-skip.*`（依赖二进制被 Skipped 的表象）、`schroot-1.6.13-cmake4-no-findboost.*`（同类"依赖头/库未进编译行"问题）。
- **横向扩展**：把 `CALL_RE`/`DEF_RE` 的家族函数表替换掉，即可复用到其它"空壳头/裁剪头"类问题（例如不同 sysroot 下被裁掉的 `pty.h`、`termios.h` 子集）；探针部分把 `--target` 与头名参数化后同样适用。
- **自适应**：目标平台若补齐 libintl，环境探针会自动转为可用，扫描结果不再升级为 `blocker`（工具按环境自适应，无需改文档）。
- **维护责任**：新增 gettext 家族函数（如 `pgettext`）时，同步更新 `CALL_RE`/`DEF_RE` 与脚本内的函数表。
