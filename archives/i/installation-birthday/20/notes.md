# installation-birthday 20 适配笔记

## 上游与来源

- installation-birthday：Chris Lamb（lamby@debian.org）维护的
  Debian native 源包——"Receive congratulations on system installation
  anniversaries"，单文件 Python 3 CLI：探测系统安装时间（ext 文件系统
  创建时间 via tune2fs，或 /var/log/installer、/etc/hostname 等候选
  文件 mtime，取最旧者），周年当天打印 ASCII 生日蛋糕。Debian 侧经
  cron.daily 集成实现"自动向本地系统管理员发送消息"。
- 上游仓库：https://salsa.debian.org/lamby/installation-birthday
  （tag 20 = master HEAD dc916f94，GPL-3+，Copyright © 2017-2020
  Chris Lamb）。v20 由 Debian sid 发行（2024-12-31，changelog：
  "Add /etc/hostname to the list of candidate filename timestamps"）。
- 版本 20 与任务卡一致。官方 main 无此包（R37 无递增需求）。
- 钉死源：Debian 官方 pool 源包 tarball（native 包，无 orig 区分），
  sha256 `e1ed3ef6…a5621` 与 .dsc 的 Checksums-Sha256 字段一致
  （本地下载实测核对）；备源 = 清华 TUNA Debian 镜像同文件。
  salsa gitlab 的 /-/archive/ gzip 流每次请求字节可能不同，不作
  钉死源。

## 许可证

- **GPL-3+**（脚本头部 GPL-3-or-later 声明 + tarball 内 COPYING
  674 行 GPL-3 全文；debian/copyright 同）。COPYING 随包进入
  share/doc/installation-birthday/。

## OHOS 适配

纯脚本包，无编译无链接（kicad-demos/inform6-library/ldraw-parts/
fabric-completion 范式）：

- `build()` 防漂移：2 载荷文件在位 + 全树总数 == 17（含 debian/
  打包目录 9 文件、setup.py/pyproject.toml/.travis.yml）；
- `package()` 显式逐文件复制：
  - `installation-birthday` → `bin/`（chmod 755；脚本名为上游原名，
    Debian 亦安装为 /usr/bin/installation-birthday）；
  - `COPYING` → `share/doc/installation-birthday/`；
  - debian/ 目录（cron.daily、help2man manpage 规则、autopkgtest）
    属 Debian 发行集成，不进入 conan 包；
- `package_id` 清空；`cpp_info.bindirs` = bin、`resdirs` = doc 目录；
- 无 runenv（CLI 工具，仅命令行参数接口）。
- 消费者运行前提：python3 ≥ 3.11（`datetime.UTC`）+ python3-distro
  （可选：仅蛋糕模板取发行版名）；e2fsprogs/tune2fs 缺失时脚本自动
  降级到候选文件 mtime 路径（OSError/CalledProcessError 兜底）。

## 测试口径

上游测试 = 2 个 Debian autopkgtest smoke 用例（debian/tests/
0001-smoketest: `installation-birthday --verbosity=2`；-force 变体），
仅在 Debian CI 运行，不随 tarball 进入发行。适配后两层探针：

1. C++ 消费者探针（`test_package/installation_birthday_probe.cpp`）
   5 组静态断言：包内清单（2 文件精确，排除 conan 簿记）/ 脚本内容
   锚点 14 项（shebang、GPL-3 头、2017-2020 Lamb 版权行 UTF-8 字节、
   DESCRIPTION、蛋糕模板、--verbosity/--puppet/--force、候选时间戳
   列表含 v20 新增 /etc/hostname、datetime.UTC、主入口守卫）/ COPYING
   锚点 3 项 / 静态完整性（226+674 行精确、无 CR、末行锚点）/ 负向
   注入（截断、CR 污染副本检出并清理）；
2. Python 行为探针（`test_package/test_behavior.py`，纯标准库）
   6 项：py_compile 语法完整性 / --help 退出码 0 / --verbosity 5
   退出码 2（argparse invalid choice）/ --force --puppet 全跑
   rc∈{0,1}（rc==0 → 输出恰一行 installation_date=YYYY-MM-DD；
   rc==1 → stdout 空，即真机无任何候选时间戳文件时上游语义）/
   --verbosity=2 复刻上游 smoke 语义 / 截断副本检出。
   本机无 python3-distro 时自动注入桩模块（仅影响子进程 import）。

## 真机验证（HarmonyOS PC 真机，2026-09-26）

### 首验 G2 FAIL：漂移守卫误报 conan 注入环境文件（已修复）

- `conan-verify installation-birthday 20`：G0/G1 PASS，G2 FAIL——
  `ERROR: Invalid configuration: installation-birthday 20 total file
  count 23 != 17`。
- 真机 ls 实证：conan 2 在 build() 前向 **source folder** 注入 6 个
  聚合环境文件（conanbuild.sh、conanrun.sh、conanbuildenv-*.sh、
  conanrunenv-*.sh、deactivate_conanbuild.sh、deactivate_conanrun.sh），
  17 + 6 = 23 触发守卫。
- 修复：漂移守卫排除 `.sh` + conaninfo.txt/conanmanifest.txt
  （fabric-completion 先例同款口径）；教训同 fabric：**G2 FAIL 先看
  conan-create.log 首行真实 ERROR，再采信知识图谱建议**（本次图谱
  命中 E540 runner-path-prepend 亦为误报——纯脚本包不碰 CC/CXX）。

### 验证结论（重验，2026-09-26 实录）

- `conan-verify installation-birthday 20` **八道门禁 G0-G4/L2/L4/L5
  全绿，Verdict: PASS，判定「可标记 status: published」**
  （reports/conan-verify-report.md，45 行）。
- G2 conan create 双探针全过：`installation_birthday_probe: all
  assertions passed`（5 组 32 静态断言）+ `test_behavior: all checks
  passed`（6 项行为断言）（reports/conan-create.log，185 行）。
- 真机环境实录：python3 3.12.9 自带 distro 模块（行为探针走真实
  import 路径，无需桩）；无 tune2fs、无 /etc/hostname、无
  /etc/machine-id 等候选时间戳文件 → `--force --puppet` 全跑走
  rc=1 分支且 stdout 为空（上游"无法确定安装日期→静默退出 1"
  语义，与探针断言口径吻合）。
- G3 无系统同名库冲突；G4 空包 ID 为纯数据包预期现象（package_id
  清空，与 ldraw-parts/fabric-completion 同口径）；L2/L4/L5 无
  cache 路径跳过。
- ohc-run 自动 ghfast 注入未触发（本包为 deb.debian.org/TUNA 源，
  非 github），Debian 官方池下载正常。

## 参考

- 上游仓库: https://salsa.debian.org/lamby/installation-birthday
- Debian 包页: https://packages.debian.org/sid/installation-birthday
- 项目主页: https://chris-lamb.co.uk/projects/installation-birthday
