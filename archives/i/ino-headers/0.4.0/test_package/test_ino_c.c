/* Consumer probe — C translation unit exercising the same public header.
   ino/lib.h is a C API and must compile under C (here C11; header needs C99). */
#include <ino/lib.h>

#include <stddef.h>

/* Type spot-checks: compile-time only, no linker references emitted. */
_Static_assert(__builtin_types_compatible_p(ino_context, void *), "ino_context is void*");
_Static_assert(__builtin_types_compatible_p(ino_variant, void *), "ino_variant is void*");
_Static_assert(__builtin_types_compatible_p(ino_method_cb,
                   ino_variant (*)(ino_context, const ino_variant *, size_t)),
               "ino_method_cb signature");

/* Declaration delimiters must be usable in C. */
INO_BEGIN_C_DECLS
typedef int probe_c_decls_ok;
INO_END_C_DECLS

int main(void)
{
    /* Runtime spot-check of the public enum numbering. */
    if (INO_VARIANT_TYPE_UNDEFINED != 0) return 1;
    if (INO_VARIANT_TYPE_NULL != 1) return 1;
    if (INO_VARIANT_TYPE_BOOLEAN != 2) return 1;
    if (INO_VARIANT_TYPE_STRING != 3) return 1;
    if (INO_VARIANT_TYPE_NUMBER != 4) return 1;
    if (INO_VARIANT_TYPE_OBJECT != 5) return 1;

    return 0;
}
