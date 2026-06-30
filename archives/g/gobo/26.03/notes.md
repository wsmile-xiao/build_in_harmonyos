# gobo 26.03 适配笔记

## 编译环境
- 构建系统: custom（Eiffel Bootstrap，非 autotools/cmake/meson）
- 编译日期: 2026-06-26
- 编译器: clang/clang++（LLVM 15.0.4）
- 状态: published
- 平台: HarmonyOS aarch64

## 编译步骤

Gobo Eiffel 26.03 使用 Bootstrap 机制编译，不使用 configure/make：

1. **下载源码**: `curl --max-time 600 -L -o gobo-26.03.tar.gz https://downloads.sourceforge.net/project/gobo-eiffel/gobo-eiffel/26.03/gobo-26.03.tar.gz`
2. **初始化**: `python3 ohc-run.py init-build gobo 26.03`（解压、创建工作副本）
3. **创建 pthread stubs**: 编译 `pthread_stubs.c`（提供 `pthread_setcancelstate` 和 `pthread_cancel` 的 stub 实现），修改 `clang.cfg` 将 stub 链入
4. **修改 bootstrap.sh**: 将 `STRIP=strip` 改为 `STRIP=echo`（strip 会破坏 HarmonyOS ELF 执行权限）
5. **Bootstrap 编译**: `sh bootstrap.sh -v clang`（3 轮引导：C源码→gec0→gec1→gec）
6. **工具编译**: 用 gec 逐一编译 12 个 Eiffel 工具（gecc, geant, gedoc, getest, gelint, gecop, gelsp, geimage, gelex, geyacc, gepp, gexslt）
7. **打包**: 将 13 个二进制打包为 `gobo-26.03-ohos-aarch64.tar.gz`

关键命令:
```bash
export GOBO="/path/to/gobo-26.03.work"
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH"
cd "$GOBO/bin"
# Bootstrap (修改后，无 strip)
sh "$GOBO/tool/gec/bootstrap/bootstrap.sh" -v clang
# 编译各工具
./gec --finalize "$GOBO/tool/gecc/src/system.ecf"
./gec --finalize "$GOBO/tool/geant/src/system.ecf"
# ... 其他工具类似
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SourceForge 下载超时 | 网络到 SF 慢 | 用 curl --max-time 600 下载 |
| 2 | `pthread_setcancelstate` / `pthread_cancel` 链接失败 | HarmonyOS bionic libc 不提供这两个函数 | 创建 pthread_stubs.c stub 实现，修改 clang.cfg 的 libs_gc 添加 stub .o |
| 3 | strip 后二进制无法执行 (Operation not permitted) | HarmonyOS 安全机制：strip 修改 ELF 后签名失效 | 修改 bootstrap.sh 设 STRIP=echo 跳过 strip |
| 4 | install.sh 调用 bootstrap.sh 重新 strip | install.sh 内部调用 bootstrap.sh | 创建修改版 install.sh 跳过 bootstrap 和 strip |
| 5 | Conan env 参数格式错误 | Conan 2.x 要求 env 为 list 而非 dict | 改用 os.environ 直接设置环境变量 |
| 6 | clang.cfg 替换导致 stub 重复链接 | 字符串替换 `libs_gc:` 匹配了已修改行 | 使用精确匹配（含换行符 `libs_gc: -ldl\n`） |
| 7 | test_package 使用 Conan 1.x API | deps_cpp_info 在 Conan 2.x 不存在 | 改用 self.dependencies["gobo"].package_folder |

## 源码修改

### 补丁: 0001-tool-gec-backend-c-config-clang.cfg.patch
- **文件**: `tool/gec/backend/c/config/clang.cfg`
- **修改**: 在 `libs_gc` 变量中添加 pthread stubs 对象文件路径
- **原因**: HarmonyOS libc 缺少 `pthread_setcancelstate` 和 `pthread_cancel`，需通过 stub 提供链接符号

### 运行时修改（非源码补丁，构建脚本修改）
- `bootstrap.sh`: `STRIP=strip` → `STRIP=echo`（不生成补丁，构建时动态修改）
- `pthread_stubs.c`: 新建文件，提供 stub 函数（构建时动态生成）

## 依赖版本

- clang: 15.0.4 (LLVM, path: /data/service/hnp/bin/clang)
- strip: /data/service/hnp/bin/strip（未使用，因 strip 破坏 ELF 执行）
- musl libc: /lib/ld-musl-aarch64.so.1
- Conan: 2.12.0

## 验证结果

```bash
$ ./gec --version
gec version xx.xx.xx+xxxxxxx

$ readelf -d ./gec | grep NEEDED
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]

$ ./gelex test_lex.l  # 功能测试
（成功生成 Eiffel 词法分析器类）

$ ./geyacc test_yacc.y  # 功能测试
（成功生成 Eiffel 语法分析器类）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/gobo-26.03-ohos-aarch64.tar.gz | 54.4MB | 13 个编译工具的打包归档 |
| patches/0001-tool-gec-backend-c-config-clang.cfg.patch | +5/-2 | clang.cfg pthread stubs 补丁 |

## 注意事项

1. **不可 strip**: HarmonyOS 上 strip 后的 ELF 二进制无法执行（ELF 签名失效），必须保留未 strip 版本
2. **pthread stubs**: 需要 pthread_stubs.o 提供缺失的 `pthread_setcancelstate` 和 `pthread_cancel` 符号
3. **GOBO 环境变量**: 编译和运行时必须设置 `GOBO` 指向源码根目录
4. **版本字符串**: 显示 "xx.xx.xx+xxxxxxx" 占位符，需设置 CI 环境变量 `GOBO_VERSION` 才能显示真实版本
5. **GC Warning**: "Failed to find PT_GNU_RELRO segment" 警告来自 Boehm GC，非致命，不影响功能

---

**编译结束**: 2026-06-26 02:29
**最终状态**: published
