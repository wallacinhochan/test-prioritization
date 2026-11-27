package kan23;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Base64;
import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.TestExecutionListener;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;

public final class RastroJUnit implements TestExecutionListener {
    private final String output = System.getProperty("kan23.trace");
    private BufferedWriter writer;
    private long origin;
    private long sequence;

    @Override
    public synchronized void testPlanExecutionStarted(TestPlan plan) {
        if (output == null) {
            return;
        }
        try {
            writer = Files.newBufferedWriter(Path.of(output), StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            origin = System.nanoTime();
            anchor("start");
            writer.write("seq\tns\tevent\tunique_id_b64\tsource_b64\tdetail_b64\n");
            record("plan_start", null, "");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }

    @Override
    public synchronized void testPlanExecutionFinished(TestPlan plan) {
        if (writer == null) {
            return;
        }
        try {
            record("plan_finish", null, "");
            anchor("finish");
            writer.close();
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        } finally {
            writer = null;
        }
    }

    @Override
    public synchronized void dynamicTestRegistered(TestIdentifier test) {
        record("register", test, "");
    }

    @Override
    public synchronized void executionStarted(TestIdentifier test) {
        record("start", test, "");
    }

    @Override
    public synchronized void executionFinished(TestIdentifier test, TestExecutionResult result) {
        record("finish", test, result.getStatus().name());
    }

    @Override
    public synchronized void executionSkipped(TestIdentifier test, String reason) {
        record("skip", test, reason);
    }

    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private void anchor(String name) throws IOException {
        if (!Boolean.getBoolean("kan23.anchor")) {
            return;
        }
        long before = System.nanoTime() - origin;
        String uptime = Files.readString(Path.of("/proc/uptime")).split(" ", 2)[0];
        long after = System.nanoTime() - origin;
        Files.writeString(Path.of(output + ".clock.tsv"),
                name + "\t" + before + "\t" + uptime + "\t" + after + "\n",
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private void record(String event, TestIdentifier test, String detail) {
        if (writer == null) {
            return;
        }
        long elapsed = System.nanoTime() - origin;
        String source = test == null ? "" : test.getSource()
                .filter(MethodSource.class::isInstance)
                .map(MethodSource.class::cast)
                .map(method -> method.getClassName() + "#" + method.getMethodName()
                        + "(" + method.getMethodParameterTypes() + ")")
                .orElse("");
        try {
            writer.write(++sequence + "\t" + elapsed + "\t" + event + "\t"
                    + encode(test == null ? "" : test.getUniqueId()) + "\t"
                    + encode(source) + "\t" + encode(detail) + "\n");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }
}
