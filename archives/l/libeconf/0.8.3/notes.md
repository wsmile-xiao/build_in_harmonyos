# libeconf 0.8.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# cmake 配置（带 install RPATH 和 soname）
cd build && cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE \
  -DCMAKE_INSTALL_RPATH=/storage/Users/currentUser/usr/local/lib \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libeconf.so.0"

# 编译与安装（DESTDIR 模式，R20）
make -j2
make install DESTDIR=$TEST_PREFIX

# 版本符号链接（cmake SOVERSION 在 HarmonyOS 上不自动生成，需手动创建）
cd $TEST_PREFIX/$DEFAULT_PREFIX/lib/
mv libeconf.so libeconf.so.0.8.3
ln -s libeconf.so.0.8.3 libeconf.so.0
ln -s libeconf.so.0 libeconf.so

# 打包（R19: 必须用 ohc-run.py package）
python3 $SKILL_ROOT/scripts/ohc-run.py package libeconf 0.8.3
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | econftool.c 硬编码 /tmp | HMDFS 上 /tmp 为只读 erofs (E002) | 改用 getenv("TMPDIR") 回退 /data/local/tmp |
| 2 | cmake SOVERSION 不生成符号链接 | HarmonyOS 平台 cmake 不识别 SOVERSION | 手动创建 libeconf.so.0.8.3/0/ 符号链接 |
| 3 | econftool NEEDED 为 ../lib/libeconf.so（相对路径） | cmake build-tree RPATH 被嵌入 NEEDED | 设置 CMAKE_BUILD_WITH_INSTALL_RPATH=TRUE + soname |

## 源码修改

- 补丁: `0001-util-econftool.c.patch`
  - 替换 `/tmp/econftool-XXXXXX` → 动态分配 `getenv("TMPDIR")/econftool-XXXXXX`
  - 替换 `/tmp` → `/data/local/tmp`（TMPDIR 未设置时的回退）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion libeconf → 0.8.3 ✅

# econftool 功能验证
LD_LIBRARY_PATH=~/usr/local/lib econftool --help ✅
```

## 功能测试结果（2026-06-03 补充）

### econftool 命令行测试
- `econftool show` ✅ 正确解析分组/键值
- `econftool syntax` ✅ 合法文件返回 OK，非法文件检测错误
- `econftool edit` ✅ 临时文件创建在 TMPDIR（补丁生效）
- `econftool --help` ✅ 正常显示帮助

### libeconf C API 测试（17项全部通过）
- 读取/写入/合并配置文件 ✅
- String/Int/Bool/Double/Int64 类型转换 ✅
- 分组/键列表获取 ✅
- econf_newKeyFile + econf_setValue ✅
- econf_writeFile + 回读验证 ✅

### 打包问题（✅ 已修复）
- 打包脚本 Step 6 (Strip) 最初未生效：文件含 .symtab 段，体积偏大
- 修复方案：先签名 → 后 strip-all + keep .codesign → add gnu_debuglink
- 修复结果：econftool 87936→30488 bytes，libeconf.so 87936→50912 bytes（主包 404K，节省 28%）
- debug 符号分离保存到 libeconf-0.8.3-ohos-aarch64-debug.tar.gz（118K）
- 符号链接被 cp 替换为真实文件：符合鸿蒙 SELinux 规范（§5 软链接替代方案）

---

**编译结束**: 2026-06-03 12:17
**最终状态**: built
---

**测试补完**: 2026-06-03
**最终状态**: published（功能全部可用，打包 strip 已修复）
