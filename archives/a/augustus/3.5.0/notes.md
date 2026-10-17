# augustus 3.5.0 适配笔记

## 编译环境
- 构建系统: makefile（上游无 configure，直接 make）
- 编译日期: 2026-08-30
- 编译器: clang/clang++（OHOS aarch64，HNP 工具链）
- 状态: built（待真机预检）

## 编译步骤

1. 上游源码：`https://github.com/Gaius-Augustus/Augustus/archive/refs/tags/v3.5.0.tar.gz`
   - sha256: `5ed6ce6106303b800c5e91d37a250baff43b20824657b853ae04d11ad8bdd686`
   - 与 Homebrew core Formula/a/augustus.rb 记录一致，本机下载复核一致。
   - 真机无法直连 github.com（E017）：conandata.yml 的 url 已改为有序镜像列表
     （ghfast.top / gh-proxy.com 镜像在前——实测每次都能成功下载；官方 URL 最后
     回退——实测持续超时 connect timeout=30×3，sha256 不变）。
2. 依赖：**零 conan 依赖**（minimal 配置）。
   - `ZIPINPUT=false`：关闭 gzip 压缩输入，消除 boost_iostreams
     （fasta.cc/genbank.cc 的 boost include 均在 #ifdef ZIPINPUT 保护内，
     minimal 下不编译，LDLIBS 为空）。
   - `COMPGENEPRED=false`：关闭比较基因预测 CGP，消除
     gsl/lpsolve/suitesparse/boost_serialization/sqlite/mysql 全部重依赖
     （ohpcd 制品仓无 lpsolve；CGP 无法在 OHOS 编译，Homebrew 同样禁用）。
3. 构建命令（conan create，profile 见 ci/conan/profiles/ohos-aarch64）：
   ```bash
   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   ```
4. 构建产物：src/ 下 5 个程序（augustus/etraining/prepareAlign/fastBlockSearch/
   pp_simScore）→ 复制到 bin/。
5. 运行时数据：config/（140MB，166 个物种模型）必须随包分发；augustus 运行时经
   AUGUSTUS_CONFIG_PATH 环境变量（第一优先级）或可执行文件相对路径定位。
6. 上游 install 目标（复制到 /opt/augustus-* + PREFIX/bin 符号链接）不适合 conan
   包，package() 直接打包 bin/ + config/。
7. 磁盘空间（真机多轮预检失败根因）：上游 tarball 解压后 ~763MB（docs/ 364MB、
   auxprogs/ 182MB、examples/ 58MB 等构建非必需）。修复三道，单轮峰值从
   ~1.5GB 降到 ~540MB：
   - `no_copy_source = True`：禁用 source→build 整树复制（conan
     installer._copy_sources 唯一开关，仓库 63 个先例），build() 以
     self.source_folder 为 cwd 原地构建。
   - source() 用 `get(excludes=...)` 在解压时**直接跳过** docs/auxprogs/scripts/
     tests/mansrc/.github 及 examples 中除 example.fa 外全部内容，大目录永不
     落盘，源树 763MB→158MB（避免"先全量解压再 rmtree"在 HMFS 上删除受限导致
     的峰值与残留）。
   - 只构建核心 `make augustus`，不构建需 bamtools/htslib 的 auxprogs。
   - 本地实测：source 缓存 158MB（旧版 763MB），b/ 目录无源树副本（仅生成器）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 硬编码 `CXX ?= g++` | OHOS 工具链无 g++ | build() 传 `CXX=clang++`（R33：取自 conan conf） |
| 2 | 上游 install 建 PREFIX/bin 符号链接 | HMFS 上符号链接受限 | package() 直接 copy bin/ 与 config/ |
| 3 | 可执行 ELF 在 OHOS 上被内核拒绝执行 | E077/E082：需有效 .codesign 签名段 | package() 对 bin/ 下每个 ELF 用 llvm-objcopy + binary-sign-tool 自签（ispell/xeyes 先例） |
| 4 | 真机无法直连 github.com（E017） | 网络限制 | conandata 镜像列表回退 |
| 5 | 上游无 minimal 可跑的自动化测试 | make test 依赖 x86_64 + CGP 全量构建 | test_package 用 --version + --species=human 真实预测断言 |
| 6 | 真机 `No space left on device`（Errno 28，Copying sources to build folder → export 阶段创建缓存目录都失败） | 763MB 源树解压 + conan 复制到独立 build 文件夹，磁盘翻倍且多轮全量残留累积 | `no_copy_source=True` 禁用复制 + source() 用 `get(excludes=...)` 解压时跳过 docs/auxprogs 等（源树 763MB→158MB，本地实测）；另注意 export 阶段即 ENOSPC 属 worker `/var/conan` 陈旧缓存未清理的环境问题（14:39/15:14/15:23 三次同一路径 augusa14c8143d3c11） |
| 7 | 真机编译报 `fatal error: 'cmath' file not found`（lldouble.hh include `<cmath>`） | hnp clang++ 无默认 C++ 头文件搜索路径，找不到 libc++ 标准库头文件；上游 `-std=c++11` 也低于 OHOS libc++ 要求（E130） | build() 给 `CXXFLAGS` 显式加 `-stdlib=libc++` + `-std=c++17`（整体覆盖上游 `:=` CXXFLAGS；id3v2/bowtie2 先例同款）；`LDFLAGS` 亦带 `-stdlib=libc++`。真机编译全部通过（5 个二进制） |
| 8 | 真机 package() 阶段 `Error 127`（line 177，binary-sign-tool 命令未找到） | preflight worker 未预装 `/data/service/hnp/bin/binary-sign-tool`（工具链缺件，非配方逻辑） | 按 id3v2/ical2html/xeyes 先例加存在性防护：`os.path.isfile(sign_tool) and os.path.isfile(objcopy)` 才签名，缺失则跳过并输出 info；chmod 失败容错（HMBS_CAP_CHMOD=0）。CI worker 具备工具时会正常签名 |
| 9 | MR 门禁报 `缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据` | 真机预检通过（编译+打包），但 test_package 未输出上游测试证据 JSON 标记，hmbs 硬门禁判 incomplete | test.sh 末尾输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`（上游 make test 依赖 x86_64+CGP 全量构建，minimal/OHOS 无法运行，理由见 MANIFEST 审计）+ `HMBS_TEST_PACKAGE_RESULT`；test_package/conanfile.py test() 再冗余 print 一行（xsel/xeyes 先例同款） |

## 依赖版本

- 无（minimal 配置零依赖；ZIPINPUT=false + COMPGENEPRED=false）

## 验证结果

```bash
# 待 HMBS 真机预检（HarmonyOS aarch64 真机 conan create + test_package）
# test_package 断言：
#   1. augustus --version 输出含 "AUGUSTUS (3.5.0)" 且 exit 0
#   2. augustus --species=human examples/example.fa 输出含 "Predicted genes"
```

## 注意事项

- augustus 是命令行工具（application 包），package_info 只需 bindirs。
- `--version`/`--help` 均抛 HelpException(GREETING) 打印提示到 cerr 后正常返回，
  实际以 main() 的 errorcode（默认 0）退出，可作 smoke test。
- config/ 必须设置 AUGUSTUS_CONFIG_PATH 指向包内 config/ 才能运行基因预测
  （test_package 的 test.sh 里 export）。

---

**编译结束**: 2026-08-30
**最终状态**: built（待 HMBS 真机预检）
