# muscle 5.3 适配笔记

## 编译环境
- 构建系统: custom (vcxproj_make.py 将 VS .vcxproj 转为 Makefile)
- 编译日期: 2026-09-10
- 编译器: clang/clang++ (OHOS 平台自带)
- 状态: published

## 软件信息
- 名称: MUSCLE (Multiple Sequence Comparison by Log-Expectation)
- 版本: 5.3
- 仓库: https://github.com/rcedgar/muscle
- 许可证: GPL-3.0
- 类型: 命令行工具（多序列比对生物信息学软件）
- 依赖: 无外部依赖（self-contained）

## 构建系统分析

MUSCLE v5.3 使用非标准构建系统：
1. 源码 `src/` 目录包含 `muscle.vcxproj`（Visual Studio 项目文件）和大量 .cpp/.h 源文件
2. 构建脚本 `build_linux.bash` 下载 `vcxproj_make.py`（来自 https://raw.githubusercontent.com/rcedgar/vcxproj_make/806d016/vcxproj_make.py）
3. `vcxproj_make.py` 解析 .vcxproj 文件提取所有 .cpp 源文件列表
4. 生成 Makefile，设置编译器选项（-ffast-math -march=native -O3 -DNDEBUG）
5. 运行 make 编译所有 .cpp → .o，然后链接为单个二进制 `bin/muscle`

### Makefile 关键逻辑
- `CXX = g++`（可通过 `--cppcompiler` 参数修改）
- `CXXFLAGS = $(CFLAGS) -ffast-math -march=native -O3 -DNDEBUG -fopenmp`
- `LDFLAGS = $(LDFLAGS) -ffast-math -march=native -O3 -fopenmp`
- Linux 平台追加 `-static`（但 OHOS `uname -s` 返回 "HarmonyOS"，不匹配 Linux 分支）
- 非调试模式自动 `strip` 二进制

## 编译步骤

```bash
# 1. 下载 vcxproj_make.py
curl -fsSL https://raw.githubusercontent.com/rcedgar/vcxproj_make/806d016/vcxproj_make.py > vcxproj_make.py

# 2. 初始化 git 仓库（vcxproj_make.py 需要 git log 生成 gitver.txt）
git init && git add -A && git commit -m "init"

# 3. 运行 vcxproj_make.py（使用 OHOS clang++ 替代默认 g++）
python3 vcxproj_make.py --cppcompiler clang++ --ccompiler clang --openmp

# 4. 编译成功，二进制输出到 ../bin/muscle
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | vcxproj_make.py shebang `#!/usr/bin/python3` 在 OHOS 不存在 | OHOS python3 路径不是 /usr/bin/python3 | 使用 `python3 vcxproj_make.py` 而非 `./vcxproj_make.py` 执行 |
| 2 | vcxproj_make.py 需要 git 仓库生成 gitver.txt | 脚本调用 `git log` 生成版本号文件 | 在源码目录 `git init && git add -A && git commit` |
| 3 | 默认编译器为 g++，OHOS 使用 clang++ | 上游 CI 使用 g++，OHOS 平台使用 clang++ | 通过 `--cppcompiler clang++ --ccompiler clang` 参数指定 |
| 4 | 二进制无法本地执行（Operation not permitted） | OHOS ELF 签名要求，未签名二进制不可执行 | CI 流水线 sign.sh 签名后可执行，本地编译验证通过即可 |

## 源码修改

无源码修改。MUSCLE 源码本身在 OHOS clang++ 下编译无错误，仅需通过 vcxproj_make.py 参数适配编译器。

## 依赖版本

- 无外部依赖（README 明确说明 self-contained, no dependencies）
- OHOS clang++ 15.0.4
- OHOS libc (musl)
- OpenMP (libomp.so，OHOS clang 自带支持)

## 验证结果

```bash
# 编译验证
$ python3 vcxproj_make.py --cppcompiler clang++ --ccompiler clang --openmp
# → make done. (无编译错误)
$ ls -lh ../bin/muscle
# → -rwxrwx--- 1.0M ../bin/muscle
$ file bin/muscle
# → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
$ readelf -d bin/muscle | grep NEEDED
# → NEEDED: libc++_shared.so, libomp.so, libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/muscle | 1.0M | MUSCLE v5.3 aarch64 二进制（动态链接） |

## 注意事项

1. MUSCLE 构建系统非标准（vcxproj_make.py），conanfile.py 需要在 build() 中手动下载 vcxproj_make.py 并执行
2. OHOS 上 `uname -s` 返回 "HarmonyOS" 而非 "Linux"，因此 Makefile 中 `-static` 链接分支不会触发，二进制为动态链接
3. 二进制依赖 libomp.so（OpenMP 运行时），需在 package_info 中声明
4. 构建需要在源码目录初始化 git 仓库（vcxproj_make.py 调用 git log 生成 gitver.txt）
5. vcxproj_make.py 的 shebang 为 `#!/usr/bin/python3`，OHOS 需用 `python3` 命令执行
---

**编译结束**: 2026-09-10 16:26
**最终状态**: published
