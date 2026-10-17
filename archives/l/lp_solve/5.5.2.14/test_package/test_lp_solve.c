#include <math.h>
#include <stdio.h>
#include <string.h>

#include <lp_lib.h>

static int nearly_equal(REAL left, REAL right) {
    return fabs((double)(left - right)) < 1.0e-7;
}

int main(int argc, char** argv) {
    if (argc == 2 && strcmp(argv[1], "--fault-missing-model") == 0) {
        char filename[] = "ohpcd-intentionally-missing-model.lp";
        char model_name[] = "fault-injection";
        lprec* missing = read_LP(filename, IMPORTANT, model_name);
        if (missing != NULL) {
            delete_lp(missing);
            fprintf(stderr, "fault injection failed: missing model accepted\n");
            return 20;
        }
        puts("fault injection passed: missing model rejected");
        return 0;
    }

    lprec* model = make_lp(0, 2);
    if (model == NULL) {
        fprintf(stderr, "make_lp failed\n");
        return 1;
    }

    REAL row[3] = {0.0, 3.0, 2.0};
    if (!set_obj_fn(model, row)) {
        delete_lp(model);
        return 2;
    }
    set_maxim(model);

    row[1] = 1.0;
    row[2] = 1.0;
    if (!add_constraint(model, row, LE, 4.0)) {
        delete_lp(model);
        return 3;
    }
    row[1] = 1.0;
    row[2] = 0.0;
    if (!add_constraint(model, row, LE, 2.0)) {
        delete_lp(model);
        return 4;
    }

    set_verbose(model, IMPORTANT);
    if (solve(model) != OPTIMAL) {
        delete_lp(model);
        return 5;
    }
    if (!nearly_equal(get_objective(model), 10.0)) {
        fprintf(stderr, "unexpected objective: %.12g\n",
                (double)get_objective(model));
        delete_lp(model);
        return 6;
    }

    REAL variables[2] = {0.0, 0.0};
    if (!get_variables(model, variables) ||
        !nearly_equal(variables[0], 2.0) ||
        !nearly_equal(variables[1], 2.0)) {
        fprintf(stderr, "unexpected solution: %.12g %.12g\n",
                (double)variables[0], (double)variables[1]);
        delete_lp(model);
        return 7;
    }

    delete_lp(model);
    puts("lp_solve consumer checks passed");
    return 0;
}
