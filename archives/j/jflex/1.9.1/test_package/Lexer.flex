%%
%public
%class GeneratedLexer
%unicode
%type String
%function nextToken
%line
%column
%{
  private String token(String kind) {
    return kind + "(" + yytext() + ")";
  }
%}

Identifier = [:jletter:] [:jletterdigit:]*
Integer = 0 | [1-9][0-9]*
Whitespace = \s+

%%
{Whitespace} { /* Ignore whitespace. */ }
{Integer} { return token("INTEGER"); }
{Identifier} { return token("IDENT"); }
"+" { return "PLUS"; }
<<EOF>> { return null; }
[^] { throw new IllegalArgumentException("Unexpected character: " + yytext()); }
