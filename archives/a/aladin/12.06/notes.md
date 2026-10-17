# aladin 12.06 适配笔记

## 编译环境
- 构建系统: custom (ant build.xml → javac + jar 手动复刻)
- 编译日期: 2026-08-19
- 编译器: BiSheng JDK 17.0.13 (javac/jar，无 C/C++ 编译)
- 状态: published

## 编译步骤

1. 安装 JDK：`curl install-jdk.sh | sh -s -- 17.0.13`（bishengjdk 17.0.13 → JAVA_HOME）
2. 获取官方源码（GitHub cds-astro/aladin，固定 commit 25e03b87，VERSION=v12.060）
3. 上游构建（参考验证）：`ant` → 编译 src/ 下全部 Java 源文件并打包 Aladin.jar
   （build.xml compil+main：javac -encoding Cp1252 -source 1.8 -target 1.8，
   jar 内嵌 lib/ 下 adql/jsamp/kxml2/cdshealpix/Moc 依赖与资源文件，
   Main-Class: cds.aladin.Aladin）
4. Conan 配方 build() 用 javac + jar 直接复刻 build.xml 逻辑，无需 ant：
   - javac 编译全部 src/**/*.java 到 bin/
   - Python zipfile 合并 lib/*.jar 到 merge/（环境无 unzip 命令）
   - 复制资源文件（*.gif/*.jpg/*.png/Ala*.*/Constellation.txt 等）
   - `jar cfe Aladin.jar cds.aladin.Aladin -C bin . -C merge .`
5. package() 打包 Aladin.jar 到 lib/ + 生成 bin/aladin 启动脚本（自动定位 JAVA_HOME）
6. 运行上游测试类：`java -cp Aladin.jar cds.astro.Test` 与 `cds.astro.TestRegion` 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 失败：FileNotFoundError 'unzip' | 鸿蒙环境无 unzip 命令 | conanfile.py 用 Python zipfile.extractall 替代 unzip |
| 2 | test_package 检查 manifest 失败 | test.sh 用 unzip 读取 jar manifest，环境无 unzip | 改用 JDK jar xf 提取 META-INF/MANIFEST.MF 再 grep |
| 3 | CI L0p 门禁失败：settings 缺少 compiler/build_type | JVM 应用仅声明 os/arch | settings 声明全部四项 "os","compiler","build_type","arch" |
| 4 | TestGaia 无法运行 | 需要 data/sample1000-gaia_source-final.csv（Gaia 数据样本），上游仓库未附带 | 记录为跳过，补等价功能测试（Test/TestRegion 已在 jar 中运行） |
| 5 | init-build 归档写入 skill 目录 | find_project_dir 默认解析到 skill 根 | 设置 OHC_PROJECT_DIR 指向项目目录重新 init-build |

## 依赖版本

- bishengjdk 17.0.13（cmd-pkgs 预编译包）
- 无 conan 依赖（Java 依赖库捆绑在源码 lib/）

## 验证结果

```bash
java -cp Aladin.jar cds.astro.Test        # ✅ exit 0（坐标/历元/自行断言）
java -cp Aladin.jar cds.astro.TestRegion  # ✅ exit 0（region centroid 123.0+34.0）
conan create ... --user=ohpcd --channel=stable  # ✅ G1-G4 全部通过
```

## 注意事项

- aladin 是 Java GUI 应用，运行需要 JVM（bishengjdk 17+）
- 源码 URL 固定到 commit 25e03b87（master HEAD = v12.060），保证 sha256 可复现
- 上游无 release tag/压缩包，官方分发为 Aladin.jar + AladinSrc.jar，GitHub 仓库为官方源码
---

**编译结束**: 2026-08-19 12:43
**最终状态**: published
