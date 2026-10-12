#pragma once

// ✅ 修复态示例（策略①，demo.sh 阶段②使用）：在封装头里显式包含 libintl.h。
// 与缺陷态的差别只有下面这一行 include —— 这正是 OHOS 适配所需的最小改动。
#include <string>

#include <libintl.h>

namespace i18n_demo {

std::string tr(const char *domain, const char *msgid);

std::string tr_plural(const char *domain, const char *msgid,
                      const char *msgid_plural, unsigned long n);

} // namespace i18n_demo
