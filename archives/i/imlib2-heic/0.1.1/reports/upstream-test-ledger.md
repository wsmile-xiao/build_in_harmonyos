# imlib2-heic 0.1.1 上游测试双口径台账（R02 终态）

任务：imlib2-heic-0.1.1-r02-pc4-16-20260919T055418Z（R02，高难度挑战）
源码：官方 tag v0.1.1（`git ls-remote ... refs/tags/v0.1.1` → 8362aa93d4aa1826d1293b805c4dd10b9eb206b8，与 R01 一致）
tarball：https://codeload.github.com/vi/imlib2-heic/tar.gz/refs/tags/v0.1.1
SHA-256：8e7771903ef2e8718e17f228e7fcdb1aeb889e57c9d846b6708d45b6310a3856
（R02 重新下载 `curl -sSL -o imlib2-heic-0.1.1.tar.gz` 后 `sha256sum` 与期望值逐字节一致；见 R02 最终报告 source_audit）
解包目录：/storage/Users/currentUser/tmp/builds/imlib2-heic-0.1.1.src/imlib2-heic-0.1.1

## 一、完整文件清单（可复制枚举，8 个文件，R02 重建后复核）

枚举命令：
```sh
tar tzf imlib2-heic-0.1.1.tar.gz | sed 's|^imlib2-heic-0.1.1/||' | grep -v '^$' | sort
tar tzf imlib2-heic-0.1.1.tar.gz | grep -iE 'test|spec|bench|fixture|sample|example|check|\.t$|run'   # exit=1 无命中
grep -nE '^[a-zA-Z_]+:|\.PHONY' makefile   # 仅 all/clean/install/uninstall
```

| 文件 | 类型 | 是否独立上游测试用例 | 分类理由 |
|---|---|---|---|
| makefile | 构建脚本 | 否 | 目标仅 all/clean/install/uninstall，**无 check/test 目标**，未注册任何测试 |
| commands.mk | 构建辅助（变量默认值） | 否 | 上游 makefile include 的公共变量定义（CC/RM/INSTALL 等默认值） |
| loader_heic.c | 生产实现源文件 | 否 | 唯一 C 源文件，是 imlib2 loader 插件实现（load/save/formats 三个导出函数） |
| imlib2_common.h | 头文件（拷贝自 imlib2 loader API） | 否 | 定义 ImlibImage/ImlibLoader 结构等，被 loader_heic.c/loader.h 包含 |
| loader.h | 头文件 | 否 | 声明 load/save/formats 导出接口 |
| README.md | 文档 | 否 | 构建/部署说明 |
| LICENSE | 许可文件 | 否 | BSD-3-Clause |
| .gitignore | 配置 | 否 | 版本控制忽略规则 |

结论：上游**不存在**任何测试源文件、测试脚本、fixture、样例、基准、测试框架注册项或构建目标测试入口（无 tests/ 目录、无 ctest、无 make check、无 meson/autotools 测试注册）。

## 二、统计口径与逐项映射（R02，构建成功后核验）

- `source_declared_total`：**0**（官方 tag 源码中按可复制枚举规则发现的测试声明总数）
- `configured_executable_total`：**0**（当前 OHOS 配置实际实例化/注册的独立可执行用例数）
- `executed_passed_total`：**0**
- 失败数：**0**（无测试用例可失败）
- 未运行/未实例化数：**0**（无被声明而未能运行的用例）

源码声明（0 项）→ 构建目标（无测试目标）→ 测试注册（无）→ 实际执行日志（无）映射为空集，无需逐项映射。

全量通过率：通过数/全量发现数 = 0/0（上游无测试声明，无分母可除；高难度挑战硬门禁
"实际通过数必须等于源码声明总数" 以 0=0 满足）。当前配置可执行集合通过率另列 0/0（100% 空集）。

## 三、与 R01 的差异与恢复条件（依赖门禁已解除）

R01 该台账在依赖门禁（imlib2/1.12.6 未发布）下完成枚举，结论同为 0；本轮 R02：
1. 依赖解析已解除：imlib2/1.9.1（revision 5d819e4fd242fc0ee250c554b7f43788，`conan download` 成功）、
   libheif/1.22.2、libde265/1.0.18 均已在 ohpcd 复查可用（详见 R02 最终报告依赖终态复核命令）。
2. 实际构建已成功：`conan create`（conan-verify G2）PASS，heic.so 产物生成并进入包。
3. 枚举在构建成功状态下再次复核，结论不变：上游确实无测试基础设施，0 用例是真实枚举结果，
   非"未运行/跳过"所致。因此不存在"可运行但失败/未运行/硬阻塞"的入口需要恢复。
4. 恢复条件：不适用（无未运行入口）。若后续上游新增测试，需按本台账口径重新枚举与映射。
