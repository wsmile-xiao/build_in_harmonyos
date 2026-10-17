# DRAFT-conan-get-url-filename — Conan get() 对带查询串的源 URL 硬失败：conandata.yml 应显式声明 filename

> 状态：草稿（待审核 promote，最终 Exxx 编号由知识库主编确认）
> 配对条目：`knowledge/drafts/DRAFT-conan-get-url-filename.kv`
> 案例：kicad-library-utils `0.0-git20260711.a8c0d0e`（仅为括号内案例，条目本身为问题类泛化）
> 关联：`knowledge/graph/draft/E215-draft-7A01.kv`（同族另一分支）、E183（HMDFS heredoc，仅 verification_cmd 写法关联）

## 1. 背景：GitLab 无 tag 滚动仓 pin commit 的归档获取方式

KiCad 官方库工具集（kicad-library-utils）等 GitLab 托管上游没有发布 tag，适配时
以"冻结 commit + 服务端归档"固定源码身份。归档有两条 URL 形态：

| URL 形态 | 可用性 |
|---|---|
| API 端点 `https://gitlab.com/api/v4/projects/<url-encoded-path>/repository/archive.tar.gz?sha=<full-sha>` | 无凭据 HTTPS 稳定可达，服务端按 commit 确定性生成（同 commit 两次下载 sha256 一致） |
| web 端点 `https://gitlab.com/<group>/<proj>/-/archive/<ref>/<name>-<ref>.tar.gz` | 被 Cloudflare 拦截命令行下载（403），curl/conan 均不可用 |

结论：**conandata.yml 的源 URL 只能是 API 端点**，而该形态 URL 必含 `?sha=` 查询串——
这正是本条失败机理的触发前提。S3/OSS 预签名 URL 分发源码的上游同 hit（预签名 URL
必带查询参数）。

## 2. 失败现场

`conan create` 在 source() 阶段立即失败（未进入下载）：

```
ERROR: kicad-library-utils/0.0-git20260711.a8c0d0e: Error in source() method, line 52
	get(self, **self.conan_data["sources"],
	ConanException: Cannot deduce file name from the url:
	'https://gitlab.com/api/v4/projects/kicad%2Flibraries%2Fkicad-library-utils/repository/archive.tar.gz?sha=a8c0d0e...'. Use 'filename' parameter.
```

CI 语义：L1 门禁 fail（conan create failed），阻塞面 = 构建期源获取，severity 3。

## 3. 机理：get() 的文件名推断与两个失败分支

Conan 2.x `conan/tools/files/files.py` 的 `get()` 在未显式传 `filename` 时从 URL
推断缓存文件名，且推断前有前置检查：URL 含 `?` 或 `=` 即直接 raise
`ConanException(... Use 'filename' parameter)`（files.py L123-127，Conan 2.29.1
实测）。即"带查询串的 URL"不是"推断失败再兜底"，而是**前置硬失败**。

同族区分（为什么与 E215-draft-7A01 不是重复条目）：

| | 本条 | E215-draft-7A01 |
|---|---|---|
| URL 形态 | 带 `?sha=` 查询串 | codeload URL，basename 无扩展名 |
| 失败方式 | `ConanException` 硬失败（前置检查） | BadZipFile 静默错型（内容嗅探失败） |
| 修复落点 | conandata.yml `filename` 字段 | conanfile.py 内显式 filename/解包处理 |

## 4. 修复：方案空间

- **rec（主方案）`conandata-filename-field`**：conandata.yml 的 `sources:` 下与
  url/sha256 平级声明 `filename: "<name>-<sha>.tar.gz"`。`get(self,
  **self.conan_data["sources"])` 展开后 filename 作为关键字参数进入 get()，跳过
  URL 推断分支。优点：recipe 代码零改动、文件名与 url/sha 同处一个元数据文件、
  换 commit 只改 sha 不动代码。保留 `strip_root=True` 应对
  `<name>-<sha>-<sha>/` 归档根目录。
- **fallback `get-filename-arg`**：conanfile.py 里 `get(..., filename="...")`
  硬编码。立即可用，但把下载文件名冻结进配方代码、与 conandata 的 url/sha 分离，
  换源/升级时易漏改，仅作退路。
- **forbid `url-bypass`**：禁止为绕开推断检查改写 URL（去掉查询串、改用 web 端
  `/-/archive/`、自建镜像去参数）。理由：web 端点被 Cloudflare 拦截（403）；去
  query 后 URL 与 pin commit 的绑定关系丢失、sha256 无法跨 commit 复核。后果：
  源获取不稳定或 provenance 失效（R39/R34 类门禁风险）。

## 5. 验证：三步自包含探针

任何人开新 shell 可复跑（探针文件用 printf 写，禁 heredoc——HMDFS 下 heredoc
受限，见 E183；不依赖任何 run 日志路径）：

```sh
# (1) 工具实现证据：定位 conan 的 files.py 并确认前置检查存在
CMOD=$(python3 -c "import conan.tools.files.files as m; print(m.__file__)") && grep -n "Cannot deduce file name" "$CMOD"

# (2) 定向复现：临时目录 printf 写探针 recipe（source() 用带 ?sha= 的 API 归档 URL）
cd "$(mktemp -d)" && mkdir klu-get-probe && cd klu-get-probe && printf '%s\n' \
  'from conan import ConanFile' 'from conan.tools.files import get' \
  'class Probe(ConanFile):' '    name = "klu-get-probe"' '    version = "1.0"' \
  '    settings = "os", "compiler", "build_type", "arch"' \
  '    def source(self):' \
  '        get(self, "https://gitlab.com/api/v4/projects/kicad%2Flibraries%2Fkicad-library-utils/repository/archive.tar.gz?sha=<full-sha>", strip_root=True)' \
  > conanfile.py && conan create . --build=missing
# 期望(2)：ConanException: Cannot deduce file name from the url ... Use 'filename' parameter.

# (3) 修复验证：get(...) 追加 filename="klu-probe.tar.gz" 后重跑 → 下载解压成功
```

实测记录：案例库 attempt3 失败（(2) 的签名）、补 conandata `filename` 字段后
attempt4 全门禁 PASS，上游测试 133+53+1 用例真实执行通过。

## 6. 适用面泛化

命中条件（两条同时满足）：source URL 带 query string（GitLab/GitHub API 归档端点、
S3/OSS 预签名 URL 等）＋ source() 以 `get(self, **conan_data['sources'])` 展开。
伴生事实：GitLab API 归档根目录名为 `<name>-<sha>-<sha>/`，需 `strip_root=True`；
归档为服务端按 commit 确定性生成，可安全固定 sha256。凡"无 tag 滚动仓 + pin
commit"适配（本案例 kicad-library-utils 及一切 `gitlab.com/<group>/<proj>` 归档源）
都会以完全相同的方式命中。
