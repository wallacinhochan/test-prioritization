# Cada alvo recebe estado novo e selado do próprio primeiro pai.
printf 'fase,ns,rc\n' > /out/tempos.csv
for pos in 15 42; do
    dir=/out/$pos
    sha=$(cat "$dir/sha")
    parent=$(cat "/out/$pos.parent")
    fallback=
    if [ -e "$dir/unsupported" ]; then
        fallback=diff_nao_suportado
    elif ! time_step "inicializacao_$pos" initialize "$parent" "$dir/pai" /maven-cache; then
        fallback=estado_indisponivel
    else
        cp /work/state.hashes "$dir/estado-pai.hashes"
        mkdir "/work/controle-$pos"
        cp -a /work/state/. "/work/controle-$pos/"
        if ! time_step "arvore_reuso_$pos" prepare_target "$pos"; then
            fallback=estado_invalido
        else
            cd /work/source
            if ! time_step "dirts_$pos" select_dirts "$dir/continuo" /maven-cache ||
               ! time_step "selo_$pos" seal_state "$sha"; then
                fallback=dirts_invalido
            else
                cp /work/state.hashes "$dir/continuo.hashes"
            fi
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
        cp "$dir/classes.txt" "$dir/expanded-roots.txt"
        printf '%s\n' fallback_integral > "$dir/continuidade"
    else
        printf '%s\n' reancorado_primeiro_pai > "$dir/continuidade"
    fi
    cd /work
    if [ -d state ]; then mv state "antigo-$pos"; fi
    mv source "alvo-$pos"
    rm -f /work/state.sha /work/state.hashes
done

for pos in 15 42; do
    dir=/out/$pos
    if grep -q '[^[:space:]]' "$dir/fallback"; then
        printf '%s\n' fallback_integral > "$dir/controle.status"
        continue
    fi
    cd "/work/controle-$pos"
    state_files > "$dir/controle-estado-pai.hashes"
    cmp "$dir/estado-pai.hashes" "$dir/controle-estado-pai.hashes"
    if time_step "controle_sem_diff_$pos" select_dirts "$dir/controle" /controle-cache &&
       grep -Fx 'DIRTS included: []' "$dir/controle.log"; then
        printf '%s\n' zero_sem_diff > "$dir/controle.status"
    else
        printf '%s\n' controle_nao_zero_relocalizado > "$dir/controle.status"
        break
    fi
done
