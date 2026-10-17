- **三方库名称**：libgal（General Astrodynamics Library, GAL）
- **上游版本**：0.5.0（2009-01-09 发布）
- **上游仓库地址**：http://homepage.mac.com/pclwillmott/GAL/（已下线；存世权威源经 FreeBSD distfile 缓存托管，见补充说明 1）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新：2 条知识草稿，见下方「路径 B 知识贡献说明」）
- **使用知识库**：E007（patch-autotools-script，config.sub 三元组补丁）、E232（HMDFS exec 126，make install MKDIR_P 规避同款）、libncurses 6.6 先例（conan self.run 输出流绑定日志、/data 私有构建根）、aalib 1.4p5 先例（老 autotools 三元组补丁模式）；本 PR 新增 `knowledge/drafts/DRAFT-libgal-0.5.0-vsop87-j0-oob-ub-optimizer-exploited` 与 `knowledge/drafts/DRAFT-libgal-0.5.0-scanf-long-into-int-lp64-adjacent-zeroing`（路径 B 草稿）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 53974 | 来源：上游 automake `make check`（顶层 Makefile.am check_PROGRAMS，14 个测试程序，每子库一个；上游自带 gal_test_start/gal_test_stop 测试框架逐断言统计） |
| 集成测试 | 0 | 上游无独立集成测试 |
| 其他测试 | 0 | |
| **合计** | **53974** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 53974 | 不变 | 上游 14 个测试程序原样构建并运行（test/gal_tref 的 86/87 见补充说明 2） |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 9 | 新增 | test_package 消费者二进制（OHOS aarch64 真实编译/链接/执行）：gal_cal2jd 数值与状态码 5 条、gal_pdp 1 条、gal_tlechksum 2 条、TLE 长度校验 1 条 |
| **合计** | **53983** | **+9** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 本 PR 的 3 个补丁均不触碰上游任何 `*_test.c`/测试数据/断言：
> 1. `patches/0001-config.sub-ohos.patch`：仅改构建机 `config.sub`（2009 年版本不识别 aarch64/linux-ohos 三元组），使其接受显式传入的 `--build/--host=aarch64-linux-ohos`。
> 2. `patches/0002-vsop87-j0-ub.patch`：修复库源码 `gal_vsop87()` 速度项 j==0 时读 `t[-1]` 的越界 UB（clang -O3/aarch64 下被优化器利用导致全部 VSOP87 速度分量清零、上游 ephemerides 测试 549 项失败；-O0/-O2 不受影响）。修复为 `(j > 0 ? j*t[j-1]*cp : 0.0)`，j==0 的数学结果不变。
> 3. `patches/0003-tledec-scanf-long.patch`：修复库源码 `gal_tledec()` 用 `%5ld` 写 4 字节 `int satnum` 的 LP64 结构体破坏（8 字节存储清零相邻 classification/intldesg 成员）。修复为 `%5d`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游自带完整测试框架（14 个测试程序、53974 条断言）。另按鸿蒙特有测试新增了 test_package 消费者测试（见统计表「鸿蒙特有测试」行），不属于"补全上游缺失测试"。

## 验证结果

- 编译状态：通过（conan create 端到端：构建 → make check → 校验 → 安装 → 打包 → test_package 全绿）
- 上游测试用例通过率：53973/53974（99.998%；14 个测试程序中 13 个全过，gal_tref 86/87，唯一失败项说明见补充说明 2）
- 新增测试用例通过率：9/9（100%）

## 路径 B 知识贡献说明

本 PR 修复的两个上游缺陷均非平台怪癖，而是具有普适移植价值的真实缺陷，已沉淀为知识草稿（.kv + .md 各一份，待主编 promote 为正式 E 条目）：

1. **`knowledge/drafts/DRAFT-libgal-0.5.0-vsop87-j0-oob-ub-optimizer-exploited`**：幂级数求导循环 `j * t[j-1]` 在 j==0 时读 `t[-1]` 的越界 UB，clang -O3/aarch64 被优化器利用后 VSOP87 全部速度分量静默清零（-O0/-O2 碰巧正常）。给出与"平台 libm ULP 偏差"的判定三件套（优化级相关性、残差量级、最小守卫后全档一致），适用于一切幂级数/切比雪夫求值+求导一体循环的数值库。
2. **`knowledge/drafts/DRAFT-libgal-0.5.0-scanf-long-into-int-lp64-adjacent-zeroing`**：`sscanf("%5ld", &int 成员)` 在 LP64 上 8 字节存储清零结构体相邻成员（TLE classification/intldesg 恒空、其余字段全部正确）。给出"相邻成员清零 + 被解析字段正确 + 与优化级无关"的判定链，适用于所有 scanf 家族解析定长卡格式的 32 位时代 C 库。

## 补充说明

1. **源码来源（PF7/R39 语境）**：上游原站 homepage.mac.com/pclwillmott/GAL（MobileMe 时代域名）及 Savannah/xs4all 历史镜像均已失效，该软件存世的权威存档是 FreeBSD ports `astro/libgal` 的 distfile `libgal-0.5.0.tar.gz`（7914477 字节，FreeBSD distinfo sha256 `0e149ba25a9c7f4d3705c2d9c2e7821d0a751d70adc2effb248b27f62085ad31`，与本包 conandata/manifest 逐字节一致）。取源地址用 `https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/libgal-0.5.0.tar.gz`（USTC 的 FreeBSD ports distfiles 镜像，与官方 distcache 同源同文件）。
   **换源记录**：本 PR 首版使用 `distcache.freebsd.org`（FreeBSD 官方 distfile 缓存），远程 CI 连续 5 次构建（#51216/#51266/#51401/#51534/#51535）均以「源码下载超时 / Worker 网络受限」失败——该域在 CI Worker 网络不可达；改用 USTC 镜像后内容与校验和不变，且 `mirrors.ustc.edu.cn` 是本仓库既有 167 个包验证过的 CI 可达源主机（PF7 镜像黑名单仅针对 GitHub 类代理镜像）。
2. **gal_tref 86/87 已知偏差**：gal_c2tpv00a/gal_t2cpv00a 往返一致性断言容差 1e-12（被比较量 ≈4743，约 2 ULP 余量），OHOS aarch64 实测偏差 1.8e-12。该失败在 -O0/-O1/-O2/-O3、开/关 `-ffp-contract=off` 下完全一致，属平台 libm 浮点求值特性，非算法或优化缺陷。配方对 make-check 日志做 14 个程序逐项精确校验（通过/失败计数与 PASS/FAIL 标记全部钉死），任何其他偏差即构建失败。
3. **make check 退出码处理**：因上述已知项，`make check` 退出码为 2；配方捕获退出码并以上述逐项校验替代对退出码的信任，避免吞掉未来任何真实回归。
4. **make install 兼容**：configure 将 MKDIR_P 回退为 `install-sh -c -d`，而该脚本在本平台被内核拒绝 exec（E126，同 libgtop-tools E232 类）；安装时以 `MKDIR_P='mkdir -p'` 覆盖规避，文件安装走 `/bin/install`。
5. **交付形态**：仅静态库 `lib/libgal.a` + 全量公共头文件（`include/gal.h`、`gal_const.h`、各子库 `gal_*.h`）+ `share/doc/libgal/README`；运行时仅依赖 libc/libm，无 Conan 前置依赖。
