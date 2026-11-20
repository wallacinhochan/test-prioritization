import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Comparator;
import java.util.stream.Collectors;

import org.junit.platform.engine.UniqueId;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.engine.support.descriptor.ClassSource;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

class DescobertaT0 {
    public static void main(String[] args) throws Exception {
        var seletores = Files.readAllLines(Path.of(args[0])).stream()
            .map(DiscoverySelectors::selectClass).toList();
        var pedido = LauncherDiscoveryRequestBuilder.request().selectors(seletores).build();
        var plano = LauncherFactory.create().discover(pedido);
        try (var saida = Files.newBufferedWriter(Path.of(args[1]))) {
            saida.write("raiz\tclasse\trotulo_classe\tmetodo\ttipos\ttipos_curtos\trotulo_metodo\ttipo_descritor\tdescritor\n");
            for (var teste : plano.getRoots().stream().flatMap(raiz -> plano.getDescendants(raiz).stream())
                    .sorted(Comparator.comparing(TestIdentifier::getUniqueId)).toList()) {
                if (!(teste.getSource().orElse(null) instanceof MethodSource origem)) {
                    continue;
                }
                var classe = classeDeExecucao(plano, teste);
                var uid = UniqueId.parse(teste.getUniqueId());
                var raiz = uid.getSegments().stream().filter(segmento -> segmento.getType().equals("class"))
                    .findFirst().orElseThrow().getValue();
                var parametros = origem.getJavaMethod().getParameterTypes();
                var tipos = Arrays.stream(parametros).map(Class::getTypeName).collect(Collectors.joining(","));
                var curtos = Arrays.stream(parametros).map(Class::getSimpleName).collect(Collectors.joining(","));
                var nomeClasse = ((ClassSource) classe.getSource().orElseThrow()).getClassName();
                var registro = Arrays.stream(new String[] {
                    raiz, nomeClasse, classe.getDisplayName(), origem.getMethodName(), tipos, curtos,
                    teste.getDisplayName(), uid.getLastSegment().getType(), teste.getUniqueId()
                }).map(campo -> "\"" + campo.replace("\"", "\"\"") + "\"").collect(Collectors.joining("\t"));
                saida.write(registro);
                saida.newLine();
            }
        }
    }

    private static TestIdentifier classeDeExecucao(TestPlan plano, TestIdentifier teste) {
        var ancestral = plano.getParent(teste).orElseThrow();
        while (!(ancestral.getSource().orElse(null) instanceof ClassSource)) {
            ancestral = plano.getParent(ancestral).orElseThrow();
        }
        return ancestral;
    }
}
