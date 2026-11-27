package kan23;

import static org.junit.platform.engine.discovery.DiscoverySelectors.selectClass;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.DynamicTest;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

public final class Piloto {
    @Test
    void executado() {}

    @Disabled
    @Test
    void omitido() {}

    @TestFactory
    DynamicTest dinamico() {
        return DynamicTest.dynamicTest("filho", () -> {});
    }

    public static void main(String[] args) {
        var request = LauncherDiscoveryRequestBuilder.request()
                .selectors(selectClass(Piloto.class))
                .configurationParameter("junit.jupiter.execution.parallel.enabled", "false")
                .build();
        LauncherFactory.create().execute(request);
    }
}
