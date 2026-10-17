import java.io.StringReader;
import java.util.ArrayList;
import java.util.List;

public final class TestLexer {
  private static void check(boolean condition, String message) {
    if (!condition) {
      throw new AssertionError(message);
    }
  }

  public static void main(String[] args) throws Exception {
    GeneratedLexer lexer = new GeneratedLexer(new StringReader("sum+42 value"));
    List<String> tokens = new ArrayList<String>();
    for (String token = lexer.nextToken(); token != null; token = lexer.nextToken()) {
      tokens.add(token);
    }

    check(tokens.size() == 4, "expected four tokens, got " + tokens);
    check("IDENT(sum)".equals(tokens.get(0)), "identifier mismatch: " + tokens);
    check("PLUS".equals(tokens.get(1)), "plus mismatch: " + tokens);
    check("INTEGER(42)".equals(tokens.get(2)), "integer mismatch: " + tokens);
    check("IDENT(value)".equals(tokens.get(3)), "identifier mismatch: " + tokens);

    System.out.println("JFlex consumer test passed: " + tokens);
  }
}
