import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

import nu.xom.Builder;
import nu.xom.Document;
import nu.xom.Element;
import nu.xom.ParsingException;
import nu.xom.Serializer;

/**
 * Consumer smoke test for xom 1.4.4.
 *
 * Builds a small XML document with the XOM API, serializes it to a
 * byte array, then re-parses the serialized output with the XOM
 * Builder. The test asserts that the round-tripped root element name
 * and the re-parsed document root match the original. A failure
 * raises {@link AssertionError} with exit code 1.
 *
 * This exercises the core nu.xom API (Element, Document, Builder,
 * Serializer) that consumers of the xom package depend on.
 */
public final class TestXom {

    private TestXom() {
    }

    public static void main(String[] args) throws Exception {
        Element root = new Element("greeting");
        Element child = new Element("message");
        child.appendChild("Hello from XOM on HarmonyOS");
        root.appendChild(child);
        Document doc = new Document(root);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Serializer serializer = new Serializer(out, "UTF-8");
        serializer.setIndent(2);
        serializer.write(doc);
        serializer.flush();
        byte[] payload = out.toByteArray();

        Builder builder = new Builder();
        Document reparsed;
        try (ByteArrayInputStream in = new ByteArrayInputStream(payload)) {
            reparsed = builder.build(in);
        }

        String originalRoot = doc.getRootElement().getQualifiedName();
        String reparsedRoot = reparsed.getRootElement().getQualifiedName();
        if (!"greeting".equals(originalRoot)) {
            throw new AssertionError(
                "original root mismatch: " + originalRoot
            );
        }
        if (!originalRoot.equals(reparsedRoot)) {
            throw new AssertionError(
                "round-trip root mismatch: original="
                    + originalRoot
                    + " reparsed="
                    + reparsedRoot
            );
        }
        String message = reparsed.getRootElement()
            .getFirstChildElement("message")
            .getValue();
        if (!"Hello from XOM on HarmonyOS".equals(message)) {
            throw new AssertionError(
                "round-trip text mismatch: " + message
            );
        }

        System.out.println("TestXom: PASS (round-trip ok)");
    }
}
