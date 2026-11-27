# Reproduz o controle e a seleção com o pai e o alvo no mesmo diretório.
printf 'fase,ns,rc\n' > /out/tempos.csv
for pos in 15 42; do
    dir=/out/$pos
    parent=$(cat "/out/$pos.parent")
    mkdir "/work/isolado-$pos"
    cd "/work/isolado-$pos"
    time_step "arvore_isolada_$pos" unpack "$parent" .
    if ! time_step "pai_isolado_$pos" select_dirts "$dir/pai" /controle-cache; then
        printf '%s\n' pai_invalido > "$dir/status"
        continue
    fi
    state_files > "$dir/estado-pai.hashes"
    cp -a .dirts "/work/estado-original-$pos"
    if time_step "controle_sem_diff_$pos" select_dirts "$dir/controle" /controle-cache &&
       grep -Fx 'DIRTS included: []' "$dir/controle.log"; then
        printf '%s\n' zero_sem_diff > "$dir/controle.status"
    else
        printf '%s\n' controle_nao_zero > "$dir/controle.status"
    fi
    mv .dirts "/work/estado-controle-$pos"
    mv "/work/estado-original-$pos" .dirts
    state_files > "$dir/estado-restaurado.hashes"
    cmp "$dir/estado-pai.hashes" "$dir/estado-restaurado.hashes"
    unpack "$pos" .
    if time_step "alvo_isolado_$pos" select_dirts "$dir/alvo" /controle-cache &&
       time_step "validacao_isolada_$pos" validate_output "$dir" "$dir/alvo.excludes" "$dir/alvo.log"; then
        printf '%s\n' alvo_validado > "$dir/status"
    else
        printf '%s\n' alvo_invalido > "$dir/status"
    fi
done
