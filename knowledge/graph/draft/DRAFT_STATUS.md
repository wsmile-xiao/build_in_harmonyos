# 知识图谱草稿状态报告

> 协作者提交的草稿，等待主编审核
> 最后更新: 2026-04-27

## 草稿目录: `knowledge/graph/draft/`

### ✅ 已批准并合并（2026-04-27）

| 原草稿 | 新编号 | 标题 | 合并方式 |
|--------|--------|------|---------|
| E081-draft-0D0A | **E096** | CMake C++ 标准检测失败 | 直接改编号 |
| E082-bearssl-build-system | **E097** | BearSSL 自定义构建系统 | 转写为标准 .kv |
| E085-missing-install-command | **E098** | 缺少 install 命令 | 直接改编号 |
| E095-draft-f8ae | **E099** | Boost b2 不兼容 OHOS | 直接改编号 |
| E096-draft-0D0A | **E100** | libjpeg-turbo SIMD 链接失败 | 直接改编号 |
| E103-git-safe-directory-hmdfs | **E101** | git safe.directory HMDFS | 新建 .md |
| E093-draft-f8ae | **E102** | mmsg API 缺失 | 直接改编号 + 新建 .md |
| E096-olm-cmake-version | **E103** | CMake minimum_required < 3.5 | 转写为标准 .kv |
| E097-olm-version-script | **E104** | libolm version_script 缺失 | 转写为标准 .kv |

### 🟡 待处理（与已有条目重复，需合并补充）

| 原草稿 | 重复条目 | 建议处理 |
|--------|---------|---------|
| E080-draft-f8ae | E085 (pthread_cancel) | 合并 stub 函数列表到 E085 |
| E081-draft-HGFD | E011 (umask/config.status) | 合并详细方案到 E011 |
| E082-HMDFS-mktemp-permission | E011 | 同上 |
| E099-hmdfs-autotools-tmpdir | E011 | 同上（第三个重复） |
| E083-ohos-sdk-header-conflict | E091 (sockaddr_storage) | 合并验证命令和补丁到 E091 |
| E084-musl-rpath-unsupported | E019 (runtime shared lib) | 合并 RPATH 细节到 E019 |
| E092-draft-main | E094 (CPU affinity) | 合并条件编译模式到 E094 |
| E094-draft-f8ae | E092 (CMake detection) | 合并 HAVE_* 定义模式到 E092 |
| E096-draft-f8ae (HMDFS硬链接) | E079 (hard link) | 合并到 E079 |
| E100-musl-pthread-cancel-stub | E085 | 合并完整 stub 到 E085 |
| draft-pcre-ohos-support | E007 (config.sub) | 合并基本类型列表补充到 E007 |

### 🗑️ 待删除（空模板/无内容）

| 文件 | 原因 |
|------|------|
| E093-draft-f8ae.md | 纯模板占位符 |
| E096-draft-f8ae.md | 纯模板占位符 |
| E096-draft-G1H3.md | 纯模板占位符 |

### 🆕 新增草稿（2026-06-26）

| 草稿 | 标题 | 来源 | 建议 |
|------|------|------|------|
| **E112-draft-A7F3** | HMDFS 大小写不敏感文件系统导致测试失败 | wimlib 1.14.5 编译 | 新建条目（L1 平台真理） |

### 🟡 不适合作为错误模式条目

| 原草稿 | 原因 | 建议 |
|--------|------|------|
| E098-olm-deprecated | 软件状态说明，非错误模式 | 放入 knowledge/operations/ 作为备忘 |
| E101-rocksdb-ohos-headers | L3 软件特化，不够通用 | 放入 manifest.yaml |
| E102-git-templates-missing | 打包遗漏，非编译错误 | 放入 packaging 注意事项 |

---

*主编审核时间: 2026-04-27*
*批准: 9 条 → 正式图谱 E096–E104*
*待合并: 11 条 → 补充到已有条目*
*待删除: 3 条*
