# libcrc 2.0 适配笔记

## 编译环境
- 构建系统: 纯 GNU Makefile（上游刻意无 autoconf/automake，仅手工维护的 Makefile）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS aarch64 工具链）
- 状态: built

## 编译步骤
1. `init-build libcrc 2.0 --url=https://github.com/lammertb/libcrc/archive/refs/tags/v2.0.tar.gz`
   - 官方 tag v2.0（commit 32aacc5），tarball SHA-256 `ad0f56ee6fb3393d546e22bea19c6f81ec7601f85514d7fa8a59fa6efb6fec20`
   - 仓库主页 URL 不是 tarball，init-build 首次会报"下载内容是 HTML"，必须用 `/archive/refs/tags/v2.0.tar.gz` 形态
2. `lang-preflight`：detected=c，与 task=cpp 属兼容族，通过
3. `make CC=clang LINK=clang all` → lib/libcrc.a（8 个 .c 目标文件）+ testall + tstcrc（示例 CLI）
   - 上游 Makefile 硬编码 `CC=cc`/`LINK=cc`，本机无 `cc`（仅 clang），需覆盖 CC/LINK 变量
4. 上游测试：`./testall` → 0 错误，`**** All tests succeeded`
   - test_crc：4 向量 × 10 算法 = 40 项断言；test_checksum_NMEA：146 向量
   - OHOS ELF 需 `.codesign` 签名段才能执行（未签名报 Operation not permitted / exit 126）；
     按 E077 四步：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod a+x`
5. `conan-init` 生成配方 → 手工改写 conanfile.py（autotools 模板不适用，见问题 #2）
6. `conan-verify`：G1/G2/G3/G4 全 PASS（conan create 干净构建 + test_package 消费者 11 项断言全过）
7. `finish ... built`：W3 本地 CI 通过（L0/L1/L4/L5 全 pass，.ci-result.json exit_code=0），submit 就绪

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 URL 传仓库主页，init-build 报"下载内容是 HTML" | 需要 tarball 直链 | 改用 `https://github.com/lammertb/libcrc/archive/refs/tags/v2.0.tar.gz` |
| 2 | conan-init 按 autotools 模板生成配方，`autotools.configure()` 会失败 | 库是纯 Makefile，无 configure 脚本 | 重写 conanfile.py：source() 下载 + build() 直接 `make CC=clang LINK=clang all` + package() 拷 lib/libcrc.a 与 include/checksum.h |
| 3 | `conan create` 报 "Package type is 'library', but no 'shared' option declared" | Conan 2 的 library 包类型必须声明标准 shared 选项 | 补 `options={"shared":[True,False]}; default_options={"shared":False}`（E283 已覆盖） |
| 4 | test_package CMake 报 "Library 'crc' not found in package" | package() 里 `copy(self, pattern, dst=os.path.join(package_folder,"lib"))`：conan copy() 会把 pattern 的相对子路径拼到 dst 后，实际生成 `package/lib/lib/libcrc.a` 嵌套 | dst 直接用 package_folder 本身（E362/DRAFT-picojson 同族：copy dst 语义） |
| 5 | testall/tstcrc 执行报 Operation not permitted | OHOS ELF 必须有 .codesign 签名段 | E077 四步签名后正常运行 |
| 6 | 本机无 `cc`，make 链接失败 | 上游 Makefile 硬编码 CC=cc/LINK=cc | `make CC=clang LINK=clang all`（E095 相关：硬编码编译器名） |
| 7 | /tmp 写入失败（curl 错误 23） | 设备 /tmp 受限 | 下载到 `~/tmp`（TMPDIR 已指向 /storage/Users/currentUser/tmp） |
| 8 | test_package NMEA 断言初写 `*76` 失败 | checksum_NMEA 返回不含 `*` 前缀的两位校验串 | 对照上游 testnmea.c 向量修正为 `"76"` |

## 源码修改

无（零源码修改适配：纯 ANSI C 静态库，无平台相关代码，E077 签名为执行期处理不入库）。

## 依赖版本

- 无外部依赖（纯 C 标准库）
- 工具链: clang 15.0.4 (OHOS aarch64), GNU Make 4.4.1

## 验证结果

```bash
# 上游测试（testall）
$ ./testall
Testing CRC routines: OK
Testing NMEA checksum: OK
**** All tests succeeded
# exit 0

# 消费者验证（conan create test_package，11 项公开 API 断言）
test_libcrc: ALL 11 consumer checks PASSED

# W3 本地 CI
L0_RESULT=pass / L1_RESULT=pass / L4_RESULT=pass / L5_RESULT=pass
Build Summary: Total 1, Success 1, Pass rate 100.0%
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 2.1KB | Makefile 直构建配方（无 configure） |
| conandata.yml | 347B | 官方 URL + SHA-256 |
| test_package/ | - | 消费者测试（11 项公开 API 断言）+ MANIFEST.yml |
| packaging/libcrc-2.0-ohos-aarch64.tar.gz | 25KB | 归档产物（lib/libcrc.a + include/checksum.h） |
| reports/test-report.md | 4.2KB | 上游测试双口径台账（2/2 独立用例，186 项断言） |

---

## 知识候选台账与查重（2026-09-18 第一轮）

### 候选 1: OHOS ELF 测试二进制需 .codesign 签名才能执行
- 真实错误: testall/tstcrc 执行 `Operation not permitted`（exit 126），chmod 后依旧
- 根因: OHOS 内核拒绝加载无 `.codesign` 签名段的 ELF；binary-sign-tool 不能覆盖已有签名段（"section already exists"）
- 修复/验证: E077 四步（llvm-objcopy 移除 .codesign → binary-sign-tool sign -selfSign 1 → chmod a+x）→ testall exit 0（本轮实测 logs/upstream-test-run.log）
- 适用范围: 所有 OHOS 上需要实际运行测试二进制/示例 CLI 的库
- 四范围查重: 正式知识 **E077** 精确覆盖（严重度1，linking/packaging/security）；无新增差异
- 结论: reuse_existing（E077）

### 候选 2: library 包类型必须声明标准 shared 选项
- 真实错误: `conan create` 报 "Package type is 'library', but no 'shared' option declared"
- 根因: Conan 2 的 library 包类型要求标准 shared 选项决定包 ID 与链接类型
- 修复/验证: 声明 options/default_options 后 conan create 通过（G2 PASS 实测）
- 适用范围: 所有 package_type=library 的 Conan 2 配方
- 四范围查重: 正式知识 **E283** 精确覆盖；无新增差异
- 结论: reuse_existing（E283）

### 候选 3: conan copy() 把 pattern 相对子路径拼接到 dst 之后导致包内嵌套
- 真实错误: test_package CMakeDeps 报 "Library 'crc' not found in package"；包内实际为 `lib/lib/libcrc.a`
- 根因: `copy(self, "lib/libcrc.a", dst=os.path.join(package_folder,"lib"))` → 实际落盘 `<pkg>/lib/lib/libcrc.a`；dst 必须是 package_folder 根
- 修复/验证: dst 改为 package_folder 本身 → 包内 `lib/libcrc.a` + `include/checksum.h` 布局正确，conan create 消费者链接通过（本轮实测）
- 适用范围: 所有 package() 中使用 copy() 带子路径 pattern 的 Conan 配方
- 四范围查重: 正式 E362（资源链接语义，部分相关）；草稿 **DRAFT-picojson-1.3.0-conan-copy-absolute-dst**（copy dst 语义，rec_approach=absolute-package-folder-dst）与 **DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include**（subdir-aware-copy-to-package-folder）已覆盖同根因
- 结论: causal_duplicate=partial（与两草稿同根因，本轮为 makefile 静态库场景的执行变体，无独立新增差异）→ 复用既有草稿知识

### 候选 4: 纯 Makefile 无 configure 的库需自定义 conan 配方（非 autotools 模板）
- 真实错误: conan-init 生成 autotools 模板，`autotools.configure()` 无 configure 脚本会失败
- 根因: 上游刻意不用 autoconf（Makefile 手工维护），conan-init 按 build_system 分类生成模板
- 修复/验证: conanfile.py 改为 source()+make 直构建+copy 打包，G2 干净构建通过（本轮实测）
- 适用范围: libcrc 类无 configure 的纯 Makefile 库
- 四范围查重: 正式 **E097**（no configure custom Makefile，bearssl 案例，custom-config-mk）相关；**E095**（硬编码编译器名）相关；**DRAFT-8958-clthreads-makefile-stage-install-shadow**、**DRAFT-cohomcalg-0.32-makefile-gxx-override** 等草稿覆盖 makefile 直构建变体
- 结论: trigger_overlap=true / solution_overlap=partial → 复用既有知识（E097 为正式条目），无独立新增差异

### 路径判断（知识库扩展/路径 B 评估）
- 七轴: exact_duplicate=true(候选1/2) / causal_duplicate=partial(候选3/4) / trigger_overlap=true(候选3/4) / solution_overlap=partial(候选3/4) / combination_novelty=false / boundary_novelty=false / test_migration_novelty=false
- similar_to: E077, E283, E095, E097, E362, DRAFT-picojson-1.3.0-conan-copy-absolute-dst, DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include, DRAFT-8958-clthreads-makefile-stage-install-shadow, DRAFT-cohomcalg-0.32-makefile-gxx-override
- caused_by: []; prerequisite_of: []; conflicts_with: []
- **决定: reuse_existing / path_a_no_knowledge** — 全部候选命中既有正式知识或已存在草稿，本轮无新增可跨库复用差异，不建 .md/.kv 草稿；路径 B（知识库扩展）不成立
