# E429 — clibs 单文件 C99 库（Makefile 无 configure/无 make install）的自定义 Conan 配方

## 错误特征

```
No rule to make target 'install'
make: *** No rule to make target 'configure'
make install: *** No rule to make target 'install'
bytes.c:46:3: warning: call to undeclared function 'asprintf' ...
```

## 触发条件

- 构建系统: makefile（clibs 风格单文件 C99 库，如 bytes 0.0.4）
- 阶段: build / package
- 上游 Makefile 只提供 `test` 目标（编译并运行断言式 test.c），无 `configure`、无 `make install`、无库构建目标

## 根因分析

clibs 风格单文件 C99 库的上游 Makefile 面向"下载即编译即测试"的开发流：`make test` 编译 test.o + bytes.o 并直接运行，不提供库目标（.a/.so）也不提供 install 目标。通用 Autotools/CMake 模板配方（autotools.configure() / cmake）无法直接使用；即使硬改也会在 `make install` 处失败。

## 解决方案

### 推荐方案
自定义 Conan 配方（build() + package() 手动完成）：
1. `build()`：编译器从 Conan conf 读取（`tools.build:compiler_executables`，R33 不依赖空 shell 环境变量），直接
   `cc -std=c99 -Wall -Wextra -fPIC -c bytes.c -o bytes.o` → `llvm-ar rcs libbytes.a bytes.o` → `llvm-ranlib libbytes.a`；`shared` 选项时另编 libbytes.so
2. `package()`：手动 `copy()` 安装 `bytes.h` → `include/`、`libbytes.a`（可选 `.so`）→ `lib/`
3. `package_info()`：`self.cpp_info.libs = ["bytes"]`
4. 上游测试入口为 `make test` 单入口全量运行（断言式函数，非框架 TEST_CASE）：双口径台账时按"独立断言式测试函数"计数（如 bytes 的 test_string_to_bytes / test_bytes_to_string 两个独立用例）
5. test_package 增加消费者测试（仅经公开头文件调用 API）+ 鸿蒙专项测试（如 >4GB long long 边界、asprintf 内存可释放性、整除截断语义），CMake 注册独立 ctest 用例

### 禁止做法
- ❌ 使用 Autotools 模板配方硬套（无 configure 必然失败）
- ❌ 依赖空 shell 环境变量 `${CC}`（release worker 上为空 → 静默失败，R33）
- ❌ 伪造 make install 目标或手工修改上游 Makefile 提交（无补丁必要）

## 验证

```bash
make test                                    # 上游测试 exit 0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
ctest --test-dir test_package/build/clang-15-armv8-17-release   # 消费者 + 鸿蒙专项全部通过
```

实测：bytes 0.0.4 经 conan-verify G0-G4/L2/L4/L5 全通过，上游 2/2 用例通过（100%），
鸿蒙专项 3/3 通过，消费者验证通过。

## 关联条目

- 相关: E097（BearSSL 自定义 Makefile 手动安装，多文件复杂库）、E271（单文件 release asset 自定义配方）
