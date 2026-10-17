import java.io.ByteArrayOutputStream;
import java.io.PipedInputStream;
import java.io.PipedOutputStream;
import java.nio.charset.StandardCharsets;

import org.jline.reader.LineReader;
import org.jline.reader.LineReaderBuilder;
import org.jline.terminal.Attributes;
import org.jline.terminal.Size;
import org.jline.terminal.Terminal;
import org.jline.terminal.TerminalBuilder;
import org.jline.terminal.impl.AbstractPosixTerminal;
import org.jline.terminal.impl.DumbTerminal;
import org.jline.terminal.impl.ExecPty;
import org.jline.terminal.impl.PosixSysTerminal;

/**
 * OpenHarmony consumer assertions for the packaged JLine3 jars.
 *
 * pipe: no tty is attached, so the JNA/Jansi/Exec providers must degrade
 * cleanly and TerminalBuilder must serve a dumb terminal over plain streams;
 * LineReader must round-trip one line headlessly (the deployment shape used
 * by non-interactive consumers).
 *
 * pty: run attached to a real OpenHarmony pty. The packaged set has no
 * JNA/Jansi native runtime, so the system terminal must come up through the
 * ExecPty driver (busybox stty). This validates the attribute read path
 * (stty -a parsing), the raw-mode set/restore around readLine, and the
 * winsize round trip (TIOCSWINSZ from the master side reported back through
 * stty -a).
 */
public final class TestJLine3 {
    private static int checks;

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
        checks++;
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "pipe";
        if ("pty".equals(mode)) {
            pty();
        } else {
            pipe();
        }
        System.out.println("jline3 3.3.1 " + mode + " tests passed: " + checks);
        System.out.flush();
    }

    private static void pipe() throws Exception {
        // A piped stream (kept open) instead of a ByteArrayInputStream: the
        // reader pump must not see EOF while readLine is still consuming.
        PipedInputStream in = new PipedInputStream();
        PipedOutputStream feed = new PipedOutputStream(in);
        feed.write("ohos-pipe-line\r".getBytes(StandardCharsets.UTF_8));
        feed.flush();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Terminal terminal = TerminalBuilder.builder()
                .name("ohos-test")
                .streams(in, out)
                .dumb(true)
                .type(Terminal.TYPE_DUMB)
                .build();
        check(terminal != null, "terminal created");
        check(Terminal.TYPE_DUMB.equals(terminal.getType()), "dumb terminal type");
        LineReader reader = LineReaderBuilder.builder().terminal(terminal).build();
        String line = reader.readLine("pipe> ");
        check("ohos-pipe-line".equals(line), "readLine round trip");
        check(reader.getHistory().size() == 1, "history records the line");
        terminal.writer().println("ohos-writer-ok");
        terminal.writer().flush();
        String echo = new String(out.toByteArray(), StandardCharsets.UTF_8);
        check(echo.contains("pipe> "), "prompt written to stream");
        check(echo.contains("ohos-writer-ok"), "writer output captured");
        terminal.close();
        feed.close();
    }

    private static void pty() throws Exception {
        // Give the master side time to set the winsize before the terminal
        // size is first queried through stty.
        Thread.sleep(300);
        Terminal terminal = TerminalBuilder.builder()
                .name("ohos-pty")
                .system(true)
                .dumb(false)
                .build();
        check(terminal != null, "system terminal created");
        check(!(terminal instanceof DumbTerminal), "not a dumb terminal");
        check(terminal instanceof PosixSysTerminal, "posix system terminal");
        check(((AbstractPosixTerminal) terminal).getPty() instanceof ExecPty,
                "exec-stty pty driver used (JNA/Jansi native absent)");
        Attributes before = ((AbstractPosixTerminal) terminal).getPty().getAttr();
        check(before != null, "attributes read via exec stty");
        check(before.getLocalFlag(Attributes.LocalFlag.ICANON),
                "canonical mode on entry");

        LineReader reader = LineReaderBuilder.builder().terminal(terminal).build();
        String line = reader.readLine("pty> ");
        check("ohos-pty-line".equals(line), "raw-mode readLine round trip");

        Attributes after = ((AbstractPosixTerminal) terminal).getPty().getAttr();
        check(after.getLocalFlag(Attributes.LocalFlag.ICANON),
                "canonical mode restored");
        check(after.getLocalFlag(Attributes.LocalFlag.ECHO), "echo restored");

        Size size = terminal.getSize();
        System.out.println("JLINE_SIZE=" + size.getColumns() + "x" + size.getRows());
        System.out.flush();
        System.out.println("JLINE_CLASS=" + terminal.getClass().getName());
        System.out.flush();
        System.out.println("JLINE_PTYCLASS="
                + ((AbstractPosixTerminal) terminal).getPty().getClass().getName());
        System.out.flush();
        terminal.close();
    }
}
