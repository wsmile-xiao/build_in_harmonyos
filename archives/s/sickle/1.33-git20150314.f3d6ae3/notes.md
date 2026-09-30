# Sickle 1.33-git20150314.f3d6ae3 — OpenHarmony PC (aarch64)

## 源码与依赖
- 官方源码：`https://github.com/najoshi/sickle/archive/f3d6ae3.tar.gz`；本地下载 tarball SHA256 `43e4527cde77d03445335cf63fd62a761ee035f2a30cce061cd145b321fcf554`。
- 纯 C / 上游裸 Makefile（不是 autotools）；Conan `zlib/1.3.2.1` 通过 `conan download ... --only-recipe` 和 `conan install --build=never` 验证已发布及有 OHOS 二进制。
- 2026-09-29 x86_64 构建机，OHOS clang aarch64；从 `tools.build:compiler_executables` 获取交叉编译器，显式链接 Conan zlib 静态库和 `-static`，避免 qemu 下动态 loader 缺失。上游 Makefile 默认 `CC=gcc`/`LIBS=-lz`，通过 make 参数覆盖；没有补丁。
- `init-build` 误识别为 autotools，生成的 `AutotoolsToolchain` 骨架并不适合无 configure 的原生 Makefile；手写 application 配方并用 `cwd=self.source_folder` 执行 make。已有 `E999-draft-66AE`、`E392` 覆盖此错误模式，未重复造草稿。
- `conan-verify` 第一次 G1 报 `conanfile.py 缺少: export_sources() 方法` 和 `conanfile.py 缺少: 补丁应用调用`；按已存在 `E429-draft-E4BC` 补齐无补丁时仍必要的两个方法，再次验证通过。`engine` 初始返回 `E411`（libtool 对象污染），与本案无关，不照搬。

## 上游测试清点（R51）
- 源码 `test/` 目录 1 个，只有 `test.fastq`、`test.f.fastq`、`test.r.fastq` 三份测试数据；没有自动化测试源码、CTest/pytest 注册项目，`Makefile` 没有 `check` target，`make check` 返回 2（`No rule to make target 'check'`）。**上游注册自动用例 0，N/N′=0/0，无可计算通过率；不是 100%。**
- 单独用上游成对 FASTQ 数据运行 `qemu-aarch64 sickle pe -t sanger -q 20 -l 1 -f test/test.f.fastq -r test/test.r.fastq -o f.fastq -p r.fastq -s s.fastq`，退出码 0；输出 `FastQ paired records kept: 2500 (1250 pairs)`，`f.fastq`/`r.fastq` 各 5000 行，`s.fastq` 0 行。此项是人工功能演练，不冒充上游注册测试。

## 鸿蒙特有消费者用例（rule12：1）
- `test_package/conanfile.py` → Conan 消费 `sickle/1.33-git20150314.f3d6ae3` 包 → 生成两条 FASTQ 的 gzip 输入 → 用 **包内**静态 OHOS `sickle se` 在 qemu 运行（测试 zlib gzip 解压和质量过滤，真实输出保留 good 丢弃 drop）→ 把工具产出的 `trimmed.fastq` 生成为 `generated_fastq.h` → OHOS clang 交叉编译 `test_package/consumer.c` → qemu 运行消费者比对 FASTQ 实际字节。
- 本地执行：`python3 scripts/ohc-run.py conan-verify sickle 1.33-git20150314.f3d6ae3` 退出 0；`reports/conan-create.log` 中记录 `Total FastQ records: 2` / `FastQ records kept: 1` / `FastQ records discarded: 1` / `OHOS consumer: gzip FASTQ processed; 1 good read kept, 1 poor read removed`。消费者通过 1/1（100%），真实 qemu 实跑，不是仅检查文件存在或只编译不运行。
- 交付的包内 CLI 为**静态** aarch64 二进制；该本地 qemu 验证针对相同配方产物，并非将动态 OHOS 产物声称在 x86 上运行。

## 验证及限制
- `conan-verify` G1/G2/G3/G4/L2/L4/L5 报 PASS；G2 真正运行 `conan create` 与消费者；L2/L4/L5 因验证器未解析 cache 路径而分别标记跳过，不能算额外通过测试。
- `finish built` 的 W3 `setup.sh` 与 `build_and_test.sh` 成功（`reports/w3-local-ci.log`），工具生成 `.ci-result.json` 的 `exit_code=0`；`junk_check` incremental 扫描 12 文件通过。finish 总 rc=1 来自废弃的 packaging/ 非空预检及知识引用遗漏（已用 E1100 草稿引用修正）；G0 又将 Makefile 误认作 autotools configure，非阻断且不代表 Conan 编译失败。G0 错误模式已有 `E999-draft-66AE`。
- finish 的上游预下载机制曾暂时在 `conandata.yml` 插入 `gh-proxy.com` 代理 URL；已恢复官方 GitHub URL，镜像不入 PR；本地 `.build-cache` 临时下载文件不入仓。
- 没有上游自动化测试目标；保留原始上游测试文件不改。远端 CI 尚待 PR 创建后触发，不能计入本地通过率。
---

**编译结束**: 2026-09-29 12:23
**最终状态**: built
