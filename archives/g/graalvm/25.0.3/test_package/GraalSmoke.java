public final class GraalSmoke {
    private GraalSmoke() {}

    public static void main(String[] args) {
        int value = 6 * 7;
        if (value != 42) {
            throw new AssertionError("unexpected arithmetic result: " + value);
        }
        String vendor = System.getProperty("java.vm.vendor", "unknown");
        System.out.println("JAVA_SMOKE_OK=" + vendor + ":" + value);
    }
}
