%%
%public
%class UnicodeStateLexer
%unicode
%type String
%function nextToken
%state STRING
%{
  private String token(String kind) {
    return kind + "(" + yytext() + ")";
  }
%}

Identifier = [:jletter:] [:jletterdigit:]*
Whitespace = \s+

%%
<YYINITIAL> {Whitespace} { /* Ignore whitespace. */ }
<YYINITIAL> "let" { return "KEYWORD(let)"; }
<YYINITIAL> {Identifier} { return token("IDENT"); }
<YYINITIAL> "=" { return "EQUALS"; }
<YYINITIAL> \" { yybegin(STRING); return "QUOTE_OPEN"; }
<STRING> \" { yybegin(YYINITIAL); return "QUOTE_CLOSE"; }
<STRING> [^\"]+ { return token("TEXT"); }
<<EOF>> { return null; }
[^] {
  throw new IllegalArgumentException(
      "Unexpected character in state " + yystate() + ": " + yytext());
}
