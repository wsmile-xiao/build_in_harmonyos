# advocate

## 软件描述

advocate 是一个纯 Python 库，为 `requests` 提供防 SSRF（服务端请求伪造）封装：校验每次实际建连的目标地址，拦截内网/回环/保留地址与 DNS 重绑定，并合理处理重定向（`advocate.get()` 可直接替换 `requests.get()`）。

## 功能概述

- **地址校验**：`AddrValidator` 判定 IP 是否允许建连（黑名单/白名单、私有/回环/组播/保留地址全覆盖）
- **请求封装**：`advocate.Session` / `RequestsAPIWrapper` / 模块级 `get/post/...`，与 requests 同接口
- **连接校验**：在 socket 层统一校验（含重定向的每一次建连），防范 DNS 重绑定
- **异步支持**：`advocate.futures.FuturesSession`（requests-futures 封装）

## OHOS 适配

### 构建方式

- **纯 Python noarch**：无编译——`package()` 用 `shutil.copytree` 拷贝 `advocate/` 模块到 site-packages
- 绕过 setuptools 构建；运行时依赖 pip 定版 vendor 到包内 `deps/`（requests==2.32.3、urllib3==1.26.20、six；netifaces 改为可选导入不再 vendor）
- `runenv_info.PYTHONPATH` 暴露导入路径给消费者

### 关键攻坚点

1. **sdist 缺测试辅助文件**：上游 PyPI 包缺 `test/__init__.py` 与 `test/monkeypatching.py`（git tag 有），补丁按上游原文补回后 pytest 可收集 48 个用例
2. **urllib3 大版本锁定**：advocate 1.0.0 引用 2.x 已删除的内部 API，只能用 urllib3 1.26.x
3. **上游测试实测**：pytest 跑 `test/` 全量 48 用例——build() 集成回填真实通过率（分母=全部用例，以真机预检日志为准）

### 与 Linux 的差异

- 无差异——纯 Python，全平台行为一致（netifaces 改为可选导入，缺失时本机地址探测返回空，真机复验）

## 依赖关系

交付包内 vendor：requests 2.32.3、urllib3 1.26.20、six（setup.py 中的 pyasn1/pyopenssl/ndg-httpsclient 经 import 扫描确认未被使用，不安装；netifaces 经 0002 补丁改为可选导入，不再 vendor）。

## 版本记录

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.0.0 | built | 2026-09-13 | 纯 Python noarch 适配 |

## 参考资料

- 上游仓库: https://github.com/JordanMilne/Advocate
- PyPI: https://pypi.org/project/advocate/1.0.0/
