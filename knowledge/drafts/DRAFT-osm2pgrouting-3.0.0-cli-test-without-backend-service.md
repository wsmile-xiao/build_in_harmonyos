# DRAFT：产物要连后端服务、CI 又没有该服务（且上游零测试）时，`test_package` 怎么写才算端到端

> 状态：草稿（待知识库主编 promote）
> 来源：osm2pgrouting 3.0.0 适配，`archives/o/osm2pgrouting/3.0.0`
> 类别：conan / 测试 / CLI / 无服务端
> 配套草稿：`DRAFT-osm2pgrouting-3.0.0-bundled-find-modules-probe-build-host`、
> `DRAFT-osm2pgrouting-3.0.0-cmakelists-cxx-standard-shadows-toolchain-cache`、
> `DRAFT-osm2pgrouting-3.0.0-ohos-exec-eperm-126-unsigned-elf-not-noexec`
> （本条断言**跑得起来**的前提：产物必须先签名，否则 exec 退 126）

## 错误特征

不是一条编译/链接报错，而是"验证写不下去"时踩到的两类坑：

**(a) 偷懒写法 —— 产物是个空壳也照样绿**

```python
def test(self):
    self.run("ls .../bin/osm2pgrouting")      # 没有真跑二进制
```

CI 门禁 L0d 直接判失败：`def test` 里必须有一条真正的 `self.run(...)`。

**(b) 硬要拉服务端 —— 跨 worker 抖**

```
FATAL:  role "root" does not exist
connection ... refused              # 有的 worker 装了 pg、有的没有
```

`osm2pgrouting` 的全部价值是"把 `.osm` 导进带 PostGIS + pgRouting 的 PostgreSQL
并建拓扑表"。CI 没有这样的服务器，上游也**一条测试都没有**：

- 无 `tests/` 目录、无 `enable_testing()` / `add_test()`；
- 唯一的 `.github/workflows/ubuntu.yml` 需要先起一个真 PostgreSQL 服务。

于是"补全测试用例"的全部担子落在消费侧（`rule4` 的上游用例数 = 0）。

## 触发条件

- `package_type = "application"`，运行期需要服务/数据库/网络对端/专用硬件；
- CI 环境里没有该服务，且**不可能**为单个包把它拉起来；
- 上游测试数为 0，消费侧断言必须先证明"这不是个空壳"。

## 根因分析

关键在于注意到 **fail-fast 路径本身已经穿过整条运行时栈**：

```
argv → boost::program_options 解析 → 打印解析后的配置
     → pqxx::connection 构造 → libpq → TCP socket
```

把它指向 `127.0.0.1:1`（一个没人监听的端口），socket 之前每一层都被真实执行，
且**结果确定** —— 不需要任何服务端。此时 exit code 与 stdout 上的横幅，都是
"这个产物本身"的可观测行为。

反面选项各自的代价：

- 只查文件存在 / grep 二进制 → 空壳也过，L0d 还会额外判你失败；
- 在配方里起 PostgreSQL → 把可移植性配方变成基础设施配方，worker 之间抖动。

## 与相邻条目的关系

- **E325（Conan test_package 在 OHOS 上应先解析可用 shell 再跑脚本）**：本条同样
  必须用 `CONFIG_SHELL` / `/data/service/hnp/bin/bash`，不能用 `/system/bin/sh`。
- **E298（Conan test_package 的显式运行与环境）**：`test_type = "explicit"` +
  `env="conanrun"` 的用法来源。
- **E307（Conan test_package 缺少 CMake 时使用 profile 编译器直编）**：同属
  "test_package 不引入额外构建系统"的家族。
- **E281（无编译步骤的资源型包用 test_package 做消费者完整性验证）**：同属
  "上游没有测试时，消费侧断言就是全部证据"。

## 修复清单（照抄即可）

三组、22 条断言，全部在**无 PostgreSQL** 时成立：

**① 产物健康（1、17-22）**

- `bin/osm2pgrouting` 存在且可执行；
- `share/osm2pgrouting/` 下 4 个 `mapconfig*.xml` + `COPYING` 存在且非空；
- `mapconfig_for_cars.xml` 以 `<?xml` 开头。

**② 选项解析面（2-12）**

- `--version` / `-v` 均 exit 0，且输出版本串；
- `--help` exit 0，输出选项横幅，且提到 `--file`、`--dbname`；
- 无参数 exit 0（上游 `catch (required_option)` 后返回 0），输出含 `required`、
  并打印选项说明；
- 未知选项 exit 非 0，输出含 `unrecognised` / `unrecognized`。

**③ 连接路径（13-16）**

```bash
run -f /dev/null -d osm2pgrouting_ci_probe -h 127.0.0.1 -p 1
```

- 输出含 `COMMAND LINE CONFIGURATION`（解析后的配置横幅）；
- 输出含 `Filename = /dev/null` 且 `dbname = osm2pgrouting_ci_probe`
  —— **证明 argv 真的走到了配置对象**；
- 输出含连接尝试的那行提示；
- 进程 exit 1。

要点：

1. `/dev/null` 当输入文件、端口 1 当目标：两者在**任何 worker 上都以同样方式失败**，
   断言的是行为的公共前缀，而不是某个服务器的答案。
2. 脚本结尾 `echo "assertions: $checks, failures: $failures"`，失败时非 0 退出
   —— 给门禁一个可机读的汇总行。
3. **不要 `set -e`** 和计数辅助函数混用：第一条"预期失败"就会让脚本死掉。
   本项目用 `set -uo pipefail`，判定在计数器上。
4. OHOS 细节：驱动必须经 **bash** 跑，不能是 `/system/bin/sh`（mksh 跑 ELF 不可靠），
   通过 `CONFIG_SHELL` 或显式 `/data/service/hnp/bin/bash`；
   `LD_LIBRARY_PATH` **前插** `/system/lib64`（`libc++_shared.so` 在那），
   不要覆盖 VirtualRunEnv 提供的依赖目录。
5. 只断言真实二进制的 stdout 文本：**不 grep ELF、不 tr、不调依赖自带的工具**。
6. `MANIFEST.yml` 如实记 `upstream_tests: []`（附"上游确无测试"的证据）+
   `assertion_count: 22`。

## 反例（不要做）

| 反例 | 后果 |
|------|------|
| 用 `ls` / `grep .so` / `os.path.isfile()` 代替真跑二进制 | 空壳产物照样全绿；L0d 判失败要求返工；即便合入也不提供任何回归保护 |
| 配方里 `pg_ctl` / `initdb` / `docker run` 拉起后端 | 可移植性配方变成基础设施配方，需要特权与容器运行时，CI 时绿时红 |
| `set -e` 与计数辅助函数混用 | 第一条"预期失败"就让脚本终止，后续断言从未执行却被当成通过 |
| 写死 `exit 0` | 汇总行的 `failures` 失去意义，门禁读到假绿 |
| 只跑一次就宣称 22/22 而不做破坏性自检 | 无法证明断言真的绑在产物上（移走 `bin/` 后，staging 的 `cp` 应失败、打印 `FAIL: cannot stage …` 并以非 0 退出） |
| 在 OHOS 上直接 exec 包内的 `bin/osm2pgrouting` | 未签名 ELF 被内核以 EPERM 拒绝 → 退 126、`Operation not permitted`，依赖二进制输出的断言成片失败（见 `DRAFT-osm2pgrouting-3.0.0-ohos-exec-eperm-126-unsigned-elf-not-noexec`） |
