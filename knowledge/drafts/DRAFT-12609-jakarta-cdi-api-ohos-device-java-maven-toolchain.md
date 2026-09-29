# jakarta-cdi-api 4.0.1：OHOS 真机 Java/Maven 构建链四坑（无 curl/无 CA/禁 shebang/JRuby gemspec）

> 草稿（DRAFT）— 来自 jakarta-cdi-api 4.0.1 HarmonyOS PC (aarch64) 真机八门禁验证的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/drafts/DRAFT-12609-jakarta-cdi-api-ohos-device-java-maven-toolchain.kv

## 问题

jakarta-cdi-api 4.0.1（Maven reactor 源码编译双 JAR）真机 `conan-verify` 连续五轮失败，
每修一坑露出下一坑，全部修完后八门禁全绿。四个坑全部跨库复用（jakarta 系列 / jackson 等
任何 Java 包在真机上都会踩）：

1. **G2 Error 127**：`curl: inaccessible or not found` —— 配方 Maven 自取只走 curl。
2. **G2 SSL 失败**：python3 直连 repo1.maven.org 报 `CERTIFICATE_VERIFY_FAILED`。
3. **G2 Error 126**：`bad interpreter: Permission denied` —— `mvn` 脚本直接执行被拒。
4. **G2 BUILD FAILURE**：spec-doc 模块 asciidoctor（JRuby）报 `concurrent-ruby-1.1.7.gemspec ENOENT`。

另有一条验证通道经验：真机验证期 ghfast.top 注入镜像读超时（ReadTimeoutError 30s×2），
设备侧临时把 conandata 源指向本机 `http.server` 镜像（sha256 不变）即可完成验证。

## 根因

### 坑 1+2：设备无 curl，且 python3 无 CA bundle

- `/system/bin` 下没有 curl；有 `/system/bin/wget`（toybox 版，TLS 能力不可靠）。
- python3（3.12）urllib 访问 `https://repo1.maven.org` 报
  `SSL: CERTIFICATE_VERIFY_FAILED (unable to get local issuer certificate)` ——
  设备没有 CA bundle，但**网络通**（TLS 握手已建立，只差证书校验）。
- Java 配方上游通常无 mvnw wrapper，Maven 3.9.11 需配方自取（repo1.maven.org）。

**解法**：`_ensure_maven` 改双通道——先 curl，捕获 `ConanException` 后回退 python3
urllib 免证书下载（`ssl._create_unverified_context()`），下载后 **sha256 钉校验**兜底完整性
（免证书通道的完整性保障就是 sha256 钉，这也是自取 Maven 本来就有的一步）。

```python
try:
    self.run('curl -fsSL -o "{}" "{}"'.format(dest, MAVEN_URL))
except ConanException:
    self.output.warning("curl unavailable/failed — python3 urllib fallback (no TLS verify; sha256 pin below)")
    py = (
        "import ssl,urllib.request,shutil;"
        "ctx=ssl._create_unverified_context();"
        "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
        "r=o.open('{}',timeout=300);f=open('{}','wb');"
        "shutil.copyfileobj(r,f);f.close();r.close()"
    ).format(MAVEN_URL, dest)
    self.run('python3 -c "{}"'.format(py))
```

注意：回退代码必须写成**单逻辑行**（分号连接）——`-c` 参数经 `/system/bin/sh` 传递时
`\n` 会被当字面反斜杠+n，多行会 SyntaxError；内层字符串用单引号、外层 sh 用双引号包裹。

### 坑 3：HMDFS 禁 shebang 直接 exec

- `~/bishengjdk17/bin/java -version` 可直接执行（ELF 二进制不受限）。
- `~/apache-maven-3.9.11/bin/mvn` 直接执行报
  `bash: .../mvn: /bin/sh: bad interpreter: Permission denied`（shell 错误 126）。
- 结论：HMDFS 对带 shebang 的脚本禁 exec()；把 maven bin 塞进 PATH 后裸调 `mvn` 必挂。

**解法**：build() 里显式 `sh {maven_home}/bin/mvn ...`（sh 是 /system/bin 的 ELF，脚本当参数传入，
不触发 shebang exec）。test_package 的 `bash test.sh` 同理本来就安全。

### 坑 4：asciidoctor/JRuby 在真机报 gemspec ENOENT

- spec-doc 是 pom-only 文档模块，用 asciidoctor-maven-plugin 2.2.1（内嵌 JRuby）生成 PDF。
- 真机报：`(ENOENT) file:/storage/Users/currentUser/.conan2/p/b/.../concurrent-ruby-1.1.7.gemspec`，
  模块耗时 4:49 后 FAILURE，拖住后面 lang-model/api 两个真正产 jar 的模块。
- 该模块**纯文档产物、不进包**。

**解法**：`settings.os == "OHOS"` 时追加 `-Dasciidoctor.skip=true`；Linux CI 仍全量构建不变。

```python
skip_doc = " -Dasciidoctor.skip=true" if self.settings.os == "OHOS" else ""
self.run(
    f'bash -c "cd {self.source_folder} && sh {maven_home}/bin/mvn clean package -B -DskipTests=false{skip_doc}"',
    env="conanbuild",
)
```

### 通道经验：ghfast.top 读超时 → 本机 http.server 镜像

- 真机验证期 harness 自动注入的 `https://ghfast.top/https://github.com/...` 读超时
  （ReadTimeoutError 30s×2，source() 下载失败，harness 事后自动恢复 conandata.yml）。
- 设备侧临时 sed 把 conandata url 指向 Windows 本机 `python3 -m http.server` 镜像
  （同一热点网段 http://192.168.43.12:8137/...，sha256 不变）→ source() 秒过。
- **提交配方必须保持官方原始 URL + sha256（R39）**；设备侧是临时通道，不进仓库。

## 验证

- `python3 scripts/ohc-run.py conan-verify jakarta-cdi-api 4.0.1` → **Verdict PASS**（exit 0）：
  G0/G1/G2/G3/G4/L2/L4/L5 全 PASS，结论「可标记 status: published」。
- 真机 conan create：reactor 四模块全 SUCCESS（cdi-parent 13.9s / spec-doc 5:13 /
  lang-model 5:24 / api 3:06）；上游 56 个 TestNG 真机构建时执行全过
  （surefire 汇总 Tests run: 51+5=56，Failures/Errors/Skipped 全 0）。
- 消费者探针 19/19 反射断言 + 2 JAR + 编译 + PASS 全过（=== All tests passed ===）。
- 报告落档 `archives/j/jakarta-cdi-api/4.0.1/reports/conan-verify-report.md`。

## 适用面

- 所有 Java/Maven 配方（jakarta 系列、jackson 等）：坑 1/2/3 必踩，配方模板应直接内置。
- 所有带 asciidoctor/JRuby 文档模块的 reactor：坑 4 同理。
- 所有 GitHub 源码包真机验证：ghfast.top 不稳定时用本机 http.server 通道。
- 与 DRAFT-12608-ee4j-aggregator-snapshot-module-build（EE4J 聚合器 SNAPSHOT 模块）互补：
  那是「构建哪些模块」，这是「真机上怎么构建」。
