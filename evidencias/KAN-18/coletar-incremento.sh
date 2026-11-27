# Lote incremental 47–48. As funções do piloto são carregadas pelo preparador.
printf 'fase,ns,rc\n' > /out/tempos.csv
initial=$(cat /out/47.parent)
if time_step inicializacao initialize "$initial" /out/inicializacao /maven-cache; then
    cp /work/state.hashes /out/inicializacao.hashes
fi

for pos in 47 48; do
    dir=/out/$pos
    sha=$(cat "$dir/sha")
    parent=$(cat "/out/$pos.parent")
    fallback=
    continuity=incremental
    if [ -e "$dir/unsupported" ]; then
        fallback=diff_nao_suportado
    elif ! time_step "arvore_reuso_$pos" prepare_target "$pos"; then
        continuity=reconstruido
        mv /work/state "/work/invalid-$pos"
        if ! time_step "reconstrucao_$pos" initialize "$parent" "$dir/reconstrucao" /maven-cache ||
           ! time_step "arvore_recuperada_$pos" prepare_target "$pos"; then
            fallback=estado_invalido
        fi
    fi
    if [ -z "$fallback" ]; then
        cp /work/state.hashes "$dir/estado-pai.hashes"
        cd /work/source
        if ! time_step "dirts_$pos" select_dirts "$dir/continuo" /maven-cache ||
           ! time_step "selo_$pos" seal_state "$sha"; then
            fallback=dirts_invalido
        else
            cp /work/state.hashes "$dir/continuo.hashes"
        fi
    fi
    if [ ! -f /work/source/pom.xml ]; then
        time_step "arvore_fallback_$pos" unpack "$pos" /work/source
    fi
    cd /work/source
    if ! time_step "inventario_jdeps_$pos" discover "$dir" > "$dir/descoberta.log" 2>&1; then
        printf '%s\n' inventario_indisponivel > "$dir/fallback"
        exit 1
    fi
    if [ -z "$fallback" ]; then
        if ! time_step "selecao_$pos" validate_output "$dir" "$dir/continuo.excludes" "$dir/continuo.log" ||
           ! time_step "expansao_$pos" expand_roots "$dir"; then
            fallback=selecao_invalida
        fi
    fi
    printf '%s\n' "$fallback" > "$dir/fallback"
    if [ -n "$fallback" ]; then
        continuity=fallback
        cp "$dir/classes.txt" "$dir/expanded-roots.txt"
        rm -f /work/state.sha
    fi
    printf '%s\n' "$continuity" > "$dir/continuidade"
    cd /work
    mv /work/state "/work/old-state-$pos"
    mv /work/source /work/state
done

for pos in 47 48; do
    dir=/out/$pos
    parent=$(cat "/out/$pos.parent")
    if [ -s "$dir/fallback" ] && grep -q '[^[:space:]]' "$dir/fallback"; then
        printf '%s\n' fallback_integral > "$dir/controle.status"
        continue
    fi
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
    printf '%s\n' equivalente > "$dir/controle.status"
done
