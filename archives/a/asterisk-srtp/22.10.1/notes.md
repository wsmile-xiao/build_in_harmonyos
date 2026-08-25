
## conan-verify 通过记录（2026-08-21，第18次迭代）
- G0-G4 + L2/L4/L5 全部 PASS，status: published
- 关键修复链（同系列复用）：
  1. $TMPDIR 工作目录构建（规避 .conan2 缓存目录 HMDFS MAC 限制）
  2. menuselect/configure 与主 configure 同步打 umask 022 补丁（最终根因）
  3. menuselect 子项目预配置（CC=clang + PKG_CONFIG_PATH=libxml2）
  4. 注入探索验证的完整版 menuselect.makeopts/makedeps（时序：预配置之后；未来时间戳防覆盖）
  5. make -C res SUBDIR=res ASTTOPDIR=$work SOLINK=... 只构建 res 子目录（绕开 main/utils）
