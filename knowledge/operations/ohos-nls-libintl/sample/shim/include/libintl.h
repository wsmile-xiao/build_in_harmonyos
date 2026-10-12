#pragma once

// 最小 libintl 兜底头（样例附带，对应知识库「处理策略③」）。
//
// 适用场景：目标平台或依赖未提供可用的 libintl.h。OHOS(musl) 的 sysroot 里
// 该头是空壳（存在但不声明 gettext 家族），照抄 GNU/glibc 隐式声明写法的库
// 会在目标平台编译失败——此时可：
//   * 策略① 依赖 gettext 包（拿到真实 libintl.h + libintl）：nls_mode=gettext
//   * 策略② 关闭 NLS（上游有开关时）
//   * 策略③ 使用本兜底头：只提供声明 + 恒等实现（无翻译目录时 gettext 的语义
//     就是返回 msgid），因此不需要链接 libintl
//
// 注意：本头是"无本地化需求"场景的兜底；需要真实 .mo 翻译目录时应走策略①。

extern "C" {

inline char *gettext(const char *msgid) { return const_cast<char *>(msgid); }

inline char *dgettext(const char *domainname, const char *msgid) {
  (void)domainname;
  return const_cast<char *>(msgid);
}

inline char *dcgettext(const char *domainname, const char *msgid, int category) {
  (void)domainname;
  (void)category;
  return const_cast<char *>(msgid);
}

inline char *ngettext(const char *msgid, const char *msgid_plural, unsigned long n) {
  return const_cast<char *>(n == 1 ? msgid : msgid_plural);
}

inline char *dngettext(const char *domainname, const char *msgid,
                       const char *msgid_plural, unsigned long n) {
  (void)domainname;
  return const_cast<char *>(n == 1 ? msgid : msgid_plural);
}

inline char *bindtextdomain(const char *domainname, const char *dirname) {
  (void)domainname;
  return const_cast<char *>(dirname);
}

inline char *textdomain(const char *domainname) {
  (void)domainname;
  return nullptr;
}

inline char *bind_textdomain_codeset(const char *domainname, const char *codeset) {
  (void)domainname;
  return const_cast<char *>(codeset);
}

} // extern "C"
