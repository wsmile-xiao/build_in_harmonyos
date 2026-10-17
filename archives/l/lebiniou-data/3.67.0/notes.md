# lebiniou-data 3.67.0 适配笔记

## 上游与产物

- 上游发行包 `lebiniou-data_3.67.0.orig.tar.gz`（Debian sid 源包，官方
  GitLab 仓库 gitlab.com/lebiniou/lebiniou-data 的再打包归档，与上游发行
  逐字节一致）：LEBINIOU（le biniou）音乐可视化程序的数据包，纯数据，
  无任何编译产物。sha256=4f081c22...a25f9f 实测（Debian .dsc 签名
  Checksums-Sha256 一致）。
- 内容（6 个安装目录，1727 个安装文件）：
  - `colormaps/` 1415 个 GIMP 调色板（`.gpl`，每文件恰 256 行 `R G B`
    三元组，无 GIMP Palette 魔数头）；
  - `images/biniou/` 图像主题：顶层 75 个（115 PNG + 8 JPEG 分布在顶层
    与主题目录）+ 4 个主题目录（covid-19 8 / oliv3 2 / opale95 20 /
    zebulon 18）；
  - `paths/` 8 个路径轨迹（首行 6 段逗号分隔浮点）；
  - `sequences/json/` 15 个序列定义 JSON；
  - `vue/` Web 前端资源：index.html + favicon.ico + css 9 / img 17（7
    GIF + 9 PNG + 1 SVG）/ js 18 / media 12 MP4 / sequences 105 JSON；
  - `test/` 上游 Debian autopkgtest 材料：lebiniou-test.sh.in 测试脚本 +
    lebiniou.json 配置 + 2.8MB FLAC 测试音频。
- 许可证：GPL-2.0-only（`COPYING`）。
- Debian 同源打包：`lebiniou-data` 为 `all` 架构纯数据包，安装到
  `/usr/share/lebiniou/` —— 本包布局沿用该惯例（`share/lebiniou/`）。

## OHOS 适配

纯数据包，无编译无链接（kicad-demos 范式）：

- `build()` 仅做防漂移清单校验：6 个目录逐目录计数（1416/128/9/17/169/4，
  含 Makefile.am）+ 7 个根标记文件在位；
- `package()` 将 6 个数据目录复制到 `share/lebiniou/`（排除上游不安装的
  `Makefile.am`；`bootstrap/` 不在上游 SUBDIRS，同样不安装），许可证另存
  `licenses/`；
- `package_id` 清空（数据包与 settings 无关）；
- `cpp_info.resdirs` 暴露资源目录，`runenv_info` 定义 `LEBINIOU_DATA_DIR`。

## 上游数据说明（实报）

- `.gpl` 文件不带 GIMP Palette 魔数头，直接以 `R G B` 行开始（每文件
  恰 256 行）—— 与 GIMP 标准导出格式不同，为 lebiniou 自有变体，探针
  按实际格式断言；
- `images/covid-19/covid-19.jpg` 与 `covid-19-confirmed.jpg` 扩展名为
  `.jpg` 但实为 PNG（`file` 实证：PNG image data 673×379 / 1000×563）。
  上游发行即如此，本包不修补（保持与官方发行逐字节一致），探针按实际
  格式断言并钉死误标文件恰为 2 个；
- 上游 tarball 顶层目录名为
  `lebiniou-data-version-3.67.0-<git-sha>`（GitLab 归档命名），conan
  `get(strip_root=True)` 处理；
- 上游 tarball 自带一份 `debian/` 目录（上游自己的打包材料），不参与
  安装也不参与防漂移计数。

## 测试口径

上游发行无构建期测试套件（R51 清点证据：无 tests/ 目录、无测试目标）。
`test/` 目录为 Debian autopkgtest 材料：`lebiniou-test.sh.in` 需 lebiniou
主程序 + ffmpeg + 联网执行（Debian dsc 声明 `Depends: ffmpeg, lebiniou
(>= 3.64.0)`、`Restrictions: needs-internet`），OHOS 环境不具备（lebiniou
主程序本身未适配），属环境限制，测试脚本与音频样本以数据原样随包分发。

适配后消费者探针（test_package/lebiniou_data_probe.cpp）逐文件断言：

1. 六大安装目录在位 + 安装树总文件数 1727 + 无 Makefile.am 残留；
2. 1415 个 `.gpl` 逐文件：恰 256 行、每行 RGB 三元组；
3. 115 PNG / 8 JPEG（images）+ 9 PNG / 7 GIF / 1 SVG（vue/img）魔数与
   `<svg>` 元素、4 个主题目录计数；
4. 8 个 `.path` 非空且首行 6 段逗号分隔浮点；
5. 15 + 105 个序列 JSON 均以 `{` 开头；
6. 12 个 MP4 的 `ftyp` box、index.html 的 lebiniou-vui 标题与 #app 挂载点；
7. FLAC 样本 `fLaC` 魔数与尺寸、lebiniou-test.sh.in shebang；
8. lebiniou.json 花括号平衡 + 顶层 5 键（screen/input/themes/engine/
   plugins）+ 320×180 + 109 个 plugins；
9. `licenses/COPYING` 为 GPL-2.0 文本；
10. 负向注入控制（坏 PNG 被魔数校验抓出并清理）。

## 本地预验（Windows MinGW，2026-09-25）

- 探针 g++ -std=c++11 -Wall -Wextra 编译零警告；
- 按 `package()` 布局搭 staging 目录实跑探针：**4608 项断言全过、0 失败**
  （与 test_package/MANIFEST.yml assertion_count 一致）；
- 预验还抓出上游勘误：`covid-19/*.jpg` 两个文件实为 PNG（见上节），探针
  已按实际格式断言。

## 真机验证（HarmonyOS PC 真机，2026-09-25）

- 通道：真机直驱（设备沙箱禁 ssh，fork 分支 HTTPS fetch +
  `git checkout FETCH_HEAD -- archives/l/lebiniou-data/`，共享克隆不切分支）；
  TMPDIR 三坑照旧规避（`mkdir -p ~/tmp && export TMPDIR=~/tmp`）。
- `python3 scripts/ohc-run.py conan-verify lebiniou-data 3.67.0`：
  8 道门禁 G0-G4 全部 PASS；L2/L4/L5 门禁标记 PASS、报告注明
  ⏭️ 跳过（纯数据包无 conan cache 产物）；终态 result.json 已上报，
  可标记 status: published。
- 消费者探针 conan create 内置执行：**4608 断言、0 失败、exit 0**
  （与本地 MinGW 预验一致），1727 安装文件、1415 .gpl 逐文件、
  全部图像魔数、负向注入控制全部真机复验通过。
- 真机首验抓出 1 个配方缺陷并已修复（commit 4b582d0da）：
  **conan copy() 的 excludes 按“相对 src 的完整路径”做 fnmatch 精确
  匹配**，`excludes=["Makefile.am"]` 只挡 src 顶层的同名文件，嵌套
  目录（4 个图像主题目录、sequences/json、vue 的 5 个子目录）里的
  Makefile.am 全部漏进安装树（首验 10 个漏装、探针 16 条失败：各
  目录计数 +1、1737≠1727）。修复：excludes 加 `"*/Makefile.am"`
  （fnmatch 的 `*` 可跨 `/`，覆盖任意嵌套深度），本地按 conan
  2.29.1 `_filter_files` 同款语义模拟复准 1727 后重推重验全绿。
