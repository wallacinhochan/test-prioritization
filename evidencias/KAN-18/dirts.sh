set -eu

mkdir /seletor /inventario
cp -a /opt/dirts-maven /maven-cache
goal=edu.tum.sse.dirts:dirts-maven-plugin:1.0:method_level_select

selecionar() {
    fase=$1
    rm -f Excludes || return 1
    mvn -B -ntp -Dstyle.color=never -Duser.timezone=UTC -Dmaven.repo.local=/maven-cache \
        -Drat.skip=true -Dstandalone=true "$goal" > "/entrada/$fase.log" 2>&1 || return 1
    test -s Excludes || return 1
    cp Excludes "/entrada/$fase.excludes" || return 1
}

analisar() {
    cd /seletor
    tar -xf /entrada/pai.tar || return 1
    selecionar pai && selecionar controle || return 1
    grep -Fx 'DIRTS included: []' /entrada/controle.log >/dev/null || return 1
    tar -xf /entrada/alteracoes.tar || return 1
    selecionar alvo
}

if test -f /entrada/alteracoes.tar; then
    inicio=$(date +%s%N)
    if analisar; then
        printf '%s\n' ok > /entrada/dirts.status
    else
        printf '%s\n' erro > /entrada/dirts.status
    fi
    printf '%s\n' "$(( $(date +%s%N) - inicio ))" > /entrada/dirts.ns
else
    printf '%s\n' ignorado > /entrada/dirts.status
    printf '0\n' > /entrada/dirts.ns
fi

cd /inventario
sh /entrada/descobrir.sh > /entrada/descoberta.log 2>&1
