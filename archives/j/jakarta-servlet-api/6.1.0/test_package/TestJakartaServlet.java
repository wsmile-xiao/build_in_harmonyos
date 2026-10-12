/**
 * TestJakartaServlet — jakarta.servlet-api 6.1.0 API 调用测试
 *
 * 使用反射加载并断言 jakarta.servlet / jakarta.servlet.http 命名空间的核心类型，
 * 验证 JAR 中的 API 完整可用（Jakarta Servlet 6.1 标准）。
 * 仅使用 JDK 类型（Class.forName + java.lang.reflect），编译期不依赖被测 JAR。
 */
public class TestJakartaServlet {

    private static int passed = 0;

    private static void ok(String msg) {
        passed++;
        System.out.println("OK[" + passed + "]: " + msg);
    }

    private static void fail(String msg) {
        System.err.println("FAIL: " + msg);
        System.exit(1);
    }

    private static Class<?> load(String name) throws Exception {
        Class<?> c = Class.forName(name);
        ok("loaded " + name);
        return c;
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        // 断言 1-13：jakarta.servlet 核心契约类型可加载
        Class<?> servlet = load("jakarta.servlet.Servlet");
        Class<?> servletConfig = load("jakarta.servlet.ServletConfig");
        Class<?> servletContext = load("jakarta.servlet.ServletContext");
        Class<?> filter = load("jakarta.servlet.Filter");
        Class<?> filterChain = load("jakarta.servlet.FilterChain");
        Class<?> servletRequest = load("jakarta.servlet.ServletRequest");
        Class<?> servletResponse = load("jakarta.servlet.ServletResponse");
        Class<?> inputStream = load("jakarta.servlet.ServletInputStream");
        Class<?> outputStream = load("jakarta.servlet.ServletOutputStream");
        Class<?> dispatcher = load("jakarta.servlet.RequestDispatcher");
        Class<?> asyncContext = load("jakarta.servlet.AsyncContext");
        Class<?> dispatcherType = load("jakarta.servlet.DispatcherType");
        Class<?> servletException = load("jakarta.servlet.ServletException");

        // 断言 14-20：jakarta.servlet.http 核心契约类型可加载
        Class<?> genericServlet = load("jakarta.servlet.GenericServlet");
        Class<?> httpServlet = load("jakarta.servlet.http.HttpServlet");
        Class<?> httpRequest = load("jakarta.servlet.http.HttpServletRequest");
        Class<?> httpResponse = load("jakarta.servlet.http.HttpServletResponse");
        Class<?> session = load("jakarta.servlet.http.HttpSession");
        Class<?> cookie = load("jakarta.servlet.http.Cookie");
        Class<?> part = load("jakarta.servlet.http.Part");

        // 断言 21：Servlet 是接口（历史上从抽象类改来）
        if (!servlet.isInterface()) {
            fail("jakarta.servlet.Servlet is not an interface");
        }
        ok("Servlet is an interface");

        // 断言 22：HttpServlet extends GenericServlet（继承链契约）
        if (!genericServlet.isAssignableFrom(httpServlet)) {
            fail("HttpServlet does not extend GenericServlet");
        }
        ok("HttpServlet extends GenericServlet");

        // 断言 23-24：HTTP 变体继承通用变体
        if (!servletRequest.isAssignableFrom(httpRequest)) {
            fail("HttpServletRequest does not extend ServletRequest");
        }
        ok("HttpServletRequest extends ServletRequest");
        if (!servletResponse.isAssignableFrom(httpResponse)) {
            fail("HttpServletResponse does not extend ServletResponse");
        }
        ok("HttpServletResponse extends ServletResponse");

        // 断言 25：输入/输出流为抽象类（容器实现，API 只给契约）
        if (!java.lang.reflect.Modifier.isAbstract(inputStream.getModifiers())
                || !java.lang.reflect.Modifier.isAbstract(outputStream.getModifiers())) {
            fail("ServletInputStream/ServletOutputStream are not abstract classes");
        }
        ok("ServletInputStream and ServletOutputStream are abstract classes");

        // 断言 26：DispatcherType 枚举含 5 个标准派发类型
        Object[] constants = dispatcherType.getEnumConstants();
        if (constants == null || constants.length != 5) {
            fail("DispatcherType is not an enum with 5 constants");
        }
        String names = "";
        for (Object c : constants) {
            names += ((Enum<?>) c).name() + ",";
        }
        for (String expected : new String[]{"REQUEST", "FORWARD", "INCLUDE", "ERROR", "ASYNC"}) {
            if (!names.contains(expected)) {
                fail("DispatcherType missing constant: " + expected);
            }
        }
        ok("DispatcherType has REQUEST/FORWARD/INCLUDE/ERROR/ASYNC");

        // 断言 27：ServletException 是受检异常（继承 Exception）
        if (!Exception.class.isAssignableFrom(servletException)) {
            fail("ServletException does not extend Exception");
        }
        ok("ServletException extends Exception");

        // 断言 28：Cookie 有 getName/setValue 等真实方法（非空壳类型）
        Class<?>[] noArg = new Class<?>[0];
        for (String m : new String[]{"getName", "getValue", "getMaxAge", "getPath"}) {
            cookie.getMethod(m, noArg);
        }
        ok("Cookie exposes getName/getValue/getMaxAge/getPath");

        // 断言 29：HttpSession 有 getAttribute/setAttribute/invalidate
        session.getMethod("getAttribute", new Class<?>[]{String.class});
        session.getMethod("setAttribute", new Class<?>[]{String.class, Object.class});
        session.getMethod("invalidate", noArg);
        ok("HttpSession exposes getAttribute/setAttribute/invalidate");

        // 断言 30：ServletRequest 有 getParameter/getInputStream（API 契约）
        servletRequest.getMethod("getParameter", new Class<?>[]{String.class});
        servletRequest.getMethod("getInputStream", noArg);
        ok("ServletRequest exposes getParameter/getInputStream");

        // 断言 31：AsyncContext 存在（Servlet 3.0+ 异步支持）
        asyncContext.getMethod("start", new Class<?>[]{Runnable.class});
        ok("AsyncContext exposes start(Runnable)");

        // 断言 32：Part 存在（multipart/form-data 上传契约）
        part.getMethod("getInputStream", noArg);
        ok("Part exposes getInputStream");

        System.out.println("PASS: jakarta-servlet-api 6.1.0 — " + passed + " assertions passed");
    }
}
