FROM kartoza/postgis:13.0

#ENV POSTGRES_USER ilmakalu
#ENV POSTGRES_PASSWORD ilmakalu
#ENV POSTGRES_DB ilmakalu
ARG MUNICIPALITIES
ENV MUNICIPALITIES ${MUNICIPALITIES}
RUN echo $MUNICIPALITIES

COPY init/00-init-user-db.sh /docker-entrypoint-initdb.d/
COPY init/01-init.sh /docker-entrypoint-initdb.d/
COPY init/02-init.sh /docker-entrypoint-initdb.d/
COPY init/03-init.sh /docker-entrypoint-initdb.d/
#COPY ./dump/emissiontest_stripped.sql /docker-entrypoint-initdb.d/
