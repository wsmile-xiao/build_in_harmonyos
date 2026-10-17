# 适配前置风险扫描（知识库拓展交付物）

本目录是**一类共性问题**的通用处置套件，不针对单个库：

> 上游「源码发布包 + 自有构建脚本」在 **Conan 交叉编译 + CMake 4.x + 干净 CI** 环境下，
> 存在三类可静态预检、且必然造成失败的风险。把这三类在动手适配前变成清单，
> 再按机械策略处置，可把「编译—报错—猜—重试」的循环消掉。

| 产出物 | 文件 | 说明 |
|--------|------|------|
| 检测脚本 | `prescan_risks.py` | 纯 Python 标准库、只读、无写死路径；文本 / `--json` 双输出；退出码 0/1/2 |
| 处理策略 | `STRATEGY.md` | 每类风险：现象原文 → 根因 → 识别 → 处置（首选 + 备选 + 反面案例）→ 验证 |
| 复现脚本 | `reproduce.sh` | 干净环境复现三类风险 + 处置后验证；日志一律落文件（不接管道 head，规避 SIGPIPE） |
| 样例演示库 | 本包（securefs 0.13.1） | 三类风险全中，`conanfile.py`/`conandata.yml`/`patches/` 逐一落地处置 |

三类风险（规则见 `prescan_risks.py` 头部注释）：

| 规则 | 风险 | 一句话处置 |
|------|------|-----------|
| R1 | `cmake_minimum_required` < 3.5 → CMake 4.x 硬拒绝 | 补丁抬到 3.10；或 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| R2 | 上游 archive 包缺 git submodule 源码（gitlink） | 按 gitlink 的固定 commit 补官方 archive 源 + sha256，写进 `conandata.yml` 多源清单 |
| R3 | 构建脚本写死 `/usr/local` 等系统前缀探测依赖 | 补丁去掉写死 `PATHS`；recipe 用 `CMakeToolchain.variables` 注入依赖私有前缀 |

## 快速使用

```sh
# 1) 适配前扫描任意源码目录（可在构建机 / CI / OHOS aarch64 设备上直接跑）
python3 prescan_risks.py /path/to/upstream-src
python3 prescan_risks.py /path/to/upstream-src --json    # 机器可读，便于接流水线
python3 prescan_risks.py /path/to/upstream-src --rules R2  # 只查子模块缺失

# 2) 复现 + 处置验证（日志落 <src 同级>/repro-logs）
sh reproduce.sh --src /path/to/upstream-src
sh reproduce.sh --src /path/to/upstream-src --with-conan   # 追加真实 conan create 门禁
```

退出码约定：`0` = 未发现风险 / 与预期一致；`1` = 发现风险；`2` = 用法错误。

## 环境无关性

* 检测脚本只依赖 Python 3 标准库（`argparse/json/os/re/sys`），不依赖 Conan、CMake、
  网络，也不写死任何绝对路径；在 OHOS aarch64 设备自带 `python3` 上可直接运行。
* 复现脚本的 Conan 缓存路径通过 `conan cache path` 动态解析（不写死 `~/.conan2`），
  日志统一重定向到文件后再读，避免长构建输出被 `head` 截断产生 SIGPIPE。
* 处置动作只使用工具链变量与包内补丁，不向任何共享前缀（`/usr/local`）写入文件，
  因此在共享文件系统的 CI worker 上不会与其他任务互相污染。

## 与样例库的关系

securefs 0.13.1 恰好三类风险全中（实测证据见 `../notes.md`、`../reports/`）：

* R1：`cmake_minimum_required(VERSION 3.0 FATAL_ERROR)` → CMake 4.1.2 首行即拒绝
* R2：`external/{cryptopp,argon2,utf8proc}` 在官方 archive 包里为空目录（三枚 gitlink）
* R3：`find_path(FUSE_INCLUDE_DIR fuse.h PATHS /usr/local/include)` 等写死前缀

处置落地位置：`../patches/`（R1/R3 补丁）、`../conandata.yml`（R2 多源清单）、
`../conanfile.py`（R3 依赖前缀注入 + R2 子模块落位）。
