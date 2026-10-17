# ccfits 2.7 Build Notes

## 软件信息

- **CCfits 2.7** — NASA HEASARC 官方 cfitsio C++ 面向对象接口
- 上游版本判定:`configure.ac` AC_INIT 为 2.7,`CHANGES` 顶部条目为 "Changes for CCfits 2.7"
- 源码:NASA HEASARC 官方发布目录 `.../ccfits/v2.7/CCfits-2.7.tar.gz`
  SHA-256 `f63546d2feecbf732cc08aaaa80a2eb5334ada37fb2530181b7363a5dbdeb01a`
  (设备下载实测,并与 fink ccfits 2.7 info 文件中的 Source-Checksum 交叉核对一致;
  HEASARC 旧版无版本子目录的 URL 已 404,GitHub 上无 HEASARC/CCfits 官方镜像仓库)

## 构建方法

- 上游同时提供 autotools 与 CMake;选择 **CMake**(同 cfitsio 4.6.4 的决策:
  规避本设备 HMDFS 上 autotools config.status 的已知限制)
- CMake 构建依赖解析走上游唯一的入口:`PKG_CHECK_MODULES(CFITSIO REQUIRED cfitsio)`
- 包构建选项:`BUILD_SHARED_LIBS=OFF`(默认静态)、`TESTS=OFF`、
  `CMAKE_POSITION_INDEPENDENT_CODE=ON`
- 依赖:`cfitsio/4.6.4`(仓库内已发布,OHOS binary 已用
  `conan install --build=never` 真实验证),传递依赖 zlib/1.3.1.1

## 已知问题与处理(逐项有据)

1. **cfitsio 包自带 `cfitsio.pc` 的 prefix 失效**
   - 现象:cfitsio 包内 `lib/pkgconfig/cfitsio.pc` 把 `prefix=` 写死为打包时的绝对路径
     (`.../p/b/cfitse9412fda95f6e/p`),该路径在本机 Conan 缓存中不存在
     (当前实际包目录哈希不同),pkg-config 解析出的 `-I` 指向空路径,
     首条真实编译错误为 `fatal error: 'fitsio.h' file not found`。
     注意迷惑点:pkg-config 报告 Found cfitsio(configure 通过),
     "找到"不等于"路径正确"。
   - 处理:配方 `generate()` 中用 `PkgConfigDeps` 重新生成依赖 `.pc`
     (路径指向本机真实包目录),并用 `Environment` 将 generators 目录前置注入
     build 作用域的 `PKG_CONFIG_PATH`(Conan 2.29 不会自动注入,已实测确认)。
   - 知识沉淀:路径 B 草稿
     `knowledge/drafts/DRAFT-ccfits-2.7-stale-pc-prefix-regen.md/.kv`,
     与既有 `knowledge/doc/E468.md`(PkgConfigDeps 不扩展 PKG_CONFIG_PATH)
     互补:E468 覆盖路径注入,本条补充"为何必须重新生成而非沿用依赖自带 pc"。
2. **上游 CMakeLists.txt 版本串写 2.6**
   - `CMakeLists.txt` 内 `MINOR_VERSION 6`,与 `configure.ac`/`CHANGES` 的 2.7 不一致,
     属上游疏忽;产物 `libCCfits.so` 无版本化文件名、无 SONAME(readelf 实测),
     该不一致不影响包产物,故不打补丁,仅在此记录。
3. **`FITS(fname, Write)` 创建的空 PHDU 不能直接写像素**
   - 消费者测试摸索期实测:新文件默认 PHDU NAXIS=0,直接 `pHDU().write()` 抛
     cfitsio 错误(`column number < 1 or > tfields`)。上游 cookbook 的正确模式是
     `FITS(fileName, bitpix, naxis, naxes)` 创建时定义图像几何;测试已按此模式编写。
4. **autotools 路径未使用**:HMDFS 上 config.status 失败为 cfitsio 任务已实测的
   设备限制,本任务直接走 CMake,未重复踩坑。

## 测试

- **上游测试**(统计口径:CTest 用例数,`ADD_TEST(cookbook cookbook)` 共 1 项):
  原生构建 `-DTESTS=ON` 编译 cookbook,在含 `file1.pha` 的构建目录运行,
  退出码 0,写出 atestfil.fit/btestfil.fit/ctestfil.fit,读写回显完整。
- **test_package**(消费者,7 项断言):test_ccfits.cpp 全部 PASS,退出码 0。
  覆盖:图像几何创建(FLOAT_IMG 5x5)、3 个关键字卡(string/double/string)回读、
  25 像素写入回读、轴数断言、二进制表字符串列整列写入回读。
- 统计口径分栏,取数命令见 `test_package/MANIFEST.yml`。

## 产物

- `lib/libCCfits.a`(默认静态;shared 选项时为 `lib/libCCfits.so`,无 SONAME)
- `include/CCfits/`(全部公共头 + 无扩展名总头 `CCfits`)
- `licenses/License.txt`(NASA 公有领域式许可)
