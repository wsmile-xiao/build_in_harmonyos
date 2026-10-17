/*
 * Consumer smoke test for gapp (HarmonyOS PC adaptation).
 *
 * These are consumer-side checks executed by the Conan test_package: they link
 * against the packaged library exactly like a downstream project would, so they
 * also prove that the installed header tree (including the C++20 polyfills in
 * src/utility/cpp20_compat.hpp) is self-contained. They are counted in the
 * "HarmonyOS-specific tests" row of the PR test tables and are NOT part of the
 * upstream test-suite denominator.
 */

#include <gapp/gapp.hpp>

#include <cmath>
#include <cstddef>
#include <iostream>

using namespace gapp;

namespace {

int checks_total = 0;
int checks_passed = 0;

void check(bool condition, const char* what)
{
    ++checks_total;
    if (condition)
    {
        ++checks_passed;
    }
    else
    {
        std::cerr << "FAILED: " << what << '\n';
    }
}

class SinX : public FitnessFunction<RealGene, 1>
{
    FitnessVector invoke(const Candidate<RealGene>& sol) const override { return { std::sin(sol[0]) }; }
};

class Kursawe2 : public FitnessFunction<RealGene, 2>
{
    FitnessVector invoke(const Candidate<RealGene>& sol) const override
    {
        const double f1 = 10.0 * std::exp(-0.2 * std::sqrt(std::pow(sol[0], 2) + std::pow(sol[1], 2)));
        const double f21 = std::pow(std::abs(sol[0]), 0.8) + 5.0 * std::sin(std::pow(sol[0], 3));
        const double f22 = std::pow(std::abs(sol[1]), 0.8) + 5.0 * std::sin(std::pow(sol[1], 3));

        return { -f1, -f21 - f22 };
    }
};

Population<RealGene> run_single_objective(const SinX& fitness_function)
{
    RCGA ga{ 100 };
    ga.algorithm(algorithm::SingleObjective{ selection::Tournament{}, replacement::KeepBest{} });
    ga.crossover_method(crossover::real::Wright{ 0.8_p });
    ga.mutation_method(mutation::real::Gauss{ 0.1_p });
    ga.stop_condition(stopping::FitnessBestStall{ 5 });
    return ga.solve(fitness_function, Bounds{ 0.0, 3.14 });
}

} // namespace

int main()
{
    // 1 — packaged consumer link / execution
    check(execution_threads() >= 1, "default execution_threads >= 1");
    execution_threads(2);
    check(execution_threads() == 2, "execution_threads setter/getter round-trip");

    // 2 — fitness function objects through the installed headers
    const SinX sinx;
    const FitnessVector probe_fitness = sinx(Candidate<RealGene>{});
    check(probe_fitness.size() == 1, "single-objective fitness vector has rank 1");
    check(std::abs(probe_fitness[0]) < 1e-12, "sin(0.0) evaluated to 0 through the fitness function");

    // 3 — single-objective run (real encoding, maximisation of sin(x))
    rng::prng.seed(0x123456789);
    const Population<RealGene> solutions = run_single_objective(sinx);
    check(!solutions.empty(), "single-objective run returned a population");
    check(solutions.size() <= 100, "population size never exceeds population_size");

    const double best_fitness = solutions.empty() ? -1.0 : solutions[0].fitness[0];
    const double best_gene = solutions.empty() ? -1.0 : solutions[0].chromosome[0];
    check(best_fitness > 0.9, "maximum of sin(x) on [0, 3.14] found above 0.9");
    check(best_fitness <= 1.0 + 1e-9, "maximum of sin(x) never exceeds 1.0");
    check(best_gene >= 0.0 && best_gene <= 3.14, "best candidate stays inside the search bounds");
    check(std::abs(best_fitness - std::sin(best_gene)) < 1e-12, "stored fitness equals sin(x) of the best gene");

    // 4 — multi-objective run (NSGA-III on the Kursawe function)
    rng::prng.seed(0x123456789);
    RCGA nsga{ 20 };
    nsga.algorithm(algorithm::NSGA3{});
    nsga.crossover_method(crossover::real::BLXa{});
    nsga.mutation_method(mutation::real::Boundary{ 0.1 });
    nsga.stop_condition(stopping::FitnessMeanStall{ 5 });
    const Population<RealGene> front = nsga.solve(Kursawe2{}, Bounds{ 0.0, 3.14 });

    check(!front.empty(), "multi-objective run returned a Pareto front");
    check(front.size() <= 20, "Pareto front size never exceeds population_size");
    check(!front.empty() && front[0].fitness.size() == 2, "multi-objective fitness vector has rank 2");

    bool front_in_bounds = true;
    for (const Candidate<RealGene>& sol : front)
    {
        for (const RealGene gene : sol.chromosome)
        {
            if (gene < 0.0 || gene > 3.14) front_in_bounds = false;
        }
    }
    check(front_in_bounds, "every candidate of the Pareto front stays inside the search bounds");

    // 5 — seeded reproducibility of the packaged library
    rng::prng.seed(20260926);
    const Population<RealGene> first_run = run_single_objective(sinx);
    rng::prng.seed(20260926);
    const Population<RealGene> second_run = run_single_objective(sinx);
    const double first = first_run.empty() ? -1.0 : first_run[0].fitness[0];
    const double second = second_run.empty() ? -1.0 : second_run[0].fitness[0];
    check(!first_run.empty() && !second_run.empty() && first == second,
          "identically seeded runs reproduce the same result");

    std::cout << "consumer assertions: " << checks_passed << '/' << checks_total << '\n';
    return checks_passed == checks_total ? 0 : 1;
}
