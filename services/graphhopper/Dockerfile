FROM openjdk:11

ARG COUNTRY

RUN wget http://download.geofabrik.de/europe/$COUNTRY-latest.osm.pbf \
    https://github.com/graphhopper/graphhopper/releases/download/5.3/graphhopper-web-5.3.jar \
    https://raw.githubusercontent.com/graphhopper/graphhopper/5.x/config-example.yml
RUN cat config-example.yml | sed "s/localhost/graphhopper-$COUNTRY/;" | sed -re '/graphhopper:,*/a \ \ index.max_region_search: 10000' >> config-example-edited.yml
ENTRYPOINT java -Ddw.graphhopper.datareader.file=$COUNTRY-latest.osm.pbf -jar *.jar server config-example-edited.yml
