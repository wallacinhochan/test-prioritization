set -eu
export LC_ALL=C
export TZ=UTC
goal=edu.tum.sse.dirts:dirts-maven-plugin:1.0:method_level_select
mkdir /work
cp -a /opt/dirts-maven /maven-cache
cp -a /opt/dirts-maven /t0-cache
cp -a /opt/dirts-maven /controle-cache
cd /work

time_step() {
    phase=$1
    shift
    start=$(date +%s%N)
    rc=0
    "$@" || rc=$?
    printf '%s,%s,%s\n' "$phase" "$(( $(date +%s%N) - start ))" "$rc" >> /out/tempos.csv
    return "$rc"
}

unpack() {
    mkdir -p "$2"
    tar -xf "/out/$1.tar" -C "$2"
}

maven() {
    cache=$1
    shift
    mvn -B -ntp -Dstyle.color=never -Duser.timezone=UTC -Drat.skip=true "-Dmaven.repo.local=$cache" "$@"
}

select_dirts() {
    rc=0
    rm -f Excludes || return 1
    maven "$2" -Dstandalone=true "$goal" > "$1.log" 2>&1 || rc=$?
    [ "$rc" = 0 ] && [ -s Excludes ] || return 1
    cp Excludes "$1.excludes"
}

state_files() {
    find .dirts -type f -print0 | sort -z | xargs -0 -r sha256sum
}

seal_state() {
    [ -d .dirts ] || return 1
    for prefix in graph checksums cuMapping; do
        test -n "$(find .dirts -type f -size +0c -name "${prefix}_*" -print -quit)" || return 1
    done
    state_files > /work/state.hashes && printf '%s\n' "$1" > /work/state.sha
}

valid_state() {
    [ -d .dirts ] && [ -s /work/state.hashes ] && [ "$(cat /work/state.sha 2>/dev/null)" = "$1" ] &&
    state_files > /work/current.hashes && cmp -s /work/state.hashes /work/current.hashes
}

initialize() (
    mkdir /work/state
    unpack "$1" /work/state
    cd /work/state
    select_dirts "$2" "$3" && seal_state "$1"
)

prepare_target() (
    target=$1
    mkdir -p /work/source
    cd /work/state || exit 1
    valid_state "$(cat "/out/$target.parent")" || exit 1
    cd /work
    unpack "$target" /work/source || exit 1
    mv /work/state/.dirts /work/source/.dirts
)

validate_output() (
    dir=$1
    excludes=$2
    log=$3
    { IFS= read -r header && IFS= read -r nested &&
        [ "$header" = '# DIRTS excluded' ] && [ "$nested" = '**/*$*' ] &&
        ! grep -Ev '^([A-Za-z0-9_$]+/)+[A-Za-z0-9_$]+\.java$'; } < "$excludes" || exit 1
    sed '1,2d;s#/#.#g;s/\.java$//' "$excludes" | sort -u > "$dir/excluded.txt"
    comm -23 "$dir/classes.txt" "$dir/excluded.txt" > "$dir/dirts-roots.txt"
    grep -q '^DIRTS included: \[' "$log" || exit 1
    sed -n '/^DIRTS included: \[/,/^\[INFO\] ---/p' "$log" |
        sed '1s/^DIRTS included: \[//;s/^\([A-Za-z0-9_$.]*\) <-- .*/\1/p;d' |
        sort -u > "$dir/included-all.txt"
    comm -12 "$dir/classes.txt" "$dir/included-all.txt" > "$dir/included.txt"
    cmp -s "$dir/dirts-roots.txt" "$dir/included.txt" || exit 1
    grep -q '^\[INFO\] Recalculating primary dependencies of:' "$log" || exit 1
    if [ ! -s "$dir/dirts-roots.txt" ]; then
        awk '/^\[TIME\] Cropping dependency graph/{seen=0}
             seen && NF{exit 1}
             /^\[INFO\] Recalculating primary dependencies of:/{seen=1}' "$log" || exit 1
    fi
    comm -23 "$dir/changed-tests.txt" "$dir/dirts-roots.txt" > "$dir/missing-tests.txt"
    [ ! -s "$dir/missing-tests.txt" ]
)

discover() (
    dir=$1
    maven /maven-cache test-compile \
        org.apache.maven.plugins:maven-dependency-plugin:3.9.0:build-classpath \
        -DincludeScope=test "-Dmdep.outputFile=$dir/dependencias.txt" || exit 1
    deps=$(cat "$dir/dependencias.txt")
    engine=$(printf '%s\n' "$deps" | tr ':' '\n' | grep '/junit-platform-engine/[^/]*/junit-platform-engine-[^/]*\.jar$')
    [ "$(printf '%s\n' "$engine" | wc -l)" = 1 ] || exit 1
    platform=$(basename "$(dirname "$engine")")
    maven /maven-cache org.apache.maven.plugins:maven-dependency-plugin:3.9.0:get \
        "-Dartifact=org.junit.platform:junit-platform-launcher:$platform" -Dtransitive=false || exit 1
    cp="target/test-classes:target/classes:$deps:/maven-cache/org/junit/platform/junit-platform-launcher/$platform/junit-platform-launcher-$platform.jar"
    find target/test-classes -type f -name '*Test.class' ! -name '*$*' |
        sed 's#^target/test-classes/##; s#\.class$##; s#/#.#g' | sort > "$dir/classes.txt"
    java -Duser.timezone=UTC -cp "$cp" /out/DescobertaT0.java "$dir/classes.txt" "$dir/metodos.tsv" || exit 1
    jdeps --multi-release 21 -verbose:class -filter:none -cp "$cp" target/classes target/test-classes > "$dir/jdeps.txt"
)

expand_roots() (
    dir=$1
    [ -s "$dir/metodos.tsv" ] && [ -s "$dir/classes.txt" ] && [ -s "$dir/jdeps.txt" ] || exit 1
    ! grep -E 'org\.apache\.commons\.lang3\.[^ ]+[[:space:]]+not found$' "$dir/jdeps.txt" || exit 1
    awk 'FILENAME==ARGV[1]{changed[$1]=1; print $1; next}
         $2=="->" && ($4=="classes" || $4=="test-classes") {
             sub(/\$.*/, "", $3); sub(/\$.*/, "", $1);
             if ($3 in changed) print $1;
         }' "$dir/changed-prod.txt" "$dir/jdeps.txt" > "$dir/dependencies.txt"
    sort -u "$dir/dependencies.txt" "$dir/dirts-roots.txt" > "$dir/root-candidates.txt"
    comm -12 "$dir/classes.txt" "$dir/root-candidates.txt" > "$dir/expanded-roots.txt"
)

test_maven() (
    mode=$1
    dir=$2
    cache=$3
    shift 3
    rc=0
    maven "$cache" "$@" test > "$dir/$mode.log" 2>&1 || rc=$?
    if [ -d target/surefire-reports ]; then
        mkdir "$dir/$mode-xml"
        cp target/surefire-reports/TEST-*.xml "$dir/$mode-xml/"
    fi
    return "$rc"
)

printf 'fase,ns,rc\n' > /out/tempos.csv
initial=$(cat /out/49.parent)
if time_step inicializacao initialize "$initial" /out/inicializacao /maven-cache; then
    cp /work/state.hashes /out/inicializacao.hashes
fi
for pos in 49 50; do
    dir=/out/$pos
    sha=$(cat "$dir/sha")
    parent=$(cat "/out/$pos.parent")
    fallback=
    if [ -e "$dir/unsupported" ]; then
        fallback=diff_nao_suportado
    elif ! time_step "arvore_reuso_$pos" prepare_target "$pos"; then
        fallback=estado_invalido
    fi
    if [ "$fallback" = estado_invalido ]; then
        mv /work/state "/work/invalid-$pos"
        if time_step "reconstrucao_$pos" initialize "$parent" "$dir/reconstrucao" /maven-cache &&
           time_step "arvore_recuperada_$pos" prepare_target "$pos"; then
            fallback=
        fi
    fi
    if [ -z "$fallback" ]; then
        cd /work/source
        if ! time_step "dirts_$pos" select_dirts "$dir/continuo" /maven-cache ||
           ! time_step "selo_$pos" seal_state "$sha"; then
            fallback=dirts_invalido
        else
            cp /work/state.hashes "$dir/continuo.hashes"
            if ! time_step "inventario_jdeps_$pos" discover "$dir" > "$dir/descoberta.log" 2>&1 ||
               ! time_step "selecao_$pos" validate_output "$dir" "$dir/continuo.excludes" "$dir/continuo.log" ||
               ! time_step "expansao_$pos" expand_roots "$dir"; then
                fallback=selecao_invalida
            fi
        fi
    fi
    if [ ! -f /work/source/pom.xml ]; then
        time_step "arvore_fallback_$pos" unpack "$pos" /work/source
    fi
    cd /work/source
    printf '%s\n' "$fallback" > "$dir/fallback"
    if [ -n "$fallback" ]; then
        time_step "reuso_test_$pos" test_maven reuso "$dir" /maven-cache || true
    elif [ -s "$dir/expanded-roots.txt" ]; then
        tests=$(paste -sd, "$dir/expanded-roots.txt")
        time_step "reuso_test_$pos" test_maven reuso "$dir" /maven-cache "-Dtest=$tests" || true
    fi
    cd /work
    mv /work/state "/work/old-state-$pos"
    mv /work/source /work/state
    if [ -n "$fallback" ]; then rm -f /work/state.sha; fi

    time_step "arvore_t0_$pos" unpack "$pos" "/work/t0-$pos"
    cd "/work/t0-$pos"
    time_step "t0_test_$pos" test_maven t0 "$dir" /t0-cache || true
    cd /work
done

# Controles executados fora dos relógios de produção.
for pos in 49 50; do
    dir=/out/$pos
    parent=$(cat "/out/$pos.parent")
    mkdir "$dir/isolado" "/work/isolado-$pos"
    cd "/work/isolado-$pos"
    time_step "pai_isolado_$pos" unpack "$parent" .
    time_step "dirts_pai_isolado_$pos" select_dirts "$dir/isolado/pai" /controle-cache
    time_step "controle_sem_diff_$pos" select_dirts "$dir/isolado/controle" /controle-cache
    grep -Fx 'DIRTS included: []' "$dir/isolado/controle.log"
    unpack "$pos" .
    time_step "dirts_alvo_isolado_$pos" select_dirts "$dir/isolado/alvo" /controle-cache
    cp "$dir/classes.txt" "$dir/changed-tests.txt" "$dir/isolado/"
    time_step "validacao_isolada_$pos" validate_output "$dir/isolado" "$dir/isolado/alvo.excludes" "$dir/isolado/alvo.log"
    cmp "$dir/dirts-roots.txt" "$dir/isolado/dirts-roots.txt"
done
cd /work/state
sha=$(cat /out/50/sha)
valid_state "$sha"
if valid_state "$(cat /out/50.parent)"; then exit 1; fi
printf 'parent_divergente,rejeitado\n' > /out/falhas.csv
mv .dirts /work/fault-state
if valid_state "$sha"; then exit 1; fi
printf 'estado_ausente,rejeitado\n' >> /out/falhas.csv
mv /work/fault-state .dirts
printf 'teste de adulteracao\n' > .dirts/kan18-fault
if valid_state "$sha"; then exit 1; fi
printf 'estado_adulterado,rejeitado\n' >> /out/falhas.csv
mv /work/state /work/fault-worktree
time_step controle_reconstrucao initialize "$sha" /out/recuperacao /controle-cache
cd /work/state
valid_state "$sha"
printf 'reconstrucao,validada\n' >> /out/falhas.csv
