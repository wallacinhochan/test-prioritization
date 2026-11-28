#!/bin/sh
# Executar dentro da imagem KAN-13 com /fonte.tar, /ordem.txt, /launcher-jars, /roteiros e /evidencia montados.
set -eu
maven() {
    mvn --batch-mode --no-transfer-progress -Dstyle.color=never \
        -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC "$@"
}

marcar() {
    read -r uptime idle </proc/uptime
    printf '%s\t%s\n' "$1" "$uptime" >>/evidencia/marcos.tsv
}

marcar prepare_start
mkdir -p /experimento /maven-cache /runner-classes
cd /experimento
tar -xf /fonte.tar
maven clean test-compile
maven dependency:build-classpath -DincludeScope=test -Dmdep.outputFile=/tmp/test-cp.txt
LAUNCHER_JARS="$(find /launcher-jars -name '*.jar' | tr '\n' ':' | sed 's/:$//')"
FULL_CP="target/test-classes:target/classes:$(cat /tmp/test-cp.txt):${LAUNCHER_JARS}"
javac -cp "$FULL_CP" -d /runner-classes /roteiros/ExecutarOrdenado.java
marcar runner_start
codigo=0
java -Xmx512m -Duser.timezone=UTC \
    --add-opens java.base/java.lang.reflect=ALL-UNNAMED \
    --add-opens java.base/java.lang=ALL-UNNAMED \
    --add-opens java.base/java.util=ALL-UNNAMED \
    --add-opens java.base/java.time=ALL-UNNAMED \
    --add-opens java.base/java.time.chrono=ALL-UNNAMED \
    -cp "/runner-classes:${FULL_CP}" \
    kan28.ExecutarOrdenado /ordem.txt /evidencia/eventos.tsv /evidencia/resumo_ordenado.tsv || codigo=$?
marcar reports_start
cp /ordem.txt /evidencia/ordem.txt
marcar reports_finish
test -s /evidencia/eventos.tsv
test -s /evidencia/resumo_ordenado.tsv
exit "$codigo"
