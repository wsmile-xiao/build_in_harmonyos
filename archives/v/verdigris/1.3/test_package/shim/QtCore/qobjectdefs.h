#pragma once
// Minimal Qt shim for verdigris header-only fallback without full Qt
#define QT_VERSION 0x050F02
#define QT_VERSION_CHECK(major, minor, patch) ((major<<16)|(minor<<8)|(patch))
#define Q_OBJECT
#define Q_GADGET
#define Q_NAMESPACE
#define Q_ENUM(x)
#define Q_ENUM_NS(x)
#define Q_FLAG(x)
#define Q_FLAG_NS(x)
#define Q_DECLARE_FLAGS(F,E)
#define Q_CLASSINFO(a,b)
#define Q_INTERFACE(a)
#define QT_ANNOTATE_CLASS(...)
#define Q_UNUSED(x) (void)(x)
#define Q_DECL_UNUSED
using qptrdiff = long;
using uint = unsigned int;
using uchar = unsigned char;
using ushort = unsigned short;
using ulong = unsigned long;
