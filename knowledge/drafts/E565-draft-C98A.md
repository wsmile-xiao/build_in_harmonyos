# E565 — intltool XML::Parser perl 模块在 OHOS 沙箱不可加载

## 错误特征
```
checking for XML::Parser... configure: error: XML::Parser perl module
is required for intltool
```
或 perl 运行时：
```
Can't load '.../auto/XML/Parser/Expat/Expat.so' for module
XML::Parser::Expat: Error loading shared library ...: Permission denied
```

## 触发条件
- 构建系统: autotools（IT_PROG_INTLTOOL）
- 阶段: configure（检测）/ make（intltool-merge -x 执行）
- 典型软件: klavaro 3.14、goffice 0.10.57.1（同款问题两种解法）

## 根因分析
intltool 的 XML 合并模式（`intltool-merge -x`）依赖 perl 的
XML::Parser XS 扩展。OHOS 应用沙箱内 musl loader 对用户目录下的
.so dlopen 报 Permission denied——实测确认：
- XS 扩展无论放 HMDFS 还是 tmpfs 均被拒
- 静态链接 libexpat 后仍被拒（排除依赖问题）
- perl 的报错把真实 dlerror 藏起来，"Permission denied" 是红鲱鱼
- `intltool-merge -d`（desktop）模式是纯正则实现，不受影响

## 解决方案

### 推荐方案（klavaro 3.14 三件套）
1. **补丁绕过 configure 检测**（IT_PROG_INTLTOOL 无 --disable 开关）：
   把 `if \`$INTLTOOL_PERL -e "require XML::Parser"\`` 改为 `if true`
2. **配方生成 intltool-merge shim**：拦截 `-x` 调用，用纯 perl 正则
   去翻译标记：
   ```sh
   perl -e 'my($in,$out)=($ARGV[$#ARGV-1],$ARGV[$#ARGV]);
   ...;while(<I>){s|<(\/?)_([A-Za-z]\w*)>|<$1$2>|g;print O}' -- "$@"
   ```
   ⚠️ 必须加 `--` 分隔符，否则 perl 把 `-x` 当作自己的切割参数
3. **configure 后重写 Makefile 的 INTLTOOL_MERGE 变量**：configure
   把绝对路径烤进 Makefile，PATH shim 不生效

### 替代方案（goffice 0.10.57.1）
直接打补丁禁用 intltool/NLS + po 子目录（对不需要翻译的软件更简单）。

## 关联
- goffice 0.10.57.1 notes.md 问题 #2（先例）
- klavaro 3.14 patches/0001 + conanfile.py `_write_intltool_merge_shim`
