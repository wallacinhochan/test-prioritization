set -eu
tar -xf /entrada/fonte.tar
java -version
mvn --version
mvn_t1() {
  mvn --batch-mode --no-transfer-progress -Dstyle.color=never -Duser.timezone=UTC \
    -Dmaven.repo.local=/maven-cache "$@"
}
mvn_t1 clean test-compile \
  org.apache.maven.plugins:maven-dependency-plugin:3.9.0:build-classpath \
  org.apache.maven.plugins:maven-help-plugin:3.5.1:effective-pom \
  -DincludeScope=test -Dmdep.outputFile=/entrada/dependencias.txt -Doutput=/entrada/pom-efetivo.xml
deps=$(cat /entrada/dependencias.txt)
engine=$(printf '%s\n' "$deps" | tr ':' '\n' | grep '/junit-platform-engine/[^/]*/junit-platform-engine-[^/]*\.jar$')
test "$(printf '%s\n' "$engine" | wc -l)" = 1
platform=$(basename "$(dirname "$engine")")
mvn_t1 org.apache.maven.plugins:maven-dependency-plugin:3.9.0:get \
  "-Dartifact=org.junit.platform:junit-platform-launcher:$platform" -Dtransitive=false
launcher="/maven-cache/org/junit/platform/junit-platform-launcher/$platform/junit-platform-launcher-$platform.jar"
cp="target/test-classes:target/classes:$deps:$launcher"
printf '%s\n' "$cp" > /entrada/classpath.txt
find target/test-classes -type f -name '*Test.class' ! -name '*$*' |
  sed 's#^target/test-classes/##; s#\.class$##; s#/#.#g' | LC_ALL=C sort > /entrada/classes.txt
java -Duser.timezone=UTC -cp "$cp" /entrada/DescobertaT0.java /entrada/classes.txt /entrada/metodos.tsv
jdeps --multi-release 21 -verbose:class -filter:none -cp "$cp" target/classes target/test-classes > /entrada/jdeps.txt
