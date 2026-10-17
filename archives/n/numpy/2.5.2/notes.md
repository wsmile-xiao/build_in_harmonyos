# numpy 2.5.2 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: vendored meson 1.11.1（sdist 自带，含 features 模块）
- 编译器: clang 15（DevBox, /data/service/hnp/bin/clang）
- 链接器: ld.bfd（-fuse-ld=bfd；ld.lld 依赖未安装的 libxml2.so.16）
- Python: 3.12.9（~/usr/local，非 HNP，setup_wizard 安装）
- OpenBLAS: 0.3.34（conan 预编译包）
- 状态: published（conan create 全流程通过）

## 与先前尝试的差异（为什么这个版本能过 CI）

| 尝试 | 版本 | 致命问题 | 本配方对策 |
|------|------|----------|-----------|
| #3950 | 2.5.1 | ① conandata.yml sources 用列表格式与 conanfile 解包不匹配（P0）② GitHub tag 归档不含子模块，构建期二次下载 ③ 8月4日后无任何提交，停滞 4 周 | sources 用 dict 格式（与 get(**self.conan_data["sources"]) 匹配）；改用 PyPI sdist |
| #5882 | 2.5.2 | AI review 通过但 CI 卡源码下载：files.pythonhosted.org 对 Worker 不可达；子模块经 ghfast.top 镜像下载，同样有外网依赖 | 源码改清华 PyPI 镜像（实测可达、sha256 同源）；sdist 自带子模块，零二次下载 |
| #6386 | 1.26.4 | meson CPU 探测按 x86 处理（-xop -fma4），ARM64 编译失败；8 次 /rebuild 全挂 | -Dcpu-baseline=min -Dcpu-dispatch=default，ARM 安全基线 |

## 构建步骤（conanfile.py 自动化）

1. `conan create` → source() 从清华镜像拉 sdist（自带 vendored-meson、highway、pocketfft、pythoncapi-compat 四个子模块）
2. OHOS 适配：
   - sitecustomize.py 补丁 posix_spawn 不搜 PATH 的问题
   - native file 固定 clang/ld.bfd，链接参数加 -L{python_lib} -lpython3.12（musl 不导出主 exe 符号）
   - exe_wrapper = 签名 + 运行（OHOS 未签名 ELF 不可执行）
3. vendored meson setup -Dblas=openblas -Dlapack=openblas -Dcpu-baseline=min -Dcpu-dispatch=default
4. ninja 编译 330+ 目标
5. meson install → 打包 site-packages
6. binary-sign-tool 签名所有 .so
7. test_package: python3 -S 跑 test_numpy.py（import/算术/BLAS dot/linalg 逆矩阵）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 clang/cython | OHOS posix_spawn 不搜索 PATH | sitecustomize.py 补丁 subprocess.Popen |
| 2 | Module "features" does not exist | GitHub tag 归档子模块为空 | 用 PyPI sdist（子模块齐全） |
| 3 | clang 链接失败 | lld 依赖 libxml2.so.16 未装 | -fuse-ld=bfd |
| 4 | sanity check 失败 Permission denied | 未签名 ELF 禁止执行 | exe_wrapper 签名后运行 |
| 5 | sizeof 返回 -1 | -fuse-ld=bfd 误入 c_args | 仅放 c_link_args/cpp_link_args |
| 6 | import 时 PyModule_AddObject 未定义 | musl 不导出主 exe 符号 | 链接 -lpython3.12 |
| 7 | import 时 .so Permission denied | OHOS ELF 必须签名 | binary-sign-tool selfSign 全部 .so |
| 8 | CI 源码下载超时 | Worker 访问不了 pythonhosted/github | 清华镜像 + sdist 子模块自足 |
| 9 | x86 SIMD 探测失败 | CPU 选项默认按宿主/x86 探测 | cpu-baseline=min, cpu-dispatch=default |

## 验证结果（2026-09-01 conan create 完整通过）

- `conan create . --user=ohpcd --channel=stable -pr:h/-pr:b=ohos-aarch64 --build=missing` **全流程 PASS**：
  export → source（清华镜像 sdist）→ patch（tooldetect ninja fallback）→ meson setup（lld + 自动签名）→ ninja 337/337 → package（--no-rebuild）→ **test_package 7/7 PASS**
- test_package 验证：import / 版本 / 算术 / BLAS dot=32 / mean / reshape / linalg.inv（openblas+LAPACK 集成验证）
- 上游 pytest 全量统计见 PR 正文（已按模块全量运行：_core 36602 passed/71 failed——全部为 longdouble 浮点异常的 musl 平台差异；linalg/ma/fft/lib/polynomial 等模块 100% 通过；f2py 工具链自测豁免）
