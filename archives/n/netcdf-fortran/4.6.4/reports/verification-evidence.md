# 验证证据摘要 — netcdf-fortran 4.6.4

**对象 SHA（采信轮验证对象）**：`e7ad90daddbf7fd25c0e5a86a8f97e4fd9d75be2`
**采信轮**：清缓存后的干净 `conan-verify`（`rc=0`，G0/G1/G2/G3 全 PASS）+ 独立重跑的 W3 本地 CI（`rc=0`，Pass rate 100%）
**CI**：PR #9556 构建 #44330 / #44354（`https://ohpcd.atomgit.com/ci?id=44354`）

## 〇、证据来源与指纹（先读这一节，再读下面的抄录）

仓库规则 R19「PR 中禁止的文件」禁止 `*.log` 入库，故本 PR **不携带任何 `.log`**；
本文以 Markdown **逐字节抄录**关键证据行，并给出原始日志的 sha256。
下表区分「本文抄录所依据的日志」与「本 PR 历史上曾携带的日志」——
两者是**同配方 rrev 的不同次运行**（每次干净轮都重建包目录，日志内的构建目录名与行号随之位移），
故指纹不同、行号也会整体位移：

| 日志 | 用途 | sha256 | 字节数 | 构建目录 | 该日志内出现的 rrev |
|---|---|---|---|---|---|
| `conan-create.log`（**第 5 轮＝采信轮运行**，任务私有副本，不在 PR 内） | **§一 抄录依据** | `0f5f8e0e77129434da469148141d43ec4ac1c285b5922219b6ef350e62e08590` | 77131 | `netcdabf80063a66df` | `ef1c1e0b3b925772aecac7ececd86f5d` |
| `w3-local-ci.log`（**第 5 轮 W3 独立重跑**，任务私有副本，不在 PR 内） | **§二 抄录依据** | `7f76595495eebb9dffa9e4747e090684ba49e65339a9c73f1d84f10b8ff269b1` | 79817 | `netcd521c91e37f67a` | `564ef86001b8cfc338fe3c403af72d25` |
| `reports/conan-create.log`（本 PR **曾**携带；已按 R19 于 `c54885d1` 删除） | 历史留档，供对照 | `72b7bc3e6116a2fd11320390a5fee92617f8ba21c7482a2e044c3eb37ffd7c9b` | 77029 | `netcd846cf25a560fd` | `ef1c1e0b3b925772aecac7ececd86f5d` |
| `reports/w3-local-ci.log`（本 PR **曾**携带；同提交删除） | 历史留档，供对照 | `ec2d2dfac0f1036a960c9b4aba4db0f0f9f26885ccc92a571557f782109d9e05` | 80109 | `netcd1b498c7bc9641` | `564ef86001b8cfc338fe3c403af72d25` |

> 注意两个 `.log` 记录的 **rrev 本身不同**：两者都是 `Exported:` 行上的 **recipe revision（rrev）**，不是 package revision（prev）；差异**已证实的成因是导出内容不同**（引用形式也不同，但其对 rrev 的单独贡献未做隔离实验，不列入成因），不是矛盾：
> `conan-verify` 路径用 `--user=ohpcd --channel=stable` 导出（`#ef1c1e0b…`），CI 脚本（W3）用裸 ref 并**在 export 之前先做镜像改写与 `file://` 预下载**（日志第 81-96 行：`Source URLs rewritten with mirror fallback` / `Pre-downloaded 2 files, conandata.yml updated to file:// URLs` / `exports: File 'conandata.yml' found`），导出的 `conandata.yml` 内容因此不同（`#564ef860…`）。
> 两条路径**解析出同一个 package id** `ab1dfb621746cd2521a4e722a26229dcdb548d66`，即二进制等价；且各自逐轮稳定（第 5 轮两份与 PR 曾携带的两份，同类 rrev 分别一致）。

**为什么采信轮证据对最终 SHA 仍有效**：`e7ad90daddbf7fd25c0e5a86a8f97e4fd9d75be2` 之后的提交只涉及
`reports/*.md`、`manifest.yaml` 的 `report:` 指针、`notes.md`，
以及**按 R19 删除两个 `.log`**；`archives/n/netcdf-fortran/4.6.4/{conanfile.py,conandata.yml,test_package/}`
逐字节未变：

```bash
git diff --stat e7ad90daddbf7fd25c0e5a86a8f97e4fd9d75be2..HEAD -- \
  archives/n/netcdf-fortran/4.6.4/conanfile.py \
  archives/n/netcdf-fortran/4.6.4/conandata.yml \
  archives/n/netcdf-fortran/4.6.4/test_package/          # 输出为空
```

两轮关键结论行一致（上游 `51/51`、消费者 `27/27` 与 `10/10`）。唯一差异是第 5 轮起新增的
C 侧断言行 `[ok] 实际加载来自被测包: …`——**PR 曾携带的那份 `conan-create.log` 里没有该行**
（该断言是第 5 轮随 `e7ad90dadd` 才加入的），这是本文 §一如实标注为「第 5 轮」的原因，
不是历史日志缺证据。

## 一、上游测试与消费者（依据：第 5 轮 `conan-create.log` 私有副本，`0f5f8e0e77129434…`）

| 证据 | 原始行（逐字节抄录） | 行号 |
|---|---|---|
| `Calling build()`（配方真实构建） | `netcdf-fortran/4.6.4@ohpcd/stable: Calling build()` | `:130` |
| 上游 CTest 汇总 | `100% tests passed, 0 tests failed out of 51` | `:926` |
| `Calling build()`（test_package） | `netcdf-fortran/4.6.4@ohpcd/stable (test package): Calling build()` | `:1051` |
| Fortran 消费者 | `RESULT: netcdf-fortran consumer checks 27/27 passed` | `:1128` |
| C 侧断言：加载路径来自被测包 | `[ok]   实际加载来自被测包: /storage/Users/currentUser/.conan2/p/b/netcdabf80063a66df/p/lib/libnetcdff.so.7` | `:1141` |
| C 侧契约汇总 | `RESULT: netcdf-fortran ABI contract checks 10/10 passed` | `:1142` |

计数口径：`ctest -N` 在配方实际配置（`ENABLE_TESTS=ON`、`BUILD_EXAMPLES=ON`）下注册
**51** 项 = `nf_test` 4 + `nf03_test` 2 + `nf_test4` 17 + `nf03_test4` 16 + `examples` 12；
`TOTAL 51 = PASS 51 + FAIL 0 + SKIP 0 + NOT_RUN 0`。
消费者合计 **37** = Fortran 2003 读写链路 27 + C 侧加载/ABI 契约 10。

## 二、W3 本地 CI（依据：第 5 轮独立重跑私有副本，`7f76595495eebb9d…`）

| 检查 | 原始行（逐字节抄录） | 行号 |
|---|---|---|
| G0 知识图谱完整性 | `G0_RESULT=pass` | `:8` |
| KC 知识检查 | `KC_RESULT=pass` | `:51` |
| JC 垃圾文件检查 | `JC_RESULT=pass` | `:78` |
| L0 质量门禁 | `L0_RESULT=pass: all checks passed` | `:1230` |
| L1 测试执行验证 | `L1_RESULT=pass: test_package executed` | `:1231` |
| L2 平台功能矩阵 | `L2_RESULT=pass: nf-config --version OK` | `:1232` |
| L4 静态安全 | `L4_RESULT=pass: no patches` | `:1233` |
| L5 产物基线 | `L5_RESULT=pass: bin/ has content` | `:1234` |
| W3 构建汇总 | `Pass rate: 100.0% (1/1)` | `:1242` |
| W3 退出码 | `w3_rc=0` | `:1245` |

## 三、复现命令

```bash
# ① 采信轮（先在精确 ref 上清缓存再验证；勿用「名前 5 字符」前缀 glob，会误删同前缀依赖）
conan remove "netcdf-fortran/*@*" -c
conan remove "netcdf-fortran/*" -c
python3 scripts/ohc-run.py conan-verify netcdf-fortran 4.6.4 --project-dir <repo>

# ② W3 本地 CI（与 CI worker 同源脚本）
CI_PACKAGES=archives/n/netcdf-fortran/4.6.4 CI_REPO_ROOT=<repo> \
  zsh ci/conan/build_and_test.sh archives/n/netcdf-fortran/4.6.4

# ③ 上游分母
cd <build>/build && ctest -N | tail -1        # Total Tests: 51
ctest --output-on-failure                    # 100% tests passed, 0 tests failed out of 51
```

## 四、G4/L2/L4/L5 的人工补测

`conan-verify-report.md` 里这四组打印 `✅ PASS` 但其下一行为 `⏭️ 跳过（无 cache 路径）`
（工具 G4 定位用带 `@user/channel` 的顶层键匹配不带该后缀的 `self.ref`，`KeyError` 被吞）。
按工作流第 7.2 节**以跳过为准**，判据与实测见同目录 `conan-verify-supplement.md`。
