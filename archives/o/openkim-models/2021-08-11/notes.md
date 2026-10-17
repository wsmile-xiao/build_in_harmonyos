# openkim-models 2021-08-11 适配笔记

## 上游与产物

- 上游：OpenKIM 项目的势模型集合（openkim.org），发行版本 2021-08-11。
  官方发行归档在 s3.openkim.org（txz）；Debian/Ubuntu 官方再打包归档
  `openkim-models_2021.08.11.orig.tar.xz`（无 +dfsg 后缀，内容未剔除），
  sha256 6104f6ea... 与 Launchpad .dsc PGP 记录核对一致。s3 官方
  txz（46.7MB，sha256 f42d2419...）已全量下载并与 Debian orig 逐文件
  diff 零差异（2026-09-26 实证，内容同源）。Homebrew/Guix 均以 s3
  官方 txz 为源。
- 内容：**纯数据包**——34 个模型驱动源码目录（model-drivers/，C++ 驱动，
  上游由 kim-api 的 collections-management 编译为插件）、445 个
  portable-model 参数集（portable-models/）、96 个 simulator-model
  定义（simulator-models/），共 4228 文件；根目录 CMakeLists.txt（集合
  级构建入口，需 kim-api）+ LICENSE（CDDL-1.0）。
- Debian 发行布局：`/usr/share/openkim-models/{model-drivers,
  portable-models,simulator-models}`（1:2021.08.11-4，all 架构无编译）。

## 上游测试口径（R51 三步法）

- **清点**：发行归档全树无任何测试文件（无 test/ 目录、无 *.t 等，
  逐目录 find 实测 0 个）。OpenKIM 的模型条目验证由 KIM-API 的
  kim-api-collections-management 在**编译模型驱动**时执行（驱动编译
  链接 kim-api 头/库后运行参数自检）——kim-api 本身尚未适配 OHOS
  （制品仓 archives/k/ 无 kim-api），属环境限制。
- **等价覆盖**：以内容级消费者探针代替——对 575 个条目目录逐目录断言
  KIM 元数据不变量（kimspec.edn 存在+非空+extended-id 与目录名一致、
  CMakeLists.txt 存在），全局计数防漂移（4228 文件/575 kimspec/575
  条目 CMakeLists/606 条目 LICENSE），CDDL 许可证文本与代表条目内容
  抽查，附负向注入控制（缺失/空 kimspec 必须被拒）。共 1751 断言。
- **实跑**：Windows 本地 MinGW 预验 + HarmonyOS PC 真机 conan create
  消费者测试（见"真机验证记录"）。

## OHOS 适配

- **纯数据包，零补丁**。配方（lebiniou-data/kicad-demos 同款范式）：
  build() 仅防漂移清单校验（3 目录逐目录计数 415/3108/703 + 根标记
  2 文件），package() 原样复制三个集合目录与根 CMakeLists.txt、LICENSE
  到 `share/openkim-models/`（集合树完整；LICENSE 同时存 licenses/，
  conan 惯例），package_id 清空。无编译、无链接、无软链（R5 实测
  0 软链）。
- **运行时入口**：runenv 定义 `KIM_MODELS_DIR` 指向
  `share/openkim-models/`（KIM-API 惯例）；cpp_info.resdirs 同步声明。
  消费者（未来的 kim-api 适配或参数消费方）直接读集合树。
- **模型驱动编译不在本包范围**：驱动编译需要 kim-api（头+库+工具链
  约定），kim-api 未适配 OHOS；本包把驱动**源码树**原样随包分发，
  待 kim-api 适配后消费者可按 kim-api-collections-management 流程
  编译（这正是 Debian 二进制包的构建方式）。
- **源选择**：Ubuntu 池镜像（USTC/阿里云双 URL）优先——CI worker 对
  Ubuntu 池可达性已由 kicad-library #60400、lebiniou-data 实证；s3
  官方 txz 的 CI 可达性未实测，但内容同源已本地实证（s3 txz 全量
  下载 sha256 f42d2419...，与 Debian orig 逐文件 diff 零差异，
  2026-09-26）。选 Ubuntu 池 = 内容与官方发行完全一致 + 可达性有据。

## 真机验证记录（2026-09-26 19:04，全绿）

- 设备：HarmonyOS PC（aarch64，192.168.43.14），Conan 2.29.1，
  profile ohos-aarch64（设备侧 ~/.conan2/profiles/）。
- 执行：conan-verify 八门禁 **Verdict PASS**（G0 构建系统 unknown
  跳过预查询 / G1 配方完整性 8 项全过 / G2 conan create 成功 /
  G3 无 bin/lib 无同名库冲突 / G4 产物完整性 PASS——包 ID 为空系
  package_id 清空所致 / L2/L4/L5 无 cache 路径跳过）；G2 内消费者
  探针真机实跑 **G1-G8 全 [OK]、all assertions passed (1751)**，
  G8 两条 [FAIL] 为预期负向控制。result.json 已上报（draft:false）。
- 真机首验抓出两坑已修（commit 0404b0679）：①OHOS clang 下
  `::rmdir` 无全局声明（MinGW 靠传递包含侥幸编译过）→ 探针显式
  `#include <unistd.h>`；②package() 把 LICENSE 只放 licenses/ 漏了
  集合根（探针 G1 "collection root LICENSE present" 挂）→ 集合树根
  一并复制（Debian 布局原样分发）。
- 源归档直连 Ubuntu 池镜像（USTC 首选）下载成功，无需换源。

## 参考

- 上游项目: https://openkim.org / https://github.com/openkim/openkim-models
- 官方发行归档: https://s3.openkim.org/archives/collection/openkim-models-2021-08-11.txz
- Debian 源码包: https://packages.debian.org/source/sid/openkim-models
