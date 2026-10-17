import java.io.StringReader;
import java.util.ArrayList;
import java.util.List;

public final class TestUnicodeStateLexer {
  private static void check(boolean condition, String message) {
    if (!condition) {
      throw new AssertionError(message);
    }
  }

  public static void main(String[] args) throws Exception {
    String input = "let caf\u00e9=\"\u4f60\u597d\"";
    UnicodeStateLexer lexer = new UnicodeStateLexer(new StringReader(input));
    List<String> tokens = new ArrayList<String>();
    for (String token = lexer.nextToken(); token != null; token = lexer.nextToken()) {
      tokens.add(token);
    }

    check(tokens.size() == 6, "expected six tokens, got " + tokens);
    check("KEYWORD(let)".equals(tokens.get(0)), "keyword mismatch: " + tokens);
    check("IDENT(caf\u00e9)".equals(tokens.get(1)), "unicode identifier mismatch: " + tokens);
    check("EQUALS".equals(tokens.get(2)), "equals mismatch: " + tokens);
    check("QUOTE_OPEN".equals(tokens.get(3)), "string open mismatch: " + tokens);
    check("TEXT(\u4f60\u597d)".equals(tokens.get(4)), "unicode text mismatch: " + tokens);
    check("QUOTE_CLOSE".equals(tokens.get(5)), "string close mismatch: " + tokens);

    System.out.println("JFlex Unicode/state test passed: " + tokens);
  }
}
