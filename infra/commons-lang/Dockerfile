ARG BASE=eclipse-temurin:21.0.11_10-jdk-noble@sha256:d435e5eb685fa668f894f20710bfc12608ec65f8509fec480da3f278f2382081
FROM ${BASE} AS maven
ADD https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.11/apache-maven-3.9.11-bin.tar.gz /tmp/maven.tar.gz
RUN echo 'bcfe4fe305c962ace56ac7b5fc7a08b87d5abd8b7e89027ab251069faebee516b0ded8961445d6d91ec1985dfe30f8153268843c89aa392733d1a3ec956c9978  /tmp/maven.tar.gz' | sha512sum -c - \
    && mkdir -p /opt/maven \
    && tar -xzf /tmp/maven.tar.gz --strip-components=1 -C /opt/maven

FROM ${BASE}
ARG BASE
LABEL org.opencontainers.image.base.name="${BASE}"
COPY --from=maven /opt/maven /opt/maven
ENV TZ=UTC \
    PATH="/opt/maven/bin:${PATH}"
RUN test "$(javac -version)" = 'javac 21.0.11' \
    && mvn --version | sed -n '1p' | grep -F 'Apache Maven 3.9.11'
