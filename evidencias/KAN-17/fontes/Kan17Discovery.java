import org.junit.jupiter.engine.JupiterTestEngine;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.core.LauncherConfig;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;
import java.util.stream.Stream;

class Kan17Discovery {
    public static void main(String[] args) {
        var config = LauncherConfig.builder()
            .enableTestEngineAutoRegistration(false)
            .addTestEngines(new JupiterTestEngine()).build();
        var request = LauncherDiscoveryRequestBuilder.request()
            .selectors(Stream.of(args).map(DiscoverySelectors::selectClass).toList()).build();
        var plan = LauncherFactory.create(config).discover(request);
        plan.getRoots().stream().flatMap(root -> plan.getDescendants(root).stream())
            .filter(test -> test.getSource().orElse(null) instanceof MethodSource)
            .map(test -> test.getDisplayName() + "\t" + test.getSource().orElseThrow() + "\t" + test.getUniqueId())
            .sorted().forEach(System.out::println);
    }
}
