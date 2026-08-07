import java.nio.file.Files;
import java.nio.file.Path;

public final class FontManagerLoadSmoke {
    private FontManagerLoadSmoke() {}

    public static void main(String[] args) {
        if (args.length != 1) {
            throw new IllegalArgumentException("expected one font manager path");
        }
        Path library = Path.of(args[0]);
        if (!library.isAbsolute() || !Files.isRegularFile(library)) {
            throw new IllegalArgumentException(
                    "font manager path must name an absolute regular file");
        }
        System.load(library.toString());
        System.out.println("JAVA_FONT_MANAGER_LOAD_OK=true");
    }
}
