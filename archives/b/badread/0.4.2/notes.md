# badread 0.4.2 适配笔记

## 编译环境
- 构建系统: custom (pip wheel)
- 编译日期: 2026-07-28
- 编译器: python3 3.12.9 (纯 Python，无 C/C++ 编译)
- 状态: built

## 编译步骤

badread 是纯 Python 包（setuptools），构建流程：

1. 下载源码 tarball（19MB）：`https://github.com/rrwick/Badread/archive/refs/tags/v0.4.2.tar.gz`
2. 解压到 work 目录
3. 安装 Python 依赖（由宿主 pip 提供，非 conan 依赖）：
   - `pip3 install --user edlib numpy scipy matplotlib`
4. 构建 wheel：`python3 -m pip wheel . --no-deps`
   - 产物：`badread-0.4.2-py3-none-any.whl`（13MB）
5. 解压 wheel 到 `<prefix>/lib/python3.12/site-packages/`
6. 创建 `bin/badread` wrapper（解析同级 site-packages，注入 PYTHONPATH）
7. conan create 验证：`badread --version` 输出 `Badread v0.4.2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml 初始 sha256 错填 | 取自 gitcode 镜像返回的 3.5KB HTML 404 页面 | 重新计算真实 tarball sha256：`488ee2c4...` |
| 2 | conan create 卡在 source() 下载 | github.com 直连超时，ghfast.top/gitcode 镜像不可达或返回 HTML | 本地验证用 file:// URL 指向已下载 tarball 副本；CI 环境网络通畅用真实 HTTPS URL |
| 3 | conan 沙箱报 `pip: inaccessible or not found` | conan 沙箱 PATH 不含 ~/.local/bin（pip 所在） | 改用 `python3 -m pip` 并用 `shutil.which("python3")` 解析绝对路径 |
| 4 | test_package 报 `No module named badread` | wrapper 用 `python3 -m badread` 但未设 PYTHONPATH | 重写 wrapper：解析同级 `../lib/python3.12/site-packages` 并注入 PYTHONPATH |

## 源码修改

无源码修改，无补丁。badread 是纯 Python 包，无需修改源码。

## 依赖版本

Python 依赖（由宿主 pip 提供，非 conan 依赖）：
- edlib 1.3.9.post1（C 扩展，pip 自动编译）
- numpy 2.5.1
- scipy 1.17.1
- matplotlib 3.10.9
- Python >= 3.6（实际 3.12.9）

## 验证结果

```bash
$ conan create archives/b/badread/0.4.2/conanfile.py \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64

badread/0.4.2: Calling source()         ✅ 下载 + 解压
badread/0.4.2: Calling build()          ✅ python3 -m pip wheel
badread/0.4.2: Calling package()        ✅ 解压 wheel + 创建 wrapper
badread/0.4.2 (test package): RUN: bin/badread --version
Badread v0.4.2                          ✅ 实质验证通过
```

conan create 全流程通过：source → build → package → test_package。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| badread-0.4.2-py3-none-any.whl | ~13MB | pip wheel 构建产物 |
| bin/badread | <1KB | wrapper 脚本（解析 site-packages + 注入 PYTHONPATH） |
| lib/python3.12/site-packages/badread/ | ~13MB | 解压后的 Python 包 |

## 注意事项

- badread 是纯 Python 包，无 C/C++ 编译，无补丁
- 构建系统：pip wheel（`python3 -m pip wheel . --no-deps`）
- Python 依赖（edlib/numpy/scipy/matplotlib）由宿主 pip 提供，非 conan 依赖
- 本地验证用 file:// URL 绕过网络受限（github.com 直连超时）
- conan 沙箱找不到 pip，需用 `python3 -m pip` + `shutil.which("python3")` 解析绝对路径
- wrapper 必须解析同级 `../lib/python3.12/site-packages` 并注入 PYTHONPATH，否则 `No module named badread`
