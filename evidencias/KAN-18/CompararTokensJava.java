import com.sun.tools.javac.parser.ScannerFactory;
import com.sun.tools.javac.parser.Tokens.TokenKind;
import com.sun.tools.javac.util.Context;
import com.sun.tools.javac.util.Log;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import javax.tools.SimpleJavaFileObject;

/** Compares the javac token stream, retaining exact spellings and deprecation markers. */
class CompararTokensJava {
    private static final Pattern UNICODE_ESCAPE = Pattern.compile("\\\\u");

    private record Token(TokenKind kind, String raw, boolean deprecated) {}

    private static List<Token> scan(Path path) throws Exception {
        String source = Files.readString(path, StandardCharsets.UTF_8);
        if (UNICODE_ESCAPE.matcher(source).find() || source.indexOf('\u001a') >= 0) {
            throw new IllegalArgumentException("preprocessing-sensitive input");
        }
        var context = new Context();
        var log = Log.instance(context);
        log.useSource(new SimpleJavaFileObject(path.toUri(), javax.tools.JavaFileObject.Kind.SOURCE) {
            @Override
            public CharSequence getCharContent(boolean ignoreEncodingErrors) {
                return source;
            }
        });
        var scanner = ScannerFactory.instance(context).newScanner(source, true);
        var tokens = new ArrayList<Token>();
        scanner.nextToken();
        while (scanner.token().kind != TokenKind.EOF) {
            var token = scanner.token();
            if (token.kind == TokenKind.ERROR || log.nerrors != 0) {
                throw new IllegalArgumentException("lexical error");
            }
            tokens.add(new Token(token.kind, source.substring(token.pos, token.endPos), token.deprecatedFlag()));
            scanner.nextToken();
        }
        if (log.nerrors != 0) {
            throw new IllegalArgumentException("lexical error");
        }
        return tokens;
    }

    public static void main(String[] args) throws Exception {
        for (int i = 0; i < args.length; i += 2) {
            try {
                System.out.println(scan(Path.of(args[i])).equals(scan(Path.of(args[i + 1])))
                        ? "equivalente" : "tokens_distintos");
            } catch (Exception e) {
                System.out.println("incerto");
            }
        }
    }
}
