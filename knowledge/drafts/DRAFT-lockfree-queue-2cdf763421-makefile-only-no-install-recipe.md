# DRAFT-lockfree-queue-2cdf763421-makefile-only-no-install-recipe：仅含 Makefile（无 configure/install/库目标）极简 C 库的 Conan 直编静态库配方

> 知识草稿（DRAFT-lockfree-queue-2cdf763421-makefile-only-no-install-recipe）
> 来源库：lockfree-queue 2cdf763421（supermartian，MIT，Valois lock-free queue 实现）
> 判定：无等价命中 + 跨库可复用 → 路径 B（new_draft）
> 快照：knowledge@main，HEAD 254951ec40ae87030731698397a0ba33a66a0c17

## 问题

上游极简 C 库只带一个 Makefile（`CC=gcc` 硬编码），该 Makefile 只构建**测试可执行程序**：
无 configure、无 install 目标、**无库目标**（本案例 Makefile 仅产出 `test` 可执行文件）。

`conan-init` 按 URL/关键字将构建系统猜为 autotools，生成的 Autotools 模板
（`autotools.configure()` / `make` / `install`）在无 configure、无 install 目标时必然失败。
直接调用上游 `make` 也无法产出 `.a` 静态库——库必须由配方自行构建。

## 根因

1. conan-init 构建系统猜测器对「仅 Makefile」的源码包默认猜 autotools（本案例实测）；
2. 上游 Makefile 无库目标与 install 目标，任何「调用上游 make/make install」的配方方案都不可行；
3. OHOS 为 clang-only 环境，上游 Makefile 硬编码 `CC=gcc` 无意义且 `gcc`/`cc` 不存在
   （环境检查实测 `cc: 未找到`），R33 禁止在 recipe 内裸用 `${CC}` 等 shell 变量。

## 方案

配方完全绕开上游 Makefile：

```python
def generate(self):
    tc = GnuToolchain(self)   # R33: 编译器/标志来自 Conan profile
    tc.generate()

def build(self):
    apply_conandata_patches(self)
    cc = self.conf_info.get("tools.build:compiler_executables", {}).get("c", "clang")
    with chdir(self, self.source_folder):
        self.run(f"{cc} -fPIC -O2 -c pkt_queue.c -o pkt_queue.o", env="conanbuild")
        self.run("ar rcs libpkt_queue.a pkt_queue.o", env="conanbuild")

def package(self):
    copy(self, "pkt_queue.h", self.source_folder, os.path.join(self.package_folder, "include"))
    copy(self, "libpkt_queue.a", self.source_folder, os.path.join(self.package_folder, "lib"))

def package_info(self):
    self.cpp_info.libs = ["pkt_queue"]
```

test_package 使用 CMake `find_package(lockfree-queue REQUIRED)` + 真实 API 往返测试
（init_queue/queue_add/queue_get 100 项验证，R34 非空壳），并另设 HarmonyOS 专项测试
（OHOS 工具链编译，4 producer × 1 consumer × 25000 项，`__OHOS__`/`__aarch64__` 宏打印验证）。

## 验证

- `conan-verify` G2 干净 `conan create` PASS（OHOS aarch64 profile，`os=OHOS arch=armv8 clang 15`）
- finish W3 本地 CI 模拟 PASS（JC/L0/L1/L2/L4/L5）
- `harmonyos_specific_test` 独立运行 2/2 PASS（added=consumed=100000，SHA-256 已记录）
- test_package 消费者测试本地编译运行 OK（exit 0）

## 适用边界

- 仅适用无第三方依赖（或依赖全部 Conan requires 提供）的极简静态 C 库；
- 上游形态必须是「仅 Makefile、无 configure、无 install 目标、无库目标」；
- 需要共享库/动态链接、需要 configure 平台探测、或依赖系统库的库不适用。

## 反例与查重差异

| 条目 | 形态 | 与本草稿差异 |
|------|------|--------------|
| DRAFT-arduinospritzcipher-1.2.0-no-build-family-manual-compile | 无任何构建系统（连 Makefile 都没有） | 本稿有 Makefile 但无库/install 目标 |
| DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode | Makefile recipe 体内硬编码 gcc（无 CC 变量），仍需调用上游 make | 本稿上游 Makefile 有 CC=gcc 变量但无库目标，配方不调用上游 make |
| DRAFT-dmc_unrar-1.8.0-single-file-c-direct-compile | stb 风格单文件（.c 内含头+实现） | 本稿为分离的 .c/.h 多文件 + Makefile |
| E097（BearSSL custom-config-mk） | 自定义 mk/*.mk 配置体系 | 本稿无任何配置体系，纯直编 |

## 限制与注意事项

- conandata.yml 的 sha256 必须对官方归档实测（本案例
  `89c93f0de65d7329dd2917a31ecd1cc593f1f7f5096e472579af6b06b5740a47`）；
- W3 本地 CI 的 mirror fallback 会临时注入镜像 URL 并留 `conandata.yml.ghfast-bak` 残留，
  提交 PR 前必须恢复纯官方 URL 并清理残留（PF7 源 URL 门禁）；
- JC5 junk 检查按 `git ls-files`（index）而非工作树扫描：main 存量其他库的未登记隐藏文件
  （如 util-linux-login 的 `.ci-trigger`）会拦截 W3，需临时 index 隔离（`git rm --cached`）
  → 复验 → `git restore --staged --source=HEAD` 精确恢复，属基线噪声不走路径 B。

## 字段一致性 / 成对审计

- 本 .md 与同 stem `.kv` 的 id、title、error_signature、root_cause、rec_approach、
  knowledge_decision（new_draft / path B）字段一致；
- 位于当前库 worktree `knowledge/drafts/`，未写入正式 E###/索引/其他库目录；
- 最终原子性审计：见任务回报（草稿对 SHA-256 与白名单核对）。
