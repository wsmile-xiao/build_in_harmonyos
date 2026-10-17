## PR 信息
- **三方库名称**：curl
- **上游版本**：8.22.0
- **上游仓库地址**：https://codeload.github.com/curl/curl/tar.gz/refs/tags/curl-8_22_0
- **适配路径**：路径 A（基础适配，无补丁）+ 路径 B（知识贡献）
- **使用知识库**：curl-codeload-cmake-closure；curl-w3-openssl-include-and-drvfs-test-boundary；E7001 草稿

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1582 | `tests/runtests.pl` 要求集合；2072 项考虑、490 项能力跳过 |
| 集成测试 | 0 | 上游 runtests inventory 统一计入要求集合 |
| 其他测试 | 0 | 能力跳过项不计入要求集合分母 |
| **合计** | **1582** | 任务私有 ext4 证据 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1582 | 一致 | 1582/1582 通过 |
| 集成测试 | 0 | - | 无独立新增集成套件 |
| 鸿蒙特有测试 | 3 | 新增 | OHOS 目标 smoke：curl CLI 与 libcurl consumer |
| **合计** | **1585** | | 上游闭环加目标 smoke |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游测试源码和断言未改动；WSL DrvFs 的负时间戳限制只作为诊断证据，完整测试在任务私有 ext4 文件系统执行。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

目标 smoke 是平台验证，不替代上游测试，也不改变上游分母。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1582/1582（100%）
- 新增测试用例通过率：3/3（100%）

### 编译验证
- 编译器：clang 15（aarch64-unknown-linux-ohos）
- 编译状态：通过
- 构建系统：CMake + Conan
- 配置选项：OpenSSL/zlib 开启；brotli、zstd、libpsl、libssh2、HTTP/2、IDN、LDAP 和文档关闭；静态 libcurl 与 CLI

### 产物验证
| 项目 | 状态 | 详情 |
|------|------|------|
| 编译无错误 | PASS | CMake 配置、构建和安装完成 |
| 产物存在性 | PASS | OHOS AArch64 curl CLI 与 libcurl consumer |
| ELF 格式 | PASS | 目标机自签成功 |
| 运行测试 | PASS | 目标 smoke 3/3，target_rc=0，stderr=0，进程清零 |
| 动态依赖 | PASS | 精确依赖 openssl/3.5.8.1、zlib/1.3.2 |

### 补丁说明
无源码补丁。

### 依赖
- openssl/3.5.8.1
- zlib/1.3.2

### 测试结论
- 总体评价：任务私有 ext4 上游测试 1582/1582 通过，OHOS 目标 smoke 3/3 通过。
- 已知限制：WSL `/mnt/f` DrvFs/9p 不能保留 1940 年负 Unix mtime；本机 Linux x86_64 `conan create` 还缺依赖主机二进制，不能代替平台 CI。

### 遇到的问题与解决方案
- codeload 标签缺少生成的 Autotools `configure`，改用上游 CMake 入口。
- OpenSSL CMake include/library 路径固定到 Conan 包实际布局，避免主机库扩张闭包。
- WSL DrvFs 的时间戳限制通过任务私有 ext4 验证，未修改上游断言。

### 验证命令
```text
perl tests/runtests.pl -a -p -r !documentation
conan install --requires=openssl/3.5.8.1 --requires=zlib/1.3.2 --build=never -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

---

## 补充说明

- **关联 Issue**：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2778
- **队伍名称**：天天开心
- **申请人显示标识**：@2301_80739235
- **源分支**：feat/curl-8.22.0
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
