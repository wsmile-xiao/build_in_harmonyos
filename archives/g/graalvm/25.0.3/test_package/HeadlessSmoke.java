import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.GraphicsEnvironment;
import java.awt.image.BufferedImage;

public final class HeadlessSmoke {
    private HeadlessSmoke() {}

    public static void main(String[] args) {
        String osName = System.getProperty("os.name");
        if (!"HarmonyOS".equals(osName)) {
            throw new AssertionError("unexpected os.name: " + osName);
        }
        String fontConfigOverride = System.getProperty("sun.awt.fontconfig");
        if (fontConfigOverride != null) {
            throw new AssertionError(
                    "sun.awt.fontconfig override is forbidden: "
                            + fontConfigOverride);
        }
        if (!GraphicsEnvironment.isHeadless()) {
            throw new AssertionError("GraalVM must run in headless mode");
        }

        BufferedImage image = new BufferedImage(96, 32, BufferedImage.TYPE_INT_ARGB);
        Graphics2D graphics = image.createGraphics();
        int width;
        int ascent;
        try {
            graphics.setColor(Color.WHITE);
            graphics.fillRect(0, 0, image.getWidth(), image.getHeight());
            graphics.setColor(Color.BLACK);
            graphics.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 18));
            FontMetrics metrics = graphics.getFontMetrics();
            width = metrics.stringWidth("OpenHarmony");
            ascent = metrics.getAscent();
            if (width <= 0 || ascent <= 0) {
                throw new AssertionError("font metrics did not resolve a glyph face");
            }
            graphics.drawString("OpenHarmony", 2, ascent + 2);
        } finally {
            graphics.dispose();
        }

        boolean renderedInk = false;
        for (int y = 0; y < image.getHeight() && !renderedInk; ++y) {
            for (int x = 0; x < image.getWidth(); ++x) {
                if (image.getRGB(x, y) != Color.WHITE.getRGB()) {
                    renderedInk = true;
                    break;
                }
            }
        }
        if (!renderedInk) {
            throw new AssertionError(
                    "headless font rendering produced no glyph pixels");
        }
        System.out.println("JAVA_OS_NAME=" + osName);
        System.out.println("JAVA_FONTCONFIG_OVERRIDE=unset");
        System.out.println("JAVA_HEADLESS_OK=true");
    }
}
