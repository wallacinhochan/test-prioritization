#!/bin/sh
set -eu

maven() {
    mvn --batch-mode --no-transfer-progress -Dstyle.color=never \
        -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC "$@"
}

rodada=$1
shift
saida=/evidencia/$rodada
mkdir "$saida"
inicio=$(date +%s%3N)
set +e
(
    set -eu
    case "$rodada" in
        controle)
            mkdir /trabalho /maven-cache
            cd /trabalho
            tar -xf /entrada/fonte.tar
            mvn --version
            codigo_maven=0
            maven clean test || codigo_maven=$?
            if [ -d target/surefire-reports ]; then
                cp -a target/surefire-reports "$saida/surefire"
            fi
            test "$codigo_maven" -eq 0 || exit "$codigo_maven"
            test -d "$saida/surefire"
            rm -rf target/surefire-reports
            mv /trabalho /base
            ;;
        pit)
            mkdir /pit
            cd /pit
            tar -xf /entrada/fonte.tar
            cp -a /base/target .
            printf '%s\n' "$1" | tr ',' '\n' | while IFS= read -r classe; do
                classe=$(printf '%s' "$classe" | tr . /)
                mkdir -p "$saida/originais/$(dirname "$classe")"
                cp -p "target/classes/$classe.class" "$saida/originais/$classe.class"
            done
            awk '
                /^    <plugins>[[:space:]]*$/ && !inseriu {
                    print
                    while ((getline linha < "/entrada/pit.xml") > 0) print linha
                    inseriu = 1
                    next
                }
                { print }
                END {
                    if (!inseriu) {
                        print "Lista de plugins do build não encontrada no POM." > "/dev/stderr"
                        exit 1
                    }
                }
            ' pom.xml > pom-pit.xml
            maven -f pom-pit.xml -Dpit.dryRun=true "-DtargetClasses=$1" \
                org.pitest:pitest-maven:1.19.4:mutationCoverage
            ;;
        inventario|intacto|restaurado|variante-*|repeticao)
            cp -a /base /trabalho
            cd /trabalho
            trap 'cd /; rm -rf /trabalho' EXIT
            rm -rf target/surefire-reports target/jacoco.exec
            if [ "$rodada" = inventario ]; then
                classpath=$(cat /entrada/classpath.txt)
                java -Duser.timezone=UTC -cp "$classpath" /entrada/DescobertaT0.java \
                    /entrada/classes-surefire.txt "$saida/metodos.tsv"
                exit
            fi

            registrar_binarios() {
                find target/classes target/test-classes src/test -type f -print0 |
                    sort -z | xargs -0 sha256sum
            }

            registrar_binarios > "$saida/antes.sha256"
            if [ "$#" -gt 0 ]; then
                classe="target/classes/$1.class"
                cp -p "$classe" "$saida/original.class"
                printf '%s  %s\n' "$4" "$saida/original.class" | sha256sum -c
                cp -p "/evidencia/pit/exportacao/$2" "$classe"
                sha256sum "$classe" > "$saida/mutado.sha256"
                printf '%s  %s\n' "$3" "$classe" | sha256sum -c
                if [ "$rodada" = restaurado ]; then
                    cp -p "$saida/original.class" "$classe"
                fi
            fi
            registrar_binarios > "$saida/executado.sha256"
            codigo_maven=0
            maven org.jacoco:jacoco-maven-plugin:0.8.13:prepare-agent@prepare-agent \
                org.apache.maven.plugins:maven-surefire-plugin:3.5.4:test@default-test || codigo_maven=$?
            if [ -d target/surefire-reports ]; then
                cp -a target/surefire-reports "$saida/surefire"
            fi
            registrar_binarios > "$saida/apos.sha256"
            cmp "$saida/executado.sha256" "$saida/apos.sha256"
            if [ "$#" -gt 0 ]; then
                cp -p "$saida/original.class" "$classe"
            fi
            registrar_binarios > "$saida/restaurado.sha256"
            cmp "$saida/antes.sha256" "$saida/restaurado.sha256"
            exit "$codigo_maven"
            ;;
        *)
            echo "Rodada inválida: $rodada" >&2
            exit 2
            ;;
    esac
) > "$saida/maven.log" 2>&1
codigo=$?
set -e
printf '{"codigo":%s,"duracao_ms":%s}\n' "$codigo" "$(($(date +%s%3N) - inicio))" > "$saida/execucao.json"
exit "$codigo"
