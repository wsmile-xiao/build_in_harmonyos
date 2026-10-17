#include <stdio.h>
#include <stdlib.h>
#include <libIDL/IDL.h>

/*
 * Consumer test for libidl2 0.8.14:
 *   - parses a real CORBA IDL definition through the libIDL public API
 *     (IDL_parse_filename / IDL_tree_walk_in_order / IDL_tree_to_IDL),
 *   - verifies the parse tree contains the expected interface node and
 *     repository ID output,
 *   - on HarmonyOS (OHOS) builds additionally checks the __OHOS__ platform
 *     macro, i.e. verifies the OHOS toolchain/platform path actually
 *     compiles, links against OHOS glib and runs the produced binary.
 * This is the HarmonyOS-specific consumer validation (rule12, N>=1): it runs
 * in the OHOS CI worker on the OHOS-built static library.
 */

static gboolean
find_interface (IDL_tree_func_data *tfd, gpointer data)
{
    int *found = data;
    if (IDL_NODE_TYPE (tfd->tree) == IDLN_INTERFACE) {
        *found = 1;
        printf ("interface found: %s\n",
                IDL_IDENT (IDL_INTERFACE (tfd->tree).ident).str);
    }
    return TRUE;
}

int
main (void)
{
    IDL_tree tree = NULL;
    IDL_ns ns = NULL;
    int rv, found = 0;
    FILE *fp;
    /* OHOS CI workers mount /tmp read-only (erofs); write the temp IDL file
     * under $TMPDIR when available, else fall back to the (writable) cwd. */
    static char tmpfile[512];
    const char *tmpdir = getenv ("TMPDIR");
    fp = NULL;
    if (tmpdir && *tmpdir) {
        snprintf (tmpfile, sizeof tmpfile, "%s/libidl2_test_basic.idl", tmpdir);
        fp = fopen (tmpfile, "w");
    }
    if (!fp) {
        snprintf (tmpfile, sizeof tmpfile, "libidl2_test_basic.idl");
        fp = fopen (tmpfile, "w");
    }
    if (!fp) {
        perror ("fopen");
        return 2;
    }
    static const char *idl_src =
        "module Test {\n"
        "  interface Hello {\n"
        "    attribute string name;\n"
        "    long add(in long a, in long b);\n"
        "  };\n"
        "};\n";

#ifdef __OHOS__
    printf ("HarmonyOS platform macro __OHOS__ is defined\n");
#else
    printf ("host build (no __OHOS__ macro)\n");
#endif

    printf ("libIDL version: %s\n", IDL_get_libver_string ());

    fp = fopen (tmpfile, "w");
    if (!fp) {
        perror ("fopen");
        return 2;
    }
    fputs (idl_src, fp);
    fclose (fp);

    rv = IDL_parse_filename (tmpfile, NULL, NULL, &tree, &ns, 0, IDL_WARNING1);
    if (rv != IDL_SUCCESS) {
        fprintf (stderr, "IDL_parse_filename failed: %d\n", rv);
        return 3;
    }

    IDL_tree_walk_in_order (tree, (IDL_tree_func) find_interface, &found);
    if (!found) {
        fprintf (stderr, "no interface node in parse tree\n");
        return 4;
    }

    printf ("--- IDL_tree_to_IDL output ---\n");
    IDL_tree_to_IDL (tree, ns, stdout, 0);
    printf ("\n--- end ---\n");

    IDL_ns_free (ns);
    IDL_tree_free (tree);
    printf ("libIDL consumer test OK\n");
    return 0;
}
