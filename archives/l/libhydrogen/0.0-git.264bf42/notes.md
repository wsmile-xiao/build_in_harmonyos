# libhydrogen 0.0-git.264bf42 适配笔记

## 基本信息

- 上游：https://github.com/jedisct1/libhydrogen ，master @ `264bf42`
  （无 release tag，上游以 master 为活跃分支；本机实测 master 快照与
  264bf42 提交内容 `diff -r` 零差异，refs/heads/master.tar.gz 即该提交快照）
- 形态：C 库（单一翻译单元 hydrogen.c + impl/*.h），上游自带 CMakeLists
- 许可证：ISC
- 版本号：`0.0-git.264bf42`（上游无版本号约定，按仓库惯例用
  `0.0-git.<短hash>` 表达快照版本）

## 适配过程

1. **W0 依赖审计**：零第三方依赖——随机数取自 `impl/random/unix.h`
   （`__unix__` 分支：`open`/`read`/`poll` 读 `/dev/urandom`，纯 POSIX，
   musl/OHOS 兼容，无 glibc 专有 API）；Gimli 置换 aarch64 后端为纯 C
   宏实现（无内联汇编），天然可移植。
2. **构建**：上游 CMake 原生支持交叉编译，零补丁。关键点：
   - `-march=native` 仅在 `NOT CMAKE_CROSSCOMPILING` 时注入，OHOS
     交叉构建（CMAKE_SYSTEM_NAME=HarmonyOS）自动跳过，无需处理；
   - 交叉编译时上游把 `hydrogen-tests` 目标设为 `EXCLUDE_FROM_ALL`
     （防 Arduino/AVR 等场景误编），配方显式
     `cmake.build(target="hydrogen-tests")` 编译测试，`can_run()` 为真
     时在 build() 内直接运行（本机 OHOS arm64 可执行）。
3. **镜像**：GitHub 直连不可达（本机实测 curl 000），ghfast.top 镜像可达；
   conandata 用镜像在前 + 官方兜底的 URL 列表，两源 sha256 实测一致
   （`ae4768db…beba5`）。

## 测试范围

- **上游测试**：CMake `enable_testing()` + 1 个 `add_test`（`hydrogen-tests`
  单可执行文件，rule4 口径 N=1），内含 11 个 assert 型测试函数：
  core/hash/kdf/kx_n/kx_kk/kx_xx/kx_nk/pwhash/randombytes/secretbox/sign。
  build() 内运行 exit 0，11/11 通过。
- **消费者测试**（test_package）：24 条断言，覆盖 hydro_init、
  hydro_sign_keypair 生成 + hydro_sign_create/hydro_sign_verify 签名验证
  往返（主场景）、错误密钥/篡改签名/篡改密文拒绝、确定性 keygen 复现、
  增量签名状态 API、secretbox 加解密往返、hash/kdf 复现。24/24 通过。

## musl 兼容性（W0 核验）

- 随机数：`__unix__` → `random/unix.h`，仅用 `open`/`read`/`close`/
  `poll`/`errno`，无 `getrandom` syscall、无 glibc 扩展；
- 内存/字符串：标准 `mem*`/`str*`；
- 线程局部存储：`static TLS` 结构体，musl 支持；
- 结论：musl 全兼容，无需任何源码补丁。

## 复现命令

```bash
conan create . \
  -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

## 已知限制

- 上游 CMake 只安装静态/动态库与头文件，不安装 pkg-config 文件
  （package_info 中以 set_property 补齐 pkg_config_name=hydrogen）。
- 交叉 CI worker（非 OHOS arm64 宿主）上 `can_run()` 为假时，
  上游套件与消费者测试编译为产物、在目标机执行。
