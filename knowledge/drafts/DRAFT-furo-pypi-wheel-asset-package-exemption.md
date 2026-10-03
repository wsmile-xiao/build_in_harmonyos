# DRAFT-furo-pypi-wheel-asset-package-exemption — PyPI 纯资产包取源决策:sdist 需 node 构建链时改用官方 wheel + 任务号无上游发布时的溯源基线规则

> 来源:furo 2024.8.30 适配(task furo/2024.8.30,自导入)
> 环境:build_in_harmonyos 配方仓库;PyPI(无代理直连),OH 构建环境无 node/npm

## 场景特征

```
平台任务版本 2024.8.30 → 上游 furo 无此发布(2024 线实际为 2024.8.6);
PyPI sdist 的 CSS/JS 是 src/ 下 SCSS/JS 源,主题资产需 node+webpack 构建后才存在;
官方 wheel(py3-none-any)即为上游构建完成的产物(80 资产文件 + 5 dist-info)。
```

## 触发条件

- 任务源为 PyPI 包,且 sdist 的构建需要 node/webpack/rust 等平台没有(或不应引入)的工具链
- 平台任务版本号与上游发布不对应(任务号按需求时间点编,上游版本线不同步)
- 包本质是"纯资产/纯解释型语言包"(主题、模板、静态资源、纯 py)

## 根因分析

1. **sdist ≠ 可装即用**:现代 PyPI 项目的 sdist 是"构建输入"(源 SCSS/TS + pyproject
   构建钩子),不是"构建输出";套零编译模式直接装 sdist 会装出一堆没用的源文件,
   而走 node 构建链则违背 OH 构建环境约束。官方 wheel 是同一 release 的上游构建产物,
   内容即最终资产,天然满足"零编译 + 可钉死哈希校验"。
2. **任务号 ≠ 上游 tag**:平台任务版本常按任务创建时间取整(如 2024.8.30),
   上游按实际发布日打 tag(2024.8.6)。硬凑任务号会引出"上游无此版本"的评审质疑;
   正确姿势是取任务号所在时间线的最近真实发布作基线,溯源链(source url/sha256/notes)
   完整保留——与 libzippp 6.2(上游无 6.2,基线 v6.1-1.9.2)先例同型。

## 解决方案

### 推荐方案
1. **取源**:PyPI JSON API(`https://pypi.org/pypi/<name>/<version>/json`)拿
   `bdist_wheel` 条目的 url+sha256+size(三元组全部钉进 conandata.yml);
   wheel 即 zip,`get()` sha256 校验下载 + `unzip()` 展开,不依赖 pip/node。
2. **版本溯源**:包目录/分支/conan 版本用任务号(R40:分支名=目录版本),
   manifest/notes 明确"任务号无上游对应发布,基线=X(同时间线最近真实发布)"。
3. **打包布局**:按目标生态惯例——Python 包 = `share/python/site-packages/<pkg>/`
   + `<pkg>-<ver>.dist-info/`;`package_info` 导出 `PYTHONPATH`(buildenv/runenv)
   与包专属变量;Sphinx 主题由 dist-info entry points + PYTHONPATH 直接被发现。
4. **验证**:与数据/源码包豁免模式一致——`package_id()` 清空 noarch,
   build()/test_package 双端运行钉死哈希校验器(全量文件 size+sha256)。

### 禁止做法
- ❌ 引入 node/webpack 只为"从 sdist 构建主题资产"(平台无此工具链,且构建产物不可复现钉死)
- ❌ 直接把 sdist 源树当包安装(src/ 下的 SCSS/TS 不是可用资产)
- ❌ 为了凑任务号伪造上游 tag 或改写上游版本号

## 验证

```bash
python verify_furo.py --source-root <unpacked-wheel>   # 85/85 byte-identical
conan create archives/f/furo/2024.8.30 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

实测:本地对官方 wheel 解包树自校验 85/85 byte-identical(PyPI sha256 b63e/6cd97 双重校验)。

## 关联条目

- 相关:DRAFT-agnostic-lizard-source-only-lisp-package-conan-noarch-integrity
  (数据/源码包豁免模式的 CL 库实例;本条目将其推广到 PyPI 资产包并新增
  "sdist vs wheel 取源决策"与"任务号溯源基线"两条增量)
- 相关:DRAFT-fenics-0.10.0.1-debian-native-metapackage-port(任务号/版本溯源同型)
- 冲突:无
