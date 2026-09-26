/* SPDX-License-Identifier: LGPL-2.1 */
/*
 * trace-btf-compat.h - OHOS (musl) compatibility shim for libtraceevent's
 * src/trace-btf.c.
 *
 * The OHOS kernel UAPI header <linux/btf.h> stops at BTF_KIND_DATASEC (15):
 * no FLOAT/DECL_TAG/TYPE_TAG/ENUM64 kinds, no struct btf_decl_tag /
 * struct btf_enum64, and NR_BTF_KINDS is the trailing enum value 16.
 * musl additionally provides no GNU qsort_r().
 *
 * Include right after <linux/btf.h>: the macros below shadow the enum
 * constants for the uses in trace-btf.c (array designators / case labels)
 * and extend the kind table to 20 entries; the qsort_r macro emulates the
 * GNU comparator+thunk sort on top of plain qsort().
 */
#ifndef TRACE_BTF_COMPAT_H
#define TRACE_BTF_COMPAT_H

#include <stdlib.h>
#include <linux/types.h>

/* linux/btf.h here already #defines NR_BTF_KINDS (BTF_KIND_MAX + 1) with a
 * value of 16 and provides none of the kind constants below; shadow it. */
#undef NR_BTF_KINDS
#define NR_BTF_KINDS       20

#define BTF_KIND_FLOAT     16
#define BTF_KIND_DECL_TAG  17
#define BTF_KIND_TYPE_TAG  18
#define BTF_KIND_ENUM64    19

struct btf_decl_tag {
	__u32 component_idx;
};

struct btf_enum64 {
	__u32 name_off;
	__u32 val_lo32;
	__u32 val_hi32;
};

/* GNU qsort_r(base, nmemb, size, compar(a, b, arg), arg) over qsort(). */
static __thread void *__btf_qsort_ctx;
static __thread int (*__btf_qsort_cmp)(const void *, const void *, void *);

static inline int __btf_qsort_wrap(const void *a, const void *b)
{
	return __btf_qsort_cmp(a, b, __btf_qsort_ctx);
}

#define qsort_r(base, nmemb, size, compar, arg)				\
	do {								\
		__btf_qsort_ctx = (arg);				\
		__btf_qsort_cmp = (compar);				\
		qsort((base), (nmemb), (size), __btf_qsort_wrap);	\
	} while (0)

#endif /* TRACE_BTF_COMPAT_H */
