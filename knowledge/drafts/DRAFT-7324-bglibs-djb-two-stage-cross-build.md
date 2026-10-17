# E-DRAFT: djb/spac 系包的交叉编译两阶段模式（native bootstrap 生成器）

- **触发实例**：bglibs 2.04 适配（任务 7324，分支 feat/bglibs-2.04；GLM-15 探索 + GLM-23 收口）
- **错误签名**：`cannot execute binary file: exec format error`（交叉机上运行
  目标架构生成器）/ 构建产物架构为宿主机（conf-* 泄漏宿主 cc）
- **类别**：cross-compile-two-stage
- **严重度**：2（交叉环境确定性失败，模式化修复）

## 症状

djb/spac 风格包（bglibs 等）在 OHOS 交叉编译时：

```text
Makefile 规则：crc/*_table.c: crc-gentab      ← 构建期要"运行"生成器
交叉编译后执行 crc-gentab → exec format error（aarch64 ELF 无法在 x86 worker 运行）
或：conf-cc 保留宿主 cc → 生成物架构错误（更危险：静默错架构）
```

## 根因

1. spac/djb 树把编译器路径"烤"进生成的包装脚本（conf-cc/conf-ld →
   compile/ltcompile/load/makeshlib 第一行），构建期与目标期共用同一 conf；
2. Makefile 把"构建期生成器"当作普通目标构建并**就地执行**；
3. choose(1) 运行型探测在交叉下退化（不能执行目标码探测平台特性）。

## 修复模式：两阶段构建

- **阶段 1（native bootstrap）**：按标准名探测构建机编译器
  （`for c in gcc clang cc; do ...`，R33——绝不裸用 env CC），只构建生成器
  目标并执行，产出 CRC 查表等生成源（bglibs：6 张表）；
- **阶段 2（target）**：覆写 conf-cc/conf-ld 第一行为 Conan profile 的目标
  编译器（`-W -Wall -Wshadow` + 按构建类型的优化级），`make sysdeps.h
  libraries` 全量目标构建；生成器前置条件已满足不再触发；
- **choose 探测**：依赖 choose 契约（两分支都必须可编译），运行期由
  sysdeps.h 选择，交叉下天然安全；
- **libtool**：spac 的 ltcompile/makeshlib 依赖 libtool →
  `tool_requires("libtool/2.5.4")`（CI 无系统 libtool，cliquer 先例）；
- **暂存**：所有 staging 路径指向 build_folder 私有目录（R49/E524，
  禁 /usr/local）。

已验证：bglibs 2.04 于 OHOS aarch64 真机 conan create 干净构建通过
（conan-verify G0-G4/L2/L4/L5 全绿），上游 selftests 118 例全量运行
117 通过 + 1 项 SELinux 网络策略环境失败（逐项申报），消费者测试 19 断言通过。

## 禁忌

- 禁止在构建机上运行目标架构生成器（exec format error 的直接来源）；
- 禁止 conf-* 烤入 /usr/local 或宿主编译器路径（R49/E524、PF6）；
- 禁止手工改写生成表顶替生成器（与上游漂移）；
- 禁止 --build=missing 掩盖失败。

## 适用范围与查重

- **适用**：全部 djb/spac 包（bglibs、cvm=平台任务 6951、ucspi-*、djbdns 系）
  及一切"Makefile 构建期运行生成器"的包（gperf/bison 同构场景）；
- **查重**：knowledge/graph/index.tsv 无 spac/djb 两阶段构建条目；
  draft-review 相似度复核通过（复核记录见 PR）；
- **关联**：cvm 0.97（硬依赖 bglibs）适配时可直接复用本模式。
