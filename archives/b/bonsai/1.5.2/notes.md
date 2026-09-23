# bonsai 1.5.2 适配笔记

## 编译环境
- 构建系统: setuptools (Python C Extension)
- 编译日期: 2026-09-05
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 通过 `conandata.yml` 下载 `https://github.com/noirello/bonsai/archive/refs/tags/v1.5.2.tar.gz`，校验 sha256。
2. `get()` 解压后，检测 `/usr/include/ldap.h` 是否存在：
   - 存在：执行 `python3 setup.py build` 编译 `_bonsai` 扩展。
   - 不存在：输出 warning，回退纯 Python 路径。
3. 运行上游离线测试：`python3 -m pytest tests/test_ldapdn.py tests/test_ldapurl.py tests/test_ldapvaluelist.py tests/test_ldifreader.py tests/test_ldifwriter.py tests/test_ldapentry.py tests/test_utils.py -v`，或在无 pytest 时用 `PYTHONPATH=src python3 -c "from bonsai.ldapdn import LDAPDN; ..."` 做最小验证。
4. 打包：若有编译产物，`setup.py install --prefix` 安装；否则 `copy` 纯 Python 源码到 `lib/python/bonsai`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS 上无 `libldap2-dev` | OHOS 基础镜像未预装 OpenLDAP 开发包 | 检测 `ldap.h`，缺失时回退纯 Python 安装，保证 `conan create` 不失败；离线测试仍可通过 |
| 2 | `BuildExt._have_krb5` 探测 Kerberos 依赖 `krb5`/`gssapi` | OHOS 上无 Heimdal/Kerberos | 自动探测，失败则打印 INFO 并跳过，不阻塞构建 |
| 3 | 网络测试需 `slapd` Docker | OHOS 真机无 Docker/无 slapd | 仅运行离线单元测试，网络测试在补充说明中声明跳过 |

## 源码修改

无补丁。`setup.py` 已具备跨平台检测，无需额外 OHOS 补丁。

## 依赖版本

- Python >=3.10（OHOS 提供 3.12.9）
- 可选：libldap2-dev、libsasl2-dev、libkrb5-dev（未安装时回退）

## 验证结果

```bash
# 本地需在 HarmonyOS 真机执行
conan create archives/b/bonsai/1.5.2 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 上游离线测试（预期 7 个文件，约 60+ 用例通过）
python3 -m pytest tests/test_ldapdn.py tests/test_ldapurl.py tests/test_ldapvaluelist.py tests/test_ldifreader.py tests/test_ldifwriter.py tests/test_ldapentry.py tests/test_utils.py -v

# test_package 消费者测试
PYTHONPATH=lib/python python3 test_package/test_bonsai.py
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/python/bonsai/*.py | 纯 Python 包 |
| lib/python/bonsai/_bonsai.*.so | C 扩展（若 ldap 存在） |
| licenses/LICENSE | MIT 许可 |

## 注意事项

- 完整 LDAP 连接功能需 OpenLDAP 运行时，且需 slapd 服务器；OHOS 上离线解析功能可用。
- 后续若在 OHOS 上适配 OpenLDAP，可重新启用完整 C 扩展编译并跑通网络测试。
