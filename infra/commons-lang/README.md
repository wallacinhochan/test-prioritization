# Executar uma revisão do Apache Commons Lang

Na raiz do repositório de pesquisa, use PowerShell 7.3 ou superior, Git e um daemon Docker com contêineres Linux/amd64. O bootstrap precisa de acesso ao Docker Hub e ao Maven Central. Obter o clone do Commons Lang exige acesso ao GitHub.

## Bootstrap

```powershell
docker build --platform linux/amd64 --tag test-prioritization/commons-lang:kan13 ./infra/commons-lang
if ($LASTEXITCODE -ne 0) { throw 'Falha ao construir a imagem da KAN-13.' }

$fonte = Join-Path ([IO.Path]::GetTempPath()) ('kan13-commons-lang-' + [guid]::NewGuid())
git clone --bare --single-branch --no-tags --depth 101 --branch rel/commons-lang-3.20.0 https://github.com/apache/commons-lang.git $fonte
if ($LASTEXITCODE -ne 0) { throw 'Falha ao obter o Commons Lang.' }
```

Também é possível usar um clone existente com os objetos da revisão. O executor resolve o SHA completo para um commit Git e exporta a árvore versionada com `git archive`. O contêiner recebe apenas essa árvore. O build roda sem o histórico Git, sem arquivos locais do checkout e sem montar o diretório pessoal ou a configuração Maven do host.

A imagem fixa o Eclipse Temurin 21.0.11 por digest e verifica a distribuição Maven 3.9.11 com o SHA-512 publicado pelo Apache. O contêiner recebe `TZ=UTC` e o Maven recebe `-Duser.timezone=UTC`. [Checksum do Apache](https://archive.apache.org/dist/maven/maven-3/3.9.11/binaries/apache-maven-3.9.11-bin.tar.gz.sha512)

## Execução

```powershell
./infra/commons-lang/executar.ps1 -Fonte $fonte -Sha 598dfc163b8b410fb3bb8794521206ec8dcec82a -Saida ./resultados/KAN-13
$LASTEXITCODE
```

O padrão é `mvn clean test`. Para executar um método específico, acrescente `-Teste 'NomeDaClasse#nomeDoMetodo'`. O cache Maven começa vazio em cada contêiner, em `/maven-cache`. Cada rodada resolve as dependências em rede. A duração de ponta a ponta inclui essa resolução, o preparo do contêiner e a cópia dos relatórios.

Cada chamada cria `<saída>/<sha>/<id-da-execucao>/` e imprime o caminho. O arquivo `ambiente.json` registra o SHA confirmado, o ID e a base da imagem, as versões efetivas, o fuso configurado, o cache, os tempos e os códigos de saída. O `maven.log` preserva o comando e a saída do processo. Quando o Surefire produz relatórios, o executor os copia para `surefire/` inclusive se o Maven terminar com falha. Se a cópia falhar, o ID do contêiner fica disponível no JSON para recuperar os arquivos com `docker cp`.

O executor devolve o código do Maven após coletar as saídas. Falhas do executor, de infraestrutura ou ausência de XML após sucesso do Maven retornam 1 e registram a causa em `ambiente.json`. Consulte os [pilotos da KAN-13](../../evidencias/KAN-13/README.md) para os comandos por SHA e a localização dos XML.
