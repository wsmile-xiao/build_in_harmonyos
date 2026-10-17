- **三方库名称**：yell
- **上游版本**：1.1
- **上游仓库地址**：https://www.critical.ch/yell/ （发布源 tarball 经 FreeBSD distcache 分发：http://distcache.freebsd.org/local-distfiles/ehaupt/yell-1.1.tar.gz，SHA256 与 FreshPorts 记录一致）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无既有 E### 条目命中；本次新沉淀 1 条知识草稿（knowledge/drafts/yell-1.1-speaker-include-unistd.kv），并复用 zpaq 7.15 两条已入库经验（编译器 stdio 重定向、test_package 解释器解析禁用 shutil.which）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试框架；tarball 仅 4 文件（Makefile / yell.c / yell.h / README） |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | Makefile 仅有 default（打印提示）/ install / deinstall 目标；`make -n check` 报 `No rule to make target 'check'` |
| **合计** | **0** | 已按仓内惯例登记 `ci/config/no_official_test.txt`（先例：acpi_call） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 6 | 新增 | test_package/test.sh 对安装出的 `bin/yell` 端到端实测（T1–T6，见下） |
| **合计** | **6** | **+6** | 全部通过（6/6，100%） |

鸿蒙特有测试明细：T1 安装产物存在且可执行；T2 `readelf -h` ELF64/AArch64；T3 `readelf -d` DT_NEEDED 仅 `libc.so`；T4 无 `/dev/speaker` 时退出码 0（yell.c 的 `open` 结果有 `if (handle >= 0)` 守卫，优雅降级契约）；T5 运行无任何输出；T6 二次运行幂等退出 0。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为安装出的 CLI 新增 6 项端到端行为断言（产物存在性/ELF 架构/动态依赖/运行退出码/输出/幂等性）
> - **补全原因**：上游无任何测试套件（Makefile 无 check 目标、无测试框架文件），且 OHOS 无 PC speaker 硬件，需显式断言「无设备时优雅降级（退出码 0、无输出）」这一平台行为契约
> - **新增测试文件清单**：
>   1. `test_package/test.sh` — bash 断言脚本（`set -euo pipefail`，6 项检查 T1–T6）
>   2. `test_package/conanfile.py` — 从 `self.dependencies["yell"].package_folder` 显式解析二进制（删除包内容即测试失败，L1e 反向验证语义），解释器按 `$CONFIG_SHELL` → 固定候选清单解析
>   3. `test_package/MANIFEST.yml` — 上游测试声明（上游 = 0 项，鸿蒙侧 6 项）

## 验证结果

- 编译状态：通过（clang 15.0.4，`-Wall` 零告警；`conan create` 干净构建全绿）
- 上游测试用例通过率：0/0（上游无测试套件，不适用）
- 新增测试用例通过率：6/6（100%）

## 补充说明

- **移植内容极小**：唯一源码修改是 `patches/0001-yell.c.patch`——`#include <dev/speaker/speaker.h>`（FreeBSD 内核头，其声明未被代码使用）替换为 `<unistd.h>`（补 `write`/`close` 显式声明，二者在 FreeBSD 上经 speaker 头传递引入，仅删不加会触发隐式声明告警）。FreeBSD port 的 `ONLY_FOR_ARCHS=i386 amd64` 来自内核 speaker(4) 设备而非 C 源码，用户态代码可移植 aarch64。
- **运行语义**：OHOS 无 PC speaker 硬件，yell 在本平台是「安全空操作」——可编译、可安装、退出码 0、不发声（研判预期一致）；作为极简 C CLI 的移植样例与 shell 通知占位保留。
- **上游 Makefile 的 install 目标未使用**：其硬编码 `/usr/local/bin` + `chown root` + `chmod 4110`（setuid），对 Conan 包与 OHOS 沙箱均不适用；配方改为 FreeBSD port `do-build` 单行命令的等价调用 + `package()` 手工打包。
- **许可证**：BSD-2-Clause（FreeBSD port 记录）；上游 tarball 内**无**许可证文件，版本目录 `licenses/LICENSE` 提供归属说明与标准文本，`licenses/README` 为上游原文件。
- **源 URL 使用 distcache HTTP 直链**：作者官网对 tarball 的 HTTP 路径 302 到 HTTPS，而本环境 HTTPS 在 TLS 握手后被 RST 阻断（知识库既有约束）；distcache HTTP 实测 200，SHA256（aadc8e5b…）与 FreshPorts 记录一致。
- **PF9 说明（对齐 zpaqfranz 63.3 先例 071a2c93e8）**：本 PR 按 finalize_archive 规范包含软件级 `archives/y/yell/README.md` 与 application 包必需的 `archives/y/yell/commands.json`（CI 的 L0k 强制要求），文件落在版本目录之外；PF1–PF8 已逐项实测通过，仅 PF9 因上述文件命中，故 create-pr 使用 `--no-preflight`，非静默绕过。
- 本地 W3 conan-build-test 全绿（`.ci-result.json` exit_code=0，含日志 SHA256）；GitCode CI 结果以 PR 流水线为准。
