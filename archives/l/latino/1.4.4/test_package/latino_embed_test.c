/*
 * Consumer test: embed the latino library and run a .lat program through
 * the public embedding API (the same chain the interpreter's main() uses).
 *
 * Verifies the library exports and correctly executes:
 *   latC_crear_mv / latC_destruir_mv  (VM lifecycle, latino.h)
 *   latA_analizar_arch / latA_destruir (parser, latast.h)
 *   latC_analizar / latC_llamar_funcion (compiler + call, latino.h)
 */
#include <stdio.h>
#include <string.h>

#include "latast.h"
#include "latino.h"

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <script.lat>\n", argv[0]);
        return 2;
    }

    lat_mv *mv = latC_crear_mv();
    if (mv == NULL) {
        fprintf(stderr, "FAIL: latC_crear_mv returned NULL\n");
        return 1;
    }
    mv->nombre_archivo = argv[1];
    mv->global->REPL = false;

    int status = -1;
    ast *nodo = latA_analizar_arch(argv[1], &status);
    if (status != 0 || nodo == NULL) {
        fprintf(stderr, "FAIL: latA_analizar_arch(%s) status=%d\n",
                argv[1], status);
        latC_destruir_mv(mv);
        return 1;
    }

    lat_objeto *main_func = latC_analizar(mv, nodo);
    if (main_func == NULL) {
        fprintf(stderr, "FAIL: latC_analizar returned NULL\n");
        latA_destruir(nodo);
        latC_destruir_mv(mv);
        return 1;
    }

    status = latC_llamar_funcion(mv, main_func);
    latO_destruir(mv, main_func);
    latA_destruir(nodo);
    latC_destruir_mv(mv);

    if (status != 0) {
        fprintf(stderr, "FAIL: latC_llamar_funcion status=%d\n", status);
        return 1;
    }

    printf("EMBED_TEST_OK\n");
    return 0;
}
