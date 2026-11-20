set -eu
tar -xf /entrada/fonte.tar
mkdir /maven-cache
mvn --batch-mode --no-transfer-progress -Dstyle.color=never \
  -Dmaven.repo.local=/maven-cache -Duser.timezone=UTC clean test-compile
classpath=$(cat /entrada/classpath.txt)
old_ifs=$IFS
IFS=:
for item in $classpath; do
  test -e "$item" || { printf 'Classpath ausente: %s\n' "$item" >&2; exit 1; }
done
IFS=$old_ifs
java -Duser.timezone=UTC \
  -cp "$classpath" /entrada/DescobertaT0.java /entrada/classes.txt /entrada/metodos.tsv
