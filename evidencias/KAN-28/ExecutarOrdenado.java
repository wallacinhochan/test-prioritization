package kan28;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.TestExecutionListener;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

/**
 * Executa uma lista ordenada de metodos JUnit 5 (classe#metodo(tipos))
 * na ordem exata especificada, registrando um unico rastro monotonico continuo
 * no mesmo formato de KAN-23/RastroJUnit com ancoras de /proc/uptime.
 */
public final class ExecutarOrdenado {
    private ExecutarOrdenado() {
    }

    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static void anchor(Path tracePath, long origin, String name) throws IOException {
        long before = System.nanoTime() - origin;
        String uptime = Files.readString(Path.of("/proc/uptime"), StandardCharsets.UTF_8)
                .trim().split("\\s+", 2)[0];
        long after = System.nanoTime() - origin;
        Files.writeString(
                Path.of(tracePath.toString() + ".clock.tsv"),
                name + "\t" + before + "\t" + uptime + "\t" + after + "\n",
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND);
    }

    private static final class MethodStats {
        int invocations;
        int pass;
        int fail;
        int skip;
        long firstStartNs = -1L;
        long lastEndNs = -1L;
        long sumExecNs;
        final Map<String, Long> activeStarts = new HashMap<>();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            System.err.println("Uso: ExecutarOrdenado <ordem.txt> <eventos.tsv> <resumo_ordenado.tsv>");
            System.exit(2);
        }
        Path orderPath = Path.of(args[0]);
        Path tracePath = Path.of(args[1]);
        Path summaryPath = Path.of(args[2]);

        List<String> testIds = Files.readAllLines(orderPath, StandardCharsets.UTF_8).stream()
                .map(String::trim)
                .filter(line -> !line.isEmpty())
                .toList();

        Launcher launcher = LauncherFactory.create();
        long[] sequence = {0L};
        int[] failures = {0};
        int[] missing = {0};

        try (BufferedWriter traceWriter = Files.newBufferedWriter(
                tracePath, StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
             BufferedWriter summaryWriter = Files.newBufferedWriter(
                     summaryPath, StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {

            long origin = System.nanoTime();
            anchor(tracePath, origin, "start");
            traceWriter.write("seq\tns\tevent\tunique_id_b64\tsource_b64\tdetail_b64\n");
            summaryWriter.write(
                    "rank\ttest_id\tdiscovered\tinvocations\tpass\tfail\tskip\t"
                            + "method_start_ns\tmethod_end_ns\tmethod_wall_ns\tinvocations_sum_ns\n");

            writeEvent(traceWriter, sequence, origin, "plan_start", "", "", "");

            for (int i = 0; i < testIds.size(); i++) {
                int rank = i + 1;
                String testId = testIds.get(i);
                int hashIdx = testId.indexOf('#');
                int openIdx = testId.indexOf('(', hashIdx + 1);
                if (hashIdx <= 0 || openIdx <= hashIdx + 1 || !testId.endsWith(")")) {
                    throw new IllegalArgumentException("test_id invalido: " + testId);
                }
                String className = testId.substring(0, hashIdx);
                String methodName = testId.substring(hashIdx + 1, openIdx);
                String paramTypes = testId.substring(openIdx + 1, testId.length() - 1);

                long methodCallStart = System.nanoTime() - origin;
                LauncherDiscoveryRequest request = LauncherDiscoveryRequestBuilder.request()
                        .selectors(DiscoverySelectors.selectMethod(className, methodName, paramTypes))
                        .configurationParameter("junit.jupiter.execution.parallel.enabled", "false")
                        .build();
                TestPlan plan = launcher.discover(request);
                boolean discovered = plan.containsTests();
                MethodStats stats = new MethodStats();
                if (!discovered) {
                    missing[0]++;
                } else {
                    final String stepPrefix = "[step:" + rank + "]/";
                    TestExecutionListener listener = new TestExecutionListener() {
                        @Override
                        public void dynamicTestRegistered(TestIdentifier test) {
                            record(traceWriter, sequence, origin, stepPrefix, "register", test, "");
                        }

                        @Override
                        public void executionStarted(TestIdentifier test) {
                            long ns = record(traceWriter, sequence, origin, stepPrefix, "start", test, "");
                            if (test.isTest()) {
                                stats.activeStarts.put(test.getUniqueId(), ns);
                                if (stats.firstStartNs < 0L) {
                                    stats.firstStartNs = ns;
                                }
                            }
                        }

                        @Override
                        public void executionFinished(TestIdentifier test, TestExecutionResult result) {
                            String status = result.getStatus().name();
                            long ns = record(traceWriter, sequence, origin, stepPrefix, "finish", test, status);
                            if (test.isTest()) {
                                stats.invocations++;
                                Long started = stats.activeStarts.remove(test.getUniqueId());
                                if (started != null) {
                                    stats.sumExecNs += Math.max(0L, ns - started);
                                }
                                stats.lastEndNs = ns;
                                switch (result.getStatus()) {
                                    case SUCCESSFUL -> stats.pass++;
                                    case FAILED -> {
                                        stats.fail++;
                                        failures[0]++;
                                    }
                                    case ABORTED -> stats.skip++;
                                }
                            }
                        }

                        @Override
                        public void executionSkipped(TestIdentifier test, String reason) {
                            record(traceWriter, sequence, origin, stepPrefix, "skip", test, reason == null ? "" : reason);
                            if (test.isTest() || test.getSource().filter(MethodSource.class::isInstance).isPresent()) {
                                stats.invocations++;
                                stats.skip++;
                            }
                        }
                    };
                    launcher.execute(plan, listener);
                }
                long methodCallEnd = System.nanoTime() - origin;
                long wallNs = Math.max(0L, methodCallEnd - methodCallStart);
                summaryWriter.write(rank + "\t" + testId + "\t" + discovered + "\t"
                        + stats.invocations + "\t" + stats.pass + "\t" + stats.fail + "\t" + stats.skip + "\t"
                        + (stats.firstStartNs >= 0L ? stats.firstStartNs : methodCallStart) + "\t"
                        + (stats.lastEndNs >= 0L ? stats.lastEndNs : methodCallEnd) + "\t"
                        + wallNs + "\t" + stats.sumExecNs + "\n");
            }

            writeEvent(traceWriter, sequence, origin, "plan_finish", "", "", "");
            anchor(tracePath, origin, "finish");
        }

        System.out.println("KAN28_ORDERED_DONE methods=" + testIds.size()
                + " missing=" + missing[0] + " failures=" + failures[0]);
        if (missing[0] > 0 || failures[0] > 0) {
            System.exit(1);
        }
    }

    private static long record(BufferedWriter writer, long[] sequence, long origin,
                               String stepPrefix, String event, TestIdentifier test, String detail) {
        String source = test == null ? "" : test.getSource()
                .filter(MethodSource.class::isInstance)
                .map(MethodSource.class::cast)
                .map(method -> method.getClassName() + "#" + method.getMethodName()
                        + "(" + method.getMethodParameterTypes() + ")")
                .orElse("");
        return writeEvent(writer, sequence, origin, event,
                test == null ? "" : stepPrefix + test.getUniqueId(), source, detail);
    }

    private static long writeEvent(BufferedWriter writer, long[] sequence, long origin,
                                   String event, String uid, String source, String detail) {
        long elapsed = System.nanoTime() - origin;
        try {
            writer.write(++sequence[0] + "\t" + elapsed + "\t" + event + "\t"
                    + encode(uid) + "\t" + encode(source) + "\t" + encode(detail) + "\n");
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        return elapsed;
    }
}
