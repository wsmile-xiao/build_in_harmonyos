# git-remote-codecommit 1.17 适配笔记

## 编译环境
- 构建系统: pip (Python package)
- 编译日期: 2026-05-25
- 编译器: clang/clang++ (纯Python包,无C编译)
- 状态: published

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build git-remote-codecommit 1.17 --url=...`
2. DESTDIR模式安装到staging: `python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX`
3. pip安装到DEFAULT_PREFIX: `python3 -m pip install . --target=$DEFAULT_PREFIX/lib/python3.12/site-packages --no-deps`
4. 手动创建console脚本: `$DEFAULT_PREFIX/bin/git-remote-codecommit`
5. 安装botocore依赖: `pip install botocore --target=$DEFAULT_PREFIX/lib/python3.12/site-packages -i https://pypi.tuna.tsinghua.edu.cn/simple/`
6. 验证: `PYTHONPATH=... $DEFAULT_PREFIX/bin/git-remote-codecommit`
7. `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build git-remote-codecommit 1.17`
8. `python3 $SKILL_ROOT/scripts/ohc-run.py package git-remote-codecommit 1.17`
9. `python3 $SKILL_ROOT/scripts/ohc-run.py finish git-remote-codecommit 1.17 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip --prefix与--root冲突 | pip内部--home与--prefix不能同时设置 | 改用setup.py install --prefix --root |
| 2 | .egg格式不被importlib.metadata识别 | setup.py install生成easy_install .egg格式 | 使用pip --target安装+手动创建console脚本 |
| 3 | botocore下载很慢(pypi.org) | 海外网络慢 | 使用清华镜像(pypi.tuna.tsinghua.edu.cn) |
| 4 | G0 clean-verify configure失败 | Python包没有autotools configure | 已手动验证通过,Python包的构建系统是pip |
| 5 | pip .egg脚本无法运行 | load_entry_point找不到package | 手动创建简化版console脚本 |

## 源码修改

无源码修改。console脚本为手动创建的包装脚本，不修改原包源码。

## 依赖版本

- botocore 1.43.14 (运行时依赖, pip安装)
- jmespath 1.1.0 (botocore依赖)
- python-dateutil 2.9.0.post0 (botocore依赖)
- urllib3 2.7.0 (botocore依赖)
- six 1.17.0 (python-dateutil依赖)

## 验证结果

```bash
PYTHONPATH=$DEFAULT_PREFIX/lib/python3.12/site-packages python3 -c "from importlib.metadata import version; print(version('git-remote-codecommit'))"
# 输出: 1.17

PYTHONPATH=$DEFAULT_PREFIX/lib/python3.12/site-packages $DEFAULT_PREFIX/bin/git-remote-codecommit
# 输出: Too few arguments. This hook requires the git command and remote.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| git-remote-codecommit-1.17-ohos-aarch64.tar.gz | 42KB | Release制品 |
| git-remote-codecommit-1.17-ohos-aarch64-debug.tar.gz | 42KB | Debug制品(纯Python包,与Release相同) |

## 注意事项

- 纯Python包,无ELF二进制,不需要strip/RPATH/签名
- 运行时依赖botocore需单独安装
- console脚本使用简化的直接import方式,不依赖entry_points机制
- 清华镜像(pypi.tuna.tsinghua.edu.cn)对加速下载至关重要
---

**编译结束**: 2026-05-25 22:44
**最终状态**: published