#!/bin/sh
# Executar dentro da imagem KAN-13 com /fonte.tar, /coletor e /evidencia montados.
set -eu
maven() {
    mvn --batch-mode --no-transfer-progress -Dstyle.color=never \
        -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC "$@"
}

marcar() {
    # O primeiro campo do uptime Linux é monotônico e tem resolução de 10 ms.
    read -r uptime idle </proc/uptime
    printf '%s\t%s\n' "$1" "$uptime" >>/evidencia/marcos.tsv
}

marcar prepare_start
mkdir /experimento /maven-cache
cd /experimento
tar -xf /fonte.tar
maven clean test-compile
cp -R /coletor/. target/test-classes/
marcar runner_start
codigo=0
maven -DforkCount=1 -DreuseForks=true \
    -Djunit.jupiter.execution.parallel.enabled=false \
    -Dkan23.trace=/evidencia/eventos.tsv "-Dtest=$1" surefire:test || codigo=$?
marcar reports_start
cp -R target/surefire-reports /evidencia/
marcar reports_finish
test -s /evidencia/eventos.tsv
exit "$codigo"
