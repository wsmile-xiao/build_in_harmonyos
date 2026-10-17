# libcyaml 1.4.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（aarch64-linux-ohos）/ llvm-ar
- 状态: built（conan-verify G1-G4 通过，制品未上传）

## 编译步骤

libcyaml 是纯 Makefile 工程（无 configure 脚本），Conan 配方内直接驱动 make：

```bash
# 依赖 libyaml/0.2.5 头文件/库路径经环境变量注入（R49 私有 prefix）
CPPFLAGS='-I<libyaml>/include' LDFLAGS='-L<libyaml>/lib -lyaml' \
  make -C <源码目录> VARIANT=release CC=clang AR=llvm-ar
```

- `make -C {source_folder}`：basic_layout 把 Conan build cwd 放在 build-release/，
  而 Makefile 在源码根，必须 -C 回到源码目录
- 依赖路径用环境变量注入而非 make 命令行参数：上游 Makefile 使用
  `CPPFLAGS += $(VERSION_FLAGS)`，命令行 CPPFLAGS 会覆盖 += 导致 -DVERSION_* 宏缺失
- 不用 `-j$(nproc)`：本机文件系统拒绝 jobserver FIFO（E074）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: *** No targets specified and no makefile found` | basic_layout 构建 cwd 在 build-release/，Makefile 在源码根 | build() 用 `make -C {self.source_folder}` |
| 2 | `use of undeclared identifier 'VERSION_MAJOR'` | make 命令行 CPPFLAGS 覆盖了 Makefile 的 `CPPFLAGS += $(VERSION_FLAGS)` | 依赖路径改经环境变量注入（env 会被 += 追加） |
| 3 | `make: jobserver mkfifo: Operation not permitted` | 文件系统拒绝 mkfifo（E074） | 不启用 -j，串行 make |

## 源码修改

无（零补丁，官方源码原样编译；patches/ 仅保留 .gitkeep）

## 依赖版本

- libyaml/0.2.5（ohpcd 制品仓已发布，conan download 验证）

## 验证结果

```bash
# conan 配方验证（G1-G4 全过，test_package 2/2）
python3 scripts/ohc-run.py conan-verify libcyaml 1.4.2
# 上游全量测试（两二进制均 382/382）
./build/release/test/units/cyaml-shared   # PASS: 382 of 382
./build/release/test/units/cyaml-static   # PASS: 382 of 382
# 鸿蒙专项（test_package/ohos_test.c UTF-8 中文往返）
ctest --test-dir test_package/build/...   # 2/2 passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 型 Conan 配方（make -C + env 注入依赖） |
| conandata.yml | 官方 https://github.com/tlsa/libcyaml v1.4.2 tag 归档 + SHA-256 |
| test_package/ | 消费者测试 test.c + 鸿蒙专项 ohos_test.c |
| knowledge/drafts/DRAFT-libcyaml-1.4.2-makefile-conan-env-cppflags.{kv,md} | 路径 B 知识草稿（纯 Makefile 配方写法） |

## 注意事项

- W3 本地 CI 首次 full 整仓扫描命中 main 上其他库历史垃圾文件（embree/flatcv/libmorton 等 9 项），
  与 libcyaml 无关（详见 reports/baseline-noise-log.md）；提交后 incremental 口径（与 CI prdiff 同源）通过
- 本机 github.com 直连超时，源码经官方 tag 镜像下载并核验 SHA-256（3211b2a0…d16dc）

---

**编译结束**: 2026-09-03 04:06
**最终状态**: built
