#pragma once
#include <QtCore/qobjectdefs.h>
#include <tuple>
namespace QtPrivate {
template<typename T> struct FunctionPointer;
template<typename R, typename C, typename... Args>
struct FunctionPointer<R (C::*)(Args...)> { enum { ArgumentCount = sizeof...(Args) }; };
template<typename R, typename C, typename... Args>
struct FunctionPointer<R (C::*)(Args...) const> { enum { ArgumentCount = sizeof...(Args) }; };
#if __cplusplus >= 201703L
template<typename R, typename C, typename... Args>
struct FunctionPointer<R (C::*)(Args...) const noexcept> { enum { ArgumentCount = sizeof...(Args) }; };
template<typename R, typename C, typename... Args>
struct FunctionPointer<R (C::*)(Args...) noexcept> { enum { ArgumentCount = sizeof...(Args) }; };
#endif
}
class QMetaObject { public: static void activate(void*, const QMetaObject*, int, void**) {} };
template<typename T> class QFlags { public: using enum_type = T; };
