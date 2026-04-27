# 知识图谱草稿状态报告

> 协作者提交的草稿，等待主编审核

## 草稿目录: `knowledge/graph/draft/`

### 本次新增草稿（与机器C编译相关）

| 草稿ID | 标题 | 状态 | 说明 |
|--------|------|------|------|
| E080 | musl pthread_cancel缺失 | 待审核 | HarmonyOS使用musl libc，不支持POSIX线程取消 |
| E081 | CMake C++标准检测失败 | 待审核 | 需显式设置CMAKE_CXX_STANDARD |
| E096 | libjpeg-turbo SIMD链接失败 | 待审核 | 禁用SIMD扩展(WITH_SIMD=0) |

### 历史草稿（之前提交）

| 草稿ID | 标题 | 状态 | 说明 |
|--------|------|------|------|
| E082 | BearSSL自定义构建系统 | 待审核 | 无标准configure/make install流程 |
| E092 | OHOS缺少CPU亲和性API | 待审核 | sched_setaffinity等API缺失 |
| E093 | mmsg API缺失 | 待审核 | struct mmsghdr, recvmmsg, sendmmsg |
| E094 | CMake平台检测失败 | 待审核 | check_c_source_compiles等检测失败 |
| E095 | Boost b2构建系统不兼容 | 待审核 | 无法识别OHOS平台 |
| E096-olm-cmake-version | CMake版本问题 | 待审核 | cmake_minimum_required < 3.5 |
| E097 | libolm version script缺失 | 待审核 | Makefile缺少version_script.ver |
| E098 | libolm项目弃用 | 待审核 | 2024-07-31官方弃用 |
| draft-pcre-ohos-support | pcre OHOS支持 | 待审核 | config.sub缺少ohos支持 |

---

## 主编审核流程

1. 检查草稿格式是否符合模板规范
2. 验证错误特征和解决方案的正确性
3. 批准后执行：
   ```bash
   mv knowledge/graph/draft/E0XX-*.kv knowledge/graph/E0XX.kv
   # 重建索引
   ./scripts/ohc-run.py summary --refresh-index
   ```

---

*生成时间: 2026-04-27*
*草稿总数: 13*
*本次新增: 3*