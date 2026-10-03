import melting.Main;
import melting.ThermoResult;
import melting.configuration.OptionManagement;

/**
 * TestMelting — melting 5.2.0 API call test.
 *
 * Calls melting.Main.getMeltingResults (the same entry used by the melting
 * CLI and by upstream src/examples/MainTest) for two DNA duplexes and checks
 * six assertions: Tm in a physical range plus non-zero enthalpy/entropy.
 */
public class TestMelting {
    static int checks = 0;

    static void check(boolean cond, String name) {
        checks++;
        if (!cond) {
            System.err.println("FAIL: " + name);
            System.exit(1);
        }
        System.out.println("OK: " + name);
    }

    static ThermoResult runCase(String sequence) throws Exception {
        String[] args = {"-H", "dnadna", "-E", "Na=1", "-P", "0.0004", "-S", sequence, "-nn", "all97"};
        OptionManagement optionManager = new OptionManagement();
        ThermoResult results = Main.getMeltingResults(args, optionManager);
        if (results == null) {
            System.err.println("FAIL: null ThermoResult for " + sequence);
            System.exit(1);
        }
        return results;
    }

    public static void main(String[] args) throws Exception {
        // Case 1: CCATCGCTACC (upstream DNANoSelfComplementary.txt, TmExp 67.6)
        ThermoResult r1 = runCase("CCATCGCTACC");
        check(r1.getTm() > 0.0 && r1.getTm() < 150.0, "case1 Tm in (0,150): " + r1.getTm());
        check(r1.getEnthalpy() != 0.0, "case1 enthalpy non-zero: " + r1.getEnthalpy());
        check(r1.getEntropy() != 0.0, "case1 entropy non-zero: " + r1.getEntropy());

        // Case 2: GCGAGC (upstream DNANoSelfComplementary.txt, TmExp 33.2)
        ThermoResult r2 = runCase("GCGAGC");
        check(r2.getTm() > 0.0 && r2.getTm() < 150.0, "case2 Tm in (0,150): " + r2.getTm());
        check(r2.getEnthalpy() != 0.0, "case2 enthalpy non-zero: " + r2.getEnthalpy());
        check(r2.getEntropy() != 0.0, "case2 entropy non-zero: " + r2.getEntropy());

        System.out.println("PASS: melting API test - 6 checks passed");
    }
}
