# jpeg 10 编译进度

**日期**: 2026-04-22
**状态**: ✅ 完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 下载、解压、骨架创建完成 |
| Step 2 patches | ✅ | E007 补丁（config.guess + config.sub） |
| Step 3 configure | ✅ | 需修复 config.status 临时目录问题 |
| Step 4 make | ✅ | make -j20 成功 |
| Step 5 install | ✅ | DESTDIR 模式安装成功 |
| Step 6 safety | ✅ | 安全弹窗扫描完成（rdjpgcom/wrjpgcom 正常） |
| Step 7 check | ✅ | 所有测试通过 |
| Step 8 staging | ✅ | Staging 验证完成 |
| Step 9 package | ✅ | 预编译包制作完成 |
| Step 10 deploy | ✅ | 本地部署验证完成 |
| Step 11 finish | ✅ | 收尾完成 |

## 发现与知识

### E007: config.guess 无法识别 HarmonyOS

**问题**: GNU config.guess 不包含 HarmonyOS/__OHOS__ 检测分支

**解决方案**: 使用内置脚本 `patch-autotools-ohos.pl` 打补丁
```bash
perl ${SKILL_ROOT}/scripts/patch-autotools-ohos.pl config.guess config.sub
```

**输出**: aarch64-unknown-linux-ohos

### HMDFS 临时目录权限问题

**问题**: config.status 在当前目录创建临时文件失败
```
config.status[989]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

**解决方案**: 修改 config.status，强制使用 `$TMPDIR` 作为临时目录
```bash
# 在 config.status 开头添加
tmp=/storage/Users/currentUser/tmp/jpeg-config-tmp
ac_tmp=$tmp
# 清空第779行的 tmp= ac_tmp= 部分
```

## 编译产物

- **二进制**: cjpeg, djpeg, jpegtran, rdjpgcom, wrjpgcom
- **库**: libjpeg.so.10.0.0, libjpeg.a
- **头文件**: jconfig.h, jerror.h, jmorecfg.h, jpeglib.h

## 测试结果

```
./djpeg -dct int -ppm -outfile testout.ppm ./testorig.jpg  ✅
./djpeg -dct int -gif -outfile testout.gif ./testorig.jpg  ✅
./djpeg -dct int -bmp -colors 256 -outfile testout.bmp ./testorig.jpg  ✅
./cjpeg -dct int -outfile testout.jpg ./testimg.ppm  ✅
./djpeg -dct int -ppm -outfile testoutp.ppm ./testprog.jpg  ✅
./cjpeg -dct int -progressive -opt -outfile testoutp.jpg ./testimg.ppm  ✅
./jpegtran -outfile testoutt.jpg ./testprog.jpg  ✅
cmp ./testimg.ppm testout.ppm  ✅
cmp ./testimg.gif testout.gif  ✅
cmp ./testimg.bmp testout.bmp  ✅
cmp ./testimg.jpg testout.jpg  ✅
cmp ./testimg.ppm testoutp.ppm  ✅
cmp ./testimgp.jpg testoutp.jpg  ✅
cmp ./testorig.jpg testoutt.jpg  ✅
```

所有测试通过，无错误。
---

**编译结束**: 2026-04-22 18:40
**最终状态**: partial

---

**编译结束**: 2026-04-22 18:41
**最终状态**: success
