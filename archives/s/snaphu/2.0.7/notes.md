# snaphu 2.0.7 适配笔记（HarmonyOS PC · 裸 Makefile CLI）

## 定位
- 产出 CLI 工具 `bin/snaphu`（SNAPHU：InSAR 相位解缠），`package_type = "application"`。
- 上游 install 目标只往 `/usr/local/bin` + `/usr/local/man` 拷贝、不可用，`package()` 手工安装并 chmod 0755。

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang（取自 profile `tools.build:compiler_executables`，R33）
- CONAN_HOME: `~/tmp/ch/home-q5m-snaphu`（交接包指定）
- 状态: built

## 源码
- https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-v2.0.7.tar.gz
- sha256: `c03ac126f9a964321bb5d6fb5b4004728368da268d7cb8407bb295a8abe5b262`（真机 curl + sha256sum 实测）
- tarball 结构：`README`、`README_releasenotes.txt`、`bin/`、`config/`、`man/man1/`、`src/`。

## W0/W0b
- 依赖预检：只链接 `libm`，无三方依赖；`archives/s/snaphu` 无同版本；平台任务 10755 已在本账号名下（status=assigned）。
- `conan-init` 把构建系统误判为 **autotools**（实为裸 Makefile），生成的骨架三处错位，已按 R33/R38 重写：
  1. 无 configure → 走 custom make，`make -C <src>/src`；
  2. 是命令行工具而非库 → `package_type = "application"`，并补 `archives/s/snaphu/commands.json`（PF8）；
  3. 上游 Makefile 三处硬编码必须命令行覆写：`CC = cc`（设备无 cc）、
     `CFLAGS = -arch x86_64 -O3 -Wall`（`-arch x86_64` 是 macOS 专用，clang 会当成目标架构）、
     `BINDIR = ../bin`。

## 上游测试账本（R51）
- 上游**无任何自动化测试**：`src/Makefile` 目标只有 `all/gdebug/install/clean/clobber`，无 `check`/`test`；
  tarball 全树无测试源文件。
- `N_static = 0`、`N_registered = 0`、`N_executed = 0`（如实申报，不虚构上游测试；
  登记表原备注"算法库带测试数据"不实，已在登记表更正）。
- 消费者测试（test_package）**1 程序 / 3 场景 / 14 断言**：驱动真实 `snaphu` 二进制——
  ①`-hv` 退出码 0 + 版本横幅 + usage；②已知答案（全零相位 → 输出全零、恰 R*C*4 字节）；
  ③缠绕斜坡 → 退出码 0、R*C*4 字节、样本全有限、与输入不同且非恒定场、stdout 含 "Program snaphu done"。

## 探索构建（真机实测）
1. `make CC=clang CFLAGS="-O3 -Wall" BINDIR=$PWD/binout` → 223680 B aarch64 ELF，`snaphu -hv` 正常打印 usage。
2. CLI 行为实跑：16x16 float32 合成缠绕相位 → `snaphu in.flt 16 -o out.flt -d` 退出 0、写出 1024 B、
   stdout 收尾 `Program snaphu done`。
3. 已知答案探针：全零相位输入 → 输出每个样本精确 0.0（消费者测试固化该断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-init` 生成 autotools 骨架，`autotools.configure()` 必失败 | 上游无 configure，是裸 Makefile | 重写为 custom make 配方（R33/R38） |
| 2 | 透传上游 CFLAGS 时 clang 报未知架构 | `-arch x86_64` 为 macOS 专用 flag | `build()` 命令行覆写 `CFLAGS="-O3 -Wall"` |
| 3 | 设备无 `cc` | 上游 `CC = cc` 硬编码 | 从 profile `tools.build:compiler_executables` 取 clang（R33） |
| 4 | 上游 install 目标指向 `/usr/local`，无 root 不可用 | 上游只面向本机安装 | `package()` 手工拷贝 `bin/snaphu` + man 页并 chmod 0755 |

## 源码修改
- 无补丁（`patches: {}`）。

## 依赖版本
- 无三方依赖；系统库 `libm`。

## 验证结果

```bash
export PATH=$HOME/.local/bin:$PATH TMPDIR=$HOME/tmp \
       CONAN_HOME=$HOME/tmp/ch/home-q5m-snaphu SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
cd ~/qzy/Q-5m-snaphu-2.0.7
python3 scripts/ohc-run.py conan-verify snaphu 2.0.7
```
（结果见 `reports/conan-verify-report.md`；消费者测试 14/14 断言通过）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/snaphu` | 相位解缠 CLI（aarch64/OHOS ELF） |
| `share/man/man1/snaphu.1` | 上游 man 页 |
| `commands.json` | R38/PF8 命令清单（type=tool） |

## 注意事项
- 上游 tarball 的 `config/` 只是运行期配置模板，本包不安装；`snaphu.conf` 由使用者按需生成。
---

**编译结束**: 2026-09-21 08:23
**最终状态**: built
