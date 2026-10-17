/* compat/cblas_mangling.h — minimal stub
 * LAPACK 的 cblas_mangling.h 定义 Fortran 符号重命名宏（F77_*）。
 * 鸿蒙 clang 直接链接制品仓 liblapack.a/libblas.a（无 Fortran 重命名），
 * 因此全部定义为空——cblas.h 的 F77_* 展开为空前缀。
 */
#ifndef CBLAS_MANGLING_H
#define CBLAS_MANGLING_H
#define F77_FUNC(name,NAME) name
#define F77_FUNC_(name,NAME) name##_
#define F77_ROCALLC 1
#define CBLAS_MAJOR 2
#endif
