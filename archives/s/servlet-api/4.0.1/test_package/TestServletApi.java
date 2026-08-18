import java.io.IOException;
import javax.servlet.ReadListener;
import javax.servlet.ServletInputStream;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;

public final class TestServletApi {
    private static final class EmptyInputStream extends ServletInputStream {
        @Override
        public boolean isFinished() { return true; }

        @Override
        public boolean isReady() { return true; }

        @Override
        public void setReadListener(ReadListener listener) { }

        @Override
        public int read() throws IOException { return -1; }
    }

    public static void main(String[] args) throws Exception {
        Cookie cookie = new Cookie("session", "ok");
        if (!"session".equals(cookie.getName())) throw new AssertionError("cookie name");
        if (!"ok".equals(cookie.getValue())) throw new AssertionError("cookie value");
        cookie.setHttpOnly(true);
        if (!cookie.isHttpOnly()) throw new AssertionError("HttpOnly flag");

        ServletInputStream input = new EmptyInputStream();
        if (!input.isFinished() || !input.isReady()) throw new AssertionError("stream state");
        if (input.readLine(new byte[4], 0, 4) != -1) throw new AssertionError("empty stream");

        if (!HttpServletRequest.BASIC_AUTH.equals("BASIC")) {
            throw new AssertionError("HTTP auth constant");
        }
        if (cookie.getMaxAge() != -1) throw new AssertionError("default max age");
        System.out.println("servlet-api 4.0.1 consumer test: PASS");
    }
}
