# aghermann 1.1.2 — 系统 cairo-gobject 的 ffi 未定义符号导致 ld.lld 链接失败 (draft)

**Category**: build-system | link | ohos · **Severity**: 3 · **Tool**: ld.lld/conan/autotools

## 症状

1. CI `conan create` 在链接 `aghermann` 可执行文件时报：
   `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: ffi_type_void / ffi_prep_cif / ffi_call …`
   `>>> referenced by /storage/Users/currentUser/usr/local/lib/libcairo-gobject.so`。
2. 报错路径指向**系统目录** `~/usr/local/lib`，而非 conan 缓存内的 cairo 包。
3. 本地（同配置、同 profile）构建完全通过，无法复现——只在部分 CI worker 上失败（本次 BUILD58825，Worker OpenHarmonyPCDeveloper-CI-020，PR #10748 CI #51119）。

## 根因

- 部分 CI worker 的系统路径 `~/usr/local/lib` 下存在一份 `libcairo-gobject.so`。autotools 的
  pkg-config/链接搜索顺序可能命中它，而不是 conan 依赖图里的 cairo 包内版本。
- 该系统库编译时引用了 libffi 的 `ffi_*` 符号，但链接 aghermann 的命令行没有把 libffi 传进来
  （系统库不提供 `.pc` 元数据补充私有依赖）。
- `ld.lld` 对共享库的未定义符号默认 `--no-allow-shlib-undefined`，直接判错——这是 ld.lld 与
  GNU ld 的行为差异（GNU ld 在 `-shared` 目标上默认更宽松）。
- **本地过、CI 挂的本质**：本地机器没有这份系统 `libcairo-gobject.so`（实测本地
  `~/usr/local/lib` 无任何 cairo/ffi 文件），链接器只见到 conan 包内自洽的 cairo，错误路径
  根本不成立。环境差异类失败，同一配方无法在本地复现。

## 处置（可复用）

1. **链接注入 `-Wl,--allow-shlib-undefined`**（OHOS 分支，conanfile `generate()` 的
   `AutotoolsToolchain.extra_ldflags`）：显式允许共享库带未定义符号，运行时由系统加载器解析
   （glib/gobject 运行时本身会加载 libffi，符号实际可达）。仓库先例：
   address-standardizer/3.7.0 周期 27，同一 ld.lld 已验证支持该旗标（注意 `--weak-unresolved-symbols`
   是 GNU binutils 专属，ld.lld 不支持，勿用）。
2. **不要换 libffi/cairo 版本来"修"这个问题**：失败节点是 worker 系统库，不在 conan 依赖图内；
   ayatana-ido/0.10.4-v2 的 libffi RREV 锁定解决的是"CCI 配方 vs 仓内配方"的节点竞争，与本案
   的系统库污染是两个层面。
3. **判别指纹**：报错含 `--no-allow-shlib-undefined` + `referenced by ~/usr/local/lib/…` 即可
   断定是系统库被链入，直接套本方案；若 referenced 路径在 conan 缓存内，则是依赖图缺声明，
   应走 `requirements()` 补依赖路线。

## 验证

- 本地 W3 模拟（`CI_PACKAGES=archives/a/aghermann/1.1.2 zsh ci/conan/build_and_test.sh`）：
  L0/L1/L5 全 pass，Build Summary 1/1 success（本地本就无法复现系统库路径，验证的是
  flag 注入不破坏正常构建）。
- 最终以 CI 新构建（SHA 429ac793，/rebuild 触发）在真实 worker 上的结果为准。
