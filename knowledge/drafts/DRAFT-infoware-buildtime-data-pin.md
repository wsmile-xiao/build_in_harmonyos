# ═══ Draft knowledge entry — 上游构建期 git clone 数据文件：conandata 第二源钉定官方快照 ═══
# Timestamp: 2026-09-06
# Software: infoware 0.6.0（模式适用于任何 configure/build 期拉取数据文件的上游）
# Gate: PR #8568（任务 #5452）；CI build #40884（同类 github 构建期下载失败实证）
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-infoware-buildtime-data-pin
severity: 2
category: cmake|network|build-time-data|conandata|reproducibility
trigger_tool: cmake / git / conan
phase: configuration
approach: 找上游自带的显式路径覆盖变量（infoware 为 INFOWARE_PCI_IDS_PATH）；
  conandata.yml sources 追加第二源=官方数据仓库钉定 commit 的原始文件+实测 sha256；
  source() 第二文件用 conan.tools.files.download()（get() 对未知扩展名默认 ZIP
  解码器会报 BadZipFile）；generate() 用 toolchain.cache_variables 注入路径；
  钉 commit 而非 master 保证 sha256 可复现

keywords: pci.ids, pci_generator, git clone, INFOWARE_PCI_IDS_PATH, conandata
  second source, download, BadZipFile, 钉定, 数据快照, 构建期网络

error_signature: Couldn't find a usable git executable|The pci\.ids file.*is required
  for building|fatal: could not read Username|Error cloning.*during configure
match_keywords: pci.ids, git clone, configure time, INFOWARE_PCI_IDS_PATH, 钉定

root_cause: infoware 的 CMakeLists 在 configure 阶段无条件要求 pci.ids（生成
  pci_data.hpp），默认 git clone github pciutils/pciids。积分赛 CI worker 沙箱
  通常缺 git/网络（实证：同晚 cbmconvert 构建 #40884 在 worker 上 github 下载
  SSL/连接失败，预下载 curl 也缺失）；且 unpinned master 无法写稳定 sha256。
  独立坑：Conan 2 files.get() 对未知扩展名一律解压并默认 ZIP 解码器，
  get(pci.ids) 直接 BadZipFile。
affected_scope: 任何在 configure/build 期拉取数据文件或子仓库的上游（FetchContent、
  git clone 数据库、字体/unicode/规则表）在 OHOS CI 沙箱的适配

rec_priority: 1
rec_impl: conandata-second-source-download
verification: 干净 CONAN_HOME 无 git 环境 conan create 全绿；设备 ctest 4/4；
  CI build #40887 通过

similar_to: E150（manual-download：子仓库/目录缺失的手工搬运）、E425（依赖拆分 scope）
forbidden: 钉 master（sha256 漂移不可复现）；把数据文件提交进配方目录（体积/JC/
  许可三重问题）；用个人镜像 URL（PF7 拦截）
