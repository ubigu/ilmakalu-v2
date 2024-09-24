"""Create functions

Revision ID: caf70a92d09d
Revises: 549fab520a40
Create Date: 2024-09-24 14:32:15.455680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'caf70a92d09d'
down_revision: Union[str, None] = '549fab520a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA functions")
    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_GridProcessing(
            municipalities integer[],
            aoi regclass, -- Area of interest
            calculationYear integer,
            baseYear integer,
            km2hm2 real default 1.25,
            targetYear integer default null,
            plan_areas regclass default null,
            plan_centers regclass default null,
            plan_transit regclass default null
        )

        RETURNS TABLE (
            geom geometry(MultiPolygon),
            xyind varchar,
            mun int,
            zone bigint,
            maa_ha real,
            centdist smallint,
            pop smallint,
            employ smallint,
            k_ap_ala int,
            k_ar_ala int,
            k_ak_ala int,
            k_muu_ala int,
            k_tp_yht integer,
            k_poistuma int,
            alueteho real,
            alueteho_muutos real
        ) AS $$

        DECLARE
            demolitionsExist boolean;
            startYearExists boolean;
            endYearExists boolean;
            completionYearExists boolean;
            typeExists boolean;
            kapaExists boolean;
            pubtrans_zones int[] default ARRAY[3,12,41, 99911, 99921, 99931, 99941, 99951, 99961, 99901, 99912, 99922, 99932, 99942, 99952, 99962, 99902, 99913, 99923, 99933, 99943, 99953, 99963, 99903];
        BEGIN

        IF calculationYear = baseYear OR targetYear IS NULL OR plan_areas IS NULL THEN
            /* Creating a temporary table with e.g. YKR population and workplace data */
            EXECUTE format(
            'CREATE TEMP TABLE IF NOT EXISTS grid AS SELECT
                DISTINCT ON (grid.xyind, grid."WKT")
                grid."WKT" :: geometry(MultiPolygon),
                grid.xyind :: varchar(13),
                grid.mun :: int,
                grid.zone :: bigint,
                clc.maa_ha :: real,
                grid.centdist :: smallint,
                coalesce(pop.v_yht, 0) :: smallint AS pop,
                coalesce(employ.tp_yht, 0) :: smallint AS employ,
                0 :: int AS k_ap_ala,
                0 :: int AS k_ar_ala,
                0 :: int AS k_ak_ala,
                0 :: int AS k_muu_ala,
                0 :: int AS k_tp_yht,
                0 :: int AS k_poistuma,
                (((coalesce(pop.v_yht, 0) + coalesce(employ.tp_yht, 0)) * 50 * 1.25) :: real / 62500) :: real AS alueteho,
                0 :: real AS alueteho_muutos
                FROM delineations.grid grid
                LEFT JOIN grid_globals.pop pop
                    ON grid.xyind :: varchar = pop.xyind :: varchar
                    AND grid.mun :: int = pop.kunta :: int
                LEFT JOIN grid_globals.employ employ
                    ON grid.xyind :: varchar = employ.xyind :: varchar
                    AND grid.mun :: int = employ.kunta :: int
                LEFT JOIN grid_globals.clc clc 
                    ON grid.xyind :: varchar = clc.xyind :: varchar
                WHERE grid.mun = ANY(%1$L);'
            , municipalities);
            CREATE INDEX ON grid USING GIST ("WKT");
            CREATE INDEX ON grid (xyind);
            CREATE INDEX ON grid (zone);
            CREATE INDEX ON grid (mun);

            IF aoi IS NOT NULL THEN
                EXECUTE format(
                    'DELETE FROM grid
                        WHERE NOT ST_Intersects(st_centroid(grid.geom),
                        (SELECT st_union(bounds.geom) FROM %s bounds))', aoi);
            END IF;

            END IF;

            IF targetYear IS NOT NULL AND plan_areas IS NOT NULL THEN

                EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS kt AS SELECT * FROM %s', plan_areas);
                    ALTER TABLE kt
                        ALTER COLUMN geom TYPE geometry(MultiPolygon)
                            USING ST_Multi(ST_force2d(ST_Transform(geom)));
                    /* Calculate plan surface areas */
                    ALTER TABLE kt
                        ADD COLUMN IF NOT EXISTS area_ha real default 0;
                        UPDATE kt SET area_ha = ST_AREA(kt.geom)/10000;
                    CREATE INDEX ON kt USING GIST (geom);

                IF plan_centers IS NOT NULL THEN
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS kv AS SELECT * FROM %s', plan_centers);
                    ALTER TABLE kv
                        ALTER COLUMN geom TYPE geometry(Point, 3067)
                            USING ST_force2d(ST_Transform(geom, 3067));
                    CREATE INDEX ON kv USING GIST (geom);
                END IF;

                IF plan_transit IS NOT NULL THEN
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS pubtrans AS SELECT * FROM %s', plan_transit);
                    ALTER TABLE pubtrans
                        ALTER COLUMN geom TYPE geometry(Point, 3067)
                            USING ST_force2d(ST_Transform(geom, 3067));
                    CREATE INDEX ON pubtrans USING GIST (geom);
                END IF;

                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_poistuma') INTO demolitionsExist;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_aloitusv') INTO startYearExists;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_valmisv') INTO endYearExists;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'year_completion') INTO completionYearExists;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'type') INTO typeExists;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_ap_ala') INTO kapaExists;

                ALTER TABLE kt ADD COLUMN IF NOT EXISTS k_tp_yht int DEFAULT 0;

                /* Lasketaan käyttötarkoitusalueilta numeeriset arvot grid-ruuduille. */
                IF startYearExists AND endYearExists THEN
                    UPDATE grid
                    SET k_ap_ala = (
                        SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ap_ala <= 0 THEN 0 ELSE kt.k_ap_ala / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) END))
                        FROM kt
                        WHERE ST_Intersects(grid.geom, kt.geom)
                        AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear
                        AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                    ), k_ar_ala = (
                        SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) * (CASE WHEN kt.k_ar_ala <= 0 THEN 0 ELSE kt.k_ar_ala / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) END))
                        FROM kt
                        WHERE ST_Intersects(grid.geom, kt.geom)
                        AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear
                        AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                    ), k_ak_ala = (
                        SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ak_ala <= 0 THEN 0 ELSE kt.k_ak_ala / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) END))
                        FROM kt
                        WHERE ST_Intersects(grid.geom, kt.geom)
                        AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear
                        AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                    ), k_muu_ala = (
                        SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_muu_ala <= 0 THEN 0 ELSE kt.k_muu_ala / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) END))
                        FROM kt
                        WHERE ST_Intersects(grid.geom, kt.geom)
                        AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear
                        AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                    ), k_tp_yht = (
                        SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) * kt.k_tp_yht / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1))
                        FROM kt WHERE ST_Intersects(grid.geom, kt.geom) AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                    );
                        IF demolitionsExist THEN
                            UPDATE grid SET k_poistuma = (
                                SELECT SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / (kt.area_ha * 10000) *
                                (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) * (-1) ELSE kt.k_poistuma / (COALESCE(kt.k_valmisv,targetYear) - COALESCE(kt.k_aloitusv,baseYear) + 1) END))
                                FROM kt WHERE ST_Intersects(grid.geom, kt.geom) AND COALESCE(kt.k_aloitusv,baseYear) <= calculationYear AND COALESCE(kt.k_valmisv,targetYear) >= calculationYear
                            );
                        ELSE
                            /* DUMMY for default demolition rate */
                            UPDATE grid SET k_poistuma = 999999;
                        END IF;

                ELSIF completionYearExists AND typeExists AND NOT kapaExists THEN
                
                UPDATE grid
                    SET k_ap_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.kem2 <= 0 THEN 0 ELSE kt.kem2 END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.type IN ('ao','ap')
                            AND kt.year_completion = calculationYear
                    ), k_ar_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.kem2 <= 0 THEN 0 ELSE kt.kem2 END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.type IN ('ar','kr')
                            AND kt.year_completion = calculationYear
                    ), k_ak_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.kem2 <= 0 THEN 0 ELSE kt.kem2 END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.type IN ('ak','c')
                            AND kt.year_completion = calculationYear
                    ), k_muu_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.kem2 <= 0 THEN 0 ELSE kt.kem2 END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.type IN ('tp','muu')
                            AND kt.year_completion = calculationYear
                    ), k_tp_yht = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_tp_yht <= 0 THEN 0 ELSE kt.k_tp_yht END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    );

                    IF demolitionsExist THEN
                        UPDATE grid SET k_poistuma = (
                            SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                                (kt.area_ha * 10000) *
                                (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
                            FROM kt
                                WHERE ST_Intersects(grid.geom, kt.geom)
                                AND baseYear <= calculationYear
                        );
                    ELSE
                        UPDATE grid SET k_poistuma = 999999;
                    END IF;

                ELSIF completionYearExists AND NOT typeExists AND kapaExists THEN
                    
                UPDATE grid
                    SET k_ap_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ap_ala <= 0 THEN 0 ELSE kt.k_ap_ala END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.year_completion = calculationYear
                    ), k_ar_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ar_ala <= 0 THEN 0 ELSE kt.k_ar_ala END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.year_completion = calculationYear
                    ), k_ak_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ak_ala <= 0 THEN 0 ELSE kt.k_ak_ala END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.year_completion = calculationYear
                    ), k_muu_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_muu_ala <= 0 THEN 0 ELSE kt.k_muu_ala END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND kt.year_completion = calculationYear
                    ), k_tp_yht = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_tp_yht <= 0 THEN 0 ELSE kt.k_tp_yht END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    );

                    IF demolitionsExist THEN
                        UPDATE grid SET k_poistuma = (
                            SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                                (kt.area_ha * 10000) *
                                (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
                            FROM kt
                                WHERE ST_Intersects(grid.geom, kt.geom)
                                AND baseYear <= calculationYear
                        );
                    ELSE
                        UPDATE grid SET k_poistuma = 999999;
                    END IF;

                ELSE 
                    UPDATE grid
                    SET k_ap_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ap_ala <= 0 THEN 0 ELSE kt.k_ap_ala / (targetYear - baseYear + 1) END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    ), k_ar_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ar_ala <= 0 THEN 0 ELSE kt.k_ar_ala / (targetYear - baseYear + 1) END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    ), k_ak_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_ak_ala <= 0 THEN 0 ELSE kt.k_ak_ala / (targetYear - baseYear + 1) END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    ), k_muu_ala = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (CASE WHEN kt.k_muu_ala <= 0 THEN 0 ELSE kt.k_muu_ala / (targetYear - baseYear + 1) END)), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    ), k_tp_yht = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            (kt.area_ha * 10000) *
                            (kt.k_tp_yht / (targetYear - baseYear + 1))), 0)
                        FROM kt
                            WHERE ST_Intersects(grid.geom, kt.geom)
                            AND baseYear <= calculationYear
                    );
                        IF demolitionsExist THEN
                            UPDATE grid SET k_poistuma = (
                                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                                    (kt.area_ha * 10000) *
                                    (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
                                FROM kt
                                    WHERE ST_Intersects(grid.geom, kt.geom)
                                    AND baseYear <= calculationYear
                            );
                        ELSE
                            UPDATE grid SET k_poistuma = 999999;
                        END IF;
                END IF;

                /*  Haetaan ruudukolle nykyisen maanpeitteen mukaiset maapinta-alatiedot.
                Päivitetään mahdolliset ranta- ja vesialueiden täytöt maa_ha -sarakkeeseen.
                Maa_ha -arvoksi täytöille asetetaan 5.9, joka on rakennettujen ruutujen keskimääräinen maa-ala.
                Tässä oletetaan, että jos alle 20% ruudusta (1.25 ha) on nykyisin maata, ja alueelle rakennetaan vuodessa yli 200 neliötä kerrostaloja,
                tehdään täyttöjä (laskettu 20%lla keskimääräisestä n. 10000 m2 rakennusten pohja-alasta per ruutu, jaettuna 10 v. toteutusajalle).
                Lasketaan samalla aluetehokkuuden muutos ja päivitetään aluetehokkuus. */

                UPDATE grid g
                    SET maa_ha = 5.9
                    WHERE g.k_ak_ala >= 200;
                UPDATE grid
                    SET alueteho_muutos = CASE WHEN
                        grid.maa_ha != 0
                        THEN
                        (COALESCE(grid.k_ap_ala,0) + COALESCE(grid.k_ar_ala,0) + COALESCE(grid.k_ak_ala,0) + COALESCE(grid.k_muu_ala,0)) / (10000 * grid.maa_ha)
                        ELSE 0 END;
                UPDATE grid
                    SET alueteho = CASE WHEN
                        COALESCE(grid.alueteho,0) + COALESCE(grid.alueteho_muutos,0) > 0
                        THEN
                        COALESCE(grid.alueteho,0) + COALESCE(grid.alueteho_muutos,0)
                        ELSE 0 END;

                /* Lasketaan väestön lisäys asumisväljyyden avulla. 1.25 = kerroin kerrosalasta huoneistoalaksi. */
                UPDATE grid
                SET pop = grid.pop +
                    (   COALESCE(grid.k_ap_ala, 0)::real / COALESCE(bo.erpien,38)::real +
                        COALESCE(grid.k_ar_ala, 0)::real / COALESCE(bo.rivita,35.5)::real +
                        COALESCE(grid.k_ak_ala, 0)::real / COALESCE(bo.askert,35)::real
                    ) / COALESCE(km2hm2, 1.25)::real
                FROM built.occupancy bo
                    WHERE bo.year = calculationYear
                    AND bo.mun::int = grid.mun::int;

                UPDATE grid SET employ = grid.employ + COALESCE(grid.k_tp_yht,0);
                
                /*  KESKUSVERKON PÄIVITTÄMINEN
                Luodaan väliaikainen taso valtakunnallisesta keskusta-alueaineistosta
                Poistetaan ylimääräiset / virheelliset keskustat
                Muutetaan valtakunnallinen keskusta-alueaineisto keskipisteiksi (Point). */

                IF calculationYear = baseYear THEN
                    /* Crop the national centroid data to cover only the nearest centers to AOI */
                    /** TESTED OK **/
                    CREATE TEMP TABLE IF NOT EXISTS centralnetwork AS
                        SELECT DISTINCT ON (p2.geom) p2.* FROM
                        (SELECT p1.xyind as g1,
                            (SELECT p.id
                                FROM delineations.centroids AS p
                                WHERE p1.xyind <> p.id::varchar
                                ORDER BY p.geom <#> p1.geom ASC LIMIT 1
                            ) AS g2
                                FROM grid AS p1
                                OFFSET 0
                        ) AS q
                        JOIN grid AS p1
                            ON q.g1=p1.xyind
                        JOIN delineations.centroids AS p2
                            ON q.g2=p2.id;
                END IF;

                /* Add new centers to the central network only if the user has added such! */
                /** TESTED OK */
                IF plan_centers IS NOT NULL THEN
                    INSERT INTO centralnetwork
                    SELECT (SELECT MAX(k.id) FROM centralnetwork k) + row_number() over (order by plan.geom desc),
                        st_force2d((ST_DUMP(plan.geom)).geom) as geom,
                        k_ktyyp AS keskustyyp,
                        k_knimi AS keskusnimi
                    FROM kv plan
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM centralnetwork centers
                        WHERE ST_DWithin(plan.geom, centers.geom, 1500)
                    ) AND plan.k_ktyyp = 'Kaupunkiseudun iso alakeskus'
                    AND ((COALESCE(plan.k_kvalmv,targetYear) + COALESCE(plan.k_kalkuv,baseYear))/2 <= calculationYear
                        OR plan.k_kvalmv <= calculationYear);
                END IF;

                CREATE INDEX ON centralnetwork USING GIST (geom);

                /* Update closest distance to centroids into grid data. */
                /** TESTED OK */
                UPDATE grid
                SET centdist = sq2.centdist FROM
                    (SELECT grid.xyind, center.centdist
                    FROM grid
                    CROSS JOIN LATERAL
                        (SELECT ST_Distance(ST_CENTROID(centers.geom), grid.geom)/1000 AS centdist
                            FROM centralnetwork centers
                        WHERE centers.keskustyyp != 'Kaupunkiseudun pieni alakeskus'
                        ORDER BY grid.geom <#> centers.geom
                    LIMIT 1) AS center) as sq2
                WHERE grid.xyind = sq2.xyind;

                /* YHDYSKUNTARAKENTEEN VYÖHYKKEIDEN PÄIVITTÄMINEN */
                -- Keskustan jalankulkuvyöhyke
                /** Tested OK */
                CREATE TEMP TABLE IF NOT EXISTS grid_new AS
                SELECT * FROM
                (SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                CASE WHEN left(grid.zone::varchar,6)::int 
                    IN (999112, 999212, 999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                        THEN concat('99911',right(grid.zone::varchar,4))::bigint
                WHEN left(grid.zone::varchar,6)::int
                    IN (999122, 999222, 999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                        THEN concat('99912',right(grid.zone::varchar,4))::bigint
                ELSE 1 END AS zone
                FROM grid
                /* Search for grid cells within current UZ central areas delineation */
                /* and those cells that touch the current centers - have to use d_within for fastest approximation, st_touches doesn't work due to false DE-9IM relations */
                WHERE (grid.zone = 1 OR LEFT(grid.zone::varchar, 6)::int IN (999112, 999122)) OR (grid.maa_ha != 0 AND
                    st_dwithin(grid.geom, 
                        (SELECT st_union(grid.geom)
                            FROM grid
                            WHERE (grid.zone = 1 OR LEFT(grid.zone::varchar, 6)::int IN (999112, 999122))
                        ), 25))
                    /* Main centers must be within 1.5 km from core */
                    AND st_dwithin(grid.geom,
                        (SELECT centralnetwork.geom
                            FROM centralnetwork
                            WHERE centralnetwork.keskustyyp = 'Kaupunkiseudun keskusta'
                        ), 1500)
                    AND (grid.alueteho > 0.05 AND grid.employ > 0)
                    AND (grid.alueteho > 0.2 AND grid.pop >= 100 AND grid.employ > 0)
                    /* Select only edge neighbours, no corner touchers */
                    /* we have to use a buffer + area based intersection trick due to topological errors */
                    AND st_area(
                        st_intersection(
                            grid.geom,
                            st_buffer(
                                (SELECT st_union(grid.geom)
                                    FROM grid
                                    WHERE (grid.zone = 1 OR LEFT(grid.zone::varchar, 6)::int IN (999112, 999122))
                                ), 1)
                        )) > 1
                    AND (0.014028 * grid.pop + 0.821276 * grid.employ -3.67) > 10) uz1;
                    
                
                /* Olemassaolevien alakeskusten reunojen kasvatus */
                /** Tested OK */
                INSERT INTO grid_new
                SELECT * FROM
                (SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind, 
                CASE WHEN grid.zone IN (3,4,5, 81, 82, 83 ,84 ,85 ,86 ,87 ) THEN 10
                WHEN left(grid.zone::varchar,6)::int 
                    IN (999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                        THEN concat('999101',right(grid.zone::varchar,4))::bigint
                WHEN left(grid.zone::varchar,6)::int
                    IN (999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                        THEN concat('999102',right(grid.zone::varchar,4))::bigint
                ELSE grid.zone END AS zone
                FROM grid, centralnetwork
                /* Search for grid cells within current UZ central areas delineation */
                WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new) AND (grid.zone IN (10,11,12,6,837101) OR LEFT(grid.zone::varchar, 6)::int
                    IN (999101, 999102, 999111, 999112, 999121, 999122, 999612, 999622)) OR (grid.maa_ha != 0
                    AND st_dwithin(grid.geom, 
                        (SELECT st_union(grid.geom)
                            FROM grid
                            WHERE (grid.zone IN (10,11,12,6,837101) OR LEFT(grid.zone::varchar, 6)::int IN (999101, 999102, 999111, 999112, 999121, 999122, 999612, 999622))
                        ), 25)
                    AND (grid.alueteho > 0.05 AND grid.employ > 0)
                    AND (grid.alueteho > 0.2 AND grid.pop >= 100 AND grid.employ > 0))
                    /* Select only edge neighbours, no corner touchers */
                    /* we have to use a buffer + area based intersection trick due to topological errors */
                    AND st_area(
                        st_intersection(
                            grid.geom,
                            st_buffer(
                                (SELECT st_union(grid.geom)
                                    FROM grid
                                    WHERE (grid.zone = 1 OR LEFT(grid.zone::varchar, 6)::int IN (999112, 999122))
                                ), 1)
                        )) > 1
                    AND (0.014028 * grid.pop + 0.821276 * grid.employ -3.67) > 10) uz10;
                
                INSERT INTO grid_new
                SELECT * FROM
                    (SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                    CASE WHEN grid.zone IN (3,4,5, 81, 82, 83 ,84 ,85 ,86 ,87 ) THEN 10
                        WHEN left(grid.zone::varchar,6)::int 
                            IN (999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                                THEN concat('999101',right(grid.zone::varchar,4))::bigint
                        WHEN left(grid.zone::varchar,6)::int
                            IN (999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                                THEN concat('999102',right(grid.zone::varchar,4))::bigint
                        ELSE grid.zone END AS zone
                    FROM grid, centralnetwork
                    WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new) AND grid.maa_ha != 0 
                    AND (st_dwithin(grid.geom, centralnetwork.geom, 250) AND centralnetwork.keskustyyp = 'Kaupunkiseudun iso alakeskus')
                    OR (st_dwithin(grid.geom, centralnetwork.geom, 500) AND centralnetwork.keskustyyp = 'Kaupunkiseudun iso alakeskus'
                        AND (grid.alueteho > 0.05 AND grid.employ > 0)
                    AND (grid.alueteho > 0.2 AND grid.pop >= 100 AND grid.employ > 0))
                    ) uz10new;

                CREATE INDEX ON grid_new USING GIST (geom);

                /* Erityistapaukset */
                /** Tested OK */
                UPDATE grid_new SET zone = 6 WHERE grid_new.zone IN (837101, 10) AND st_dwithin(grid_new.geom,
                        (SELECT centralnetwork.geom FROM centralnetwork WHERE centralnetwork.keskusnimi = 'Hervanta'), 2000);

                /* Keskustan reunavyöhykkeet */
                /** Tested OK */
                INSERT INTO grid_new
                    SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                    CASE WHEN grid.zone IN (3, 4, 5, 81, 82, 83 ,84 ,85 ,86 ,87 ) THEN 2
                    WHEN left(grid.zone::varchar,6)::int
                    IN (999112, 999212, 999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                        THEN concat('99921',right(grid.zone::varchar,4))::bigint
                    WHEN left(grid.zone::varchar,6)::int
                    IN (999122, 999222, 999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                        THEN concat('99922',right(grid.zone::varchar,4))::bigint
                    ELSE grid.zone END AS zone
                    FROM grid, grid_new
                    WHERE
                        grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new) AND st_dwithin(st_centroid(grid.geom), grid_new.geom,1000)
                        AND ((grid_new.zone = 1 OR left(grid_new.zone::varchar,6)::int IN (999112, 999122))
                        AND (grid.maa_ha/6.25 > 0.1 OR grid.pop > 0 OR grid.employ > 0))
                        OR grid.zone = 2;
                
                /* JOUKKOLIIKENNEVYÖHYKKEET */
                /* Lasketaan ensin joli-vyöhykkeiden määrittelyyn väestön ja työpaikkojen naapuruussummat (k=9). */
                /** Tested OK */
                ALTER TABLE grid 
                    ADD COLUMN IF NOT EXISTS pop_nn real,
                    ADD COLUMN IF NOT EXISTS employ_nn real;
                UPDATE grid AS targetgrid
                    SET pop_nn = n.pop_nn, employ_nn = n.employ_nn
                    FROM (SELECT DISTINCT ON (nn.xyind) nn.xyind, nn.geom,
                        SUM(COALESCE(grid.pop,0)) OVER (PARTITION BY nn.xyind) AS pop_nn,
                        SUM(COALESCE(grid.employ,0)) OVER (PARTITION BY nn.xyind) AS employ_nn
                    FROM grid
                    CROSS JOIN LATERAL (
                            SELECT sqgrid.xyind, sqgrid.geom
                            FROM grid sqgrid ORDER BY sqgrid.geom <#> grid.geom
                            LIMIT 9
                        ) AS nn
                    ) AS n
                WHERE targetgrid.xyind = n.xyind;

                /* Intensiiviset joukkoliikennevyöhykkeet - uudet raideliikenteen pysäkin/asemanseudut */
                /** Tested OK */
                INSERT INTO grid_new
                    SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind, grid.zone
                    FROM grid WHERE (grid.zone = 3
                        OR LEFT(grid.zone::varchar, 3) = '999' AND LEFT(RIGHT(grid.zone::varchar, 5),1)::int IN (1, 2))
                    AND grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new);

                /** Pitää miettiä miten bussien ja päällekkäisten kohteiden kanssa toimitaan */
                IF plan_transit IS NOT NULL THEN
                    INSERT INTO grid_new
                        SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                        CONCAT('999',
                            CASE WHEN grid.zone IN (1,2,3,4,5,6) THEN grid.zone::varchar
                                WHEN grid.zone IN (12,41,81) THEN '3'
                                WHEN grid.zone IN (11,40,82) THEN '4'
                                WHEN grid.zone IN (83,84,85,86,87)  THEN '5'
                                WHEN grid.zone IN (10,11,12) THEN '0'
                                END,
                            COALESCE(pubtrans.k_jltyyp::varchar,'1'), -- 1 = 'juna'
                            pubtrans.k_liikv::varchar
                        )::bigint AS zone
                        FROM grid, pubtrans
                        /* Only those that are not already something else */
                        WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
                        AND pubtrans.k_jltyyp::int = 1
                        AND st_dwithin(grid.geom, pubtrans.geom, 1000) 
                        AND pubtrans.k_liikv <= calculationYear
                        ORDER BY grid.geom, st_distance(grid.geom, pubtrans.geom);

                    INSERT INTO grid_new
                        SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                        CONCAT('999',
                            CASE WHEN grid.zone IN (1,2,3,4,5,6) THEN grid.zone::varchar
                                WHEN grid.zone IN (12,41,81) THEN '3'
                                WHEN grid.zone IN (11,40,82) THEN '4'
                                WHEN grid.zone IN (83,84,85,86,87)  THEN '5'
                                WHEN grid.zone IN (10,11,12) THEN '0' END,
                            COALESCE(pubtrans.k_jltyyp::varchar, '2'), -- 2 = 'ratikka'
                            pubtrans.k_liikv::varchar
                        )::bigint AS zone
                        FROM grid, pubtrans
                        /* Only those that are not already something else */
                        WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
                        AND pubtrans.k_jltyyp::int = 2
                        AND st_dwithin(grid.geom, pubtrans.geom, 800) 
                        AND pubtrans.k_liikv <= calculationYear
                        ORDER BY grid.geom, st_distance(grid.geom, pubtrans.geom);
                    
                    INSERT INTO grid_new
                        SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                        CONCAT('999',
                            CASE WHEN grid.zone IN (1,2,3,4,5,6) THEN grid.zone::varchar
                                WHEN grid.zone IN (12,41,81) THEN '3'
                                WHEN grid.zone IN (11,40,82) THEN '4'
                                WHEN grid.zone IN (83,84,85,86,87)  THEN '5'
                                WHEN grid.zone IN (10,11,12) THEN '0' END,
                            COALESCE(pubtrans.k_jltyyp::varchar,'3'), -- 3 = 'bussi'
                            pubtrans.k_liikv::varchar
                        )::bigint AS zone
                        FROM grid, pubtrans
                        /* Only those that are not already something else */
                        WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
                        AND pubtrans.k_jltyyp::int = 3
                        AND st_dwithin(grid.geom, pubtrans.geom, 400) 
                        AND pubtrans.k_liikv <= calculationYear
                        ORDER BY grid.geom, st_distance(grid.geom, pubtrans.geom);

                END IF;

                -- Päivitetään joukkoliikennevyöhykkeet aiemmin muodostettujen uusien keskustojen/alakeskusten osalta
                /** Tested OK */
                IF plan_transit IS NOT NULL THEN
                    UPDATE grid_new
                        SET zone =
                        CONCAT('999',
                            CASE WHEN grid_new.zone IN (1,2,6) THEN grid_new.zone::varchar
                                WHEN grid_new.zone = 12 THEN '3'
                                WHEN grid_new.zone = 11 THEN '4'
                                WHEN grid_new.zone = 10 THEN '0' END,
                            coalesce(pubtrans.k_jltyyp::varchar,'3'), -- 1 = 'juna', 2 = 'raitiotie, 3 = 'bussi',
                            pubtrans.k_liikv::varchar
                        )::bigint
                        FROM pubtrans
                        WHERE grid_new.zone IN (1,2,10,11,12,6)
                        AND st_dwithin(
                            grid_new.geom,
                            pubtrans.geom,
                            CASE WHEN pubtrans.k_jltyyp = 1 THEN 1000
                                WHEN pubtrans.k_jltyyp = 2 THEN 800 
                                ELSE 400 END
                        ) AND pubtrans.k_liikv <= calculationYear;
                END IF;

                /* Intensiiviset joukkoliikennevyöhykkeet - nykyisten kasvatus ja uudet muualle syntyvät vyöhykkeet */
                /* Tested OK */
                INSERT INTO grid_new
                    SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                    3 AS zone
                    FROM grid
                        /* Only select those that are not already something else */
                        WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
                        AND (grid.zone = 3 OR
                        grid.pop_nn > 797 AND grid.employ_nn > 280);

                /* Joukkoliikennevyöhykkeet - nykyisten kasvatus ja uudet muualle syntyvät vyöhykkeet*/
                /* Tested OK */
                INSERT INTO grid_new
                    SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
                    4 AS zone
                    FROM grid
                        /* Only select those that are not already something else */
                        WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
                        AND (grid.zone = 4 OR (grid.pop_nn > 404 AND grid.employ_nn > 63));

                /* Poistetaan yksinäiset ruudut */
                /** Tested OK */
                DELETE FROM grid_new uz1
                WHERE uz1.xyind IN (SELECT uz1.xyind
                FROM grid_new uz1
                CROSS JOIN LATERAL
                (SELECT
                    ST_Distance(uz1.geom, uz2.geom) as dist
                    FROM grid_new uz2
                    WHERE uz1.xyind <> uz2.xyind AND uz1.zone IN (3,4)
                    ORDER BY uz1.geom <#> uz2.geom
                LIMIT 1) AS test
                WHERE test.dist > 0);

                /* Autovyöhykkeet */
                INSERT INTO grid_new
                SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind, grid.zone
                    FROM grid
                    /* Only select those that are not already something else */
                    WHERE grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new);
                    --AND grid.maa_ha > 0 AND (grid.pop > 0 OR grid.employ > 0);

                /* Yhdistetään vyöhykkeet grid-taulukkoon ja päivitetään keskustaetäisyydet tiettyihin minimi- ja maksimiarvoihin pakotettuina. */
                UPDATE grid SET
                    zone = grid_new.zone
                    FROM grid_new
                        WHERE grid.xyind = grid_new.xyind;

                UPDATE grid
                SET centdist = sq3.centdist FROM
                    (SELECT grid.xyind, center.centdist
                        FROM grid
                        CROSS JOIN LATERAL
                            (SELECT st_distance(centers.geom, grid.geom)/1000 AS centdist
                                FROM centralnetwork centers
                        ORDER BY grid.geom <#> centers.geom
                    LIMIT 1) AS center) as sq3
                WHERE grid.xyind = sq3.xyind;

                /* Poistetaan väliaikaiset taulut ja sarakkeet */
                ALTER TABLE grid 
                    DROP COLUMN IF EXISTS pop_nn,
                    DROP COLUMN IF EXISTS employ_nn;

                RETURN QUERY SELECT * FROM grid;
                DROP TABLE IF EXISTS kt, kv, pubtrans, grid_new;

                IF calculationYear = targetYear THEN
                    DROP TABLE IF EXISTS centralnetwork, grid;
                END IF;

            ELSE 
                RETURN QUERY SELECT * FROM grid;
            END IF;

            END;
            $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_UpdateBuildings(
            rak_taulu text,
            ykr_taulu text,
            calculationYears integer[] -- [year based on which emission values are calculated, min, max calculation years]
        )
        RETURNS TABLE (
            xyind varchar,
            rakv int,
            rakyht_ala integer,
            asuin_ala integer,
            erpien_ala integer,
            rivita_ala integer,
            askert_ala integer,
            liike_ala integer,
            myymal_ala integer,
            majoit_ala integer,
            asla_ala integer,
            ravint_ala integer,
            tsto_ala integer,
            liiken_ala integer,
            hoito_ala integer,
            kokoon_ala integer,
            opetus_ala integer,
            teoll_ala integer,
            varast_ala integer,
            muut_ala integer
        ) AS $$
        DECLARE
            calculationYear integer; 
            teoll_koko numeric;
            varast_koko numeric;
        BEGIN

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
            WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
            ELSE calculationYears[1]
            END;

        EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS rak AS SELECT xyind, rakv::int, rakyht_ala::int, asuin_ala::int, erpien_ala::int, rivita_ala::int, askert_ala::int, liike_ala::int, myymal_ala::int, majoit_ala::int, asla_ala::int, ravint_ala::int, tsto_ala::int, liiken_ala::int, hoito_ala::int, kokoon_ala::int, opetus_ala::int, teoll_ala::int, varast_ala::int, muut_ala::int FROM ' || quote_ident(rak_taulu) ||' WHERE rakv::int != 0';
        EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS ykr AS SELECT xyind, k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala, k_poistuma FROM ' || quote_ident(ykr_taulu) || ' WHERE (k_ap_ala IS NOT NULL AND k_ap_ala != 0) OR (k_ar_ala IS NOT NULL AND k_ar_ala != 0) OR  (k_ak_ala IS NOT NULL AND k_ak_ala != 0) OR (k_muu_ala IS NOT NULL AND k_muu_ala != 0) OR (k_poistuma IS NOT NULL AND k_poistuma != 0)';

        /* Lisätään puuttuvat sarakkeet väliaikaiseen YKR-dataan */
        /* Adding new columns into the temporary YKR data */
        ALTER TABLE ykr
            ADD COLUMN liike_osuus numeric,
            ADD COLUMN myymal_osuus numeric,
            ADD COLUMN majoit_osuus numeric,
            ADD COLUMN asla_osuus numeric,
            ADD COLUMN ravint_osuus numeric,
            ADD COLUMN tsto_osuus numeric,
            ADD COLUMN liiken_osuus numeric,
            ADD COLUMN hoito_osuus numeric,
            ADD COLUMN kokoon_osuus numeric,
            ADD COLUMN opetus_osuus numeric,
            ADD COLUMN teoll_osuus numeric,
            ADD COLUMN varast_osuus numeric,
            ADD COLUMN muut_osuus numeric,
            ADD COLUMN muu_ala numeric;
            
        /* Lasketaan eri käyttömuotojen osuudet väliaikaiseen YKR-dataan */
        /* Calculating the distribution of building uses into the temporary YKR data */
        UPDATE ykr SET 
            muu_ala = COALESCE(sq.muu_ala, 0),
            liike_osuus = COALESCE(sq.liike_ala / sq.muu_ala, 0),
            myymal_osuus = COALESCE(sq.myymal_ala / sq.muu_ala, 0),
            majoit_osuus = COALESCE(sq.majoit_ala / sq.muu_ala, 0),
            asla_osuus = COALESCE(sq.asla_ala / sq.muu_ala, 0),
            ravint_osuus = COALESCE(sq.ravint_ala / sq.muu_ala, 0),
            tsto_osuus = COALESCE(sq.tsto_ala / sq.muu_ala, 0),
            liiken_osuus = COALESCE(sq.liiken_ala / sq.muu_ala, 0),
            hoito_osuus = COALESCE(sq.hoito_ala / sq.muu_ala, 0),
            kokoon_osuus = COALESCE(sq.kokoon_ala / sq.muu_ala, 0),
            opetus_osuus = COALESCE(sq.opetus_ala / sq.muu_ala, 0),
            teoll_osuus = COALESCE(sq.teoll_ala / sq.muu_ala, 0),
            varast_osuus = COALESCE(sq.varast_ala / sq.muu_ala, 0),
            muut_osuus = COALESCE(sq.muut_ala /sq.muu_ala, 0)
        FROM
            (SELECT DISTINCT ON (r.xyind) r.xyind,
                NULLIF(SUM(COALESCE(r.liike_ala,0) + COALESCE(r.tsto_ala,0) + COALESCE(r.liiken_ala,0) + COALESCE(r.hoito_ala,0) + 
                    COALESCE(r.kokoon_ala,0) + COALESCE(r.opetus_ala,0) + COALESCE(r.teoll_ala,0) + COALESCE(r.varast_ala,0) + COALESCE(r.muut_ala,0)),0)::real AS muu_ala,
                SUM(r.liike_ala) AS liike_ala,
                SUM(r.myymal_ala) AS myymal_ala,
                SUM(r.majoit_ala) AS majoit_ala,
                SUM(r.asla_ala) AS asla_ala,
                SUM(r.ravint_ala) AS ravint_ala,
                SUM(r.tsto_ala) AS tsto_ala,
                SUM(r.liiken_ala) AS liiken_ala,
                SUM(r.hoito_ala) AS hoito_ala,
                SUM(r.kokoon_ala) AS kokoon_ala,
                SUM(r.opetus_ala) AS opetus_ala,
                SUM(r.teoll_ala) AS teoll_ala,
                SUM(r.varast_ala) AS varast_ala,
                SUM(r.muut_ala) AS muut_ala
            FROM rak r GROUP BY r.xyind ) sq
        WHERE sq.xyind = ykr.xyind;


        /* Asetetaan myös vakiojakaumat uusia alueita varten */
        /* Käyttöalaperusteinen käyttötapajakauma generoitu Tampereen alueen YKR-datasta */
        /* Set default proportions of building usage for new areas as well */
        UPDATE ykr SET
            liike_osuus = 0.1771,
            myymal_osuus = 0.1245,
            majoit_osuus = 0.0235,
            asla_osuus = 0.0265,
            ravint_osuus = 0.0025,
            tsto_osuus = 0.167,
            liiken_osuus = 0.072,
            hoito_osuus = 0.0577,
            kokoon_osuus = 0.0596,
            opetus_osuus = 0.1391,
            teoll_osuus = 0.2392,
            varast_osuus = 0.0823,
            muut_osuus = 0.006
        WHERE 
            (liike_osuus IS NULL OR liike_osuus = 0) AND
            (myymal_osuus IS NULL OR myymal_osuus = 0) AND
            (majoit_osuus IS NULL OR majoit_osuus = 0) AND
            (asla_osuus IS NULL OR asla_osuus = 0) AND
            (ravint_osuus IS NULL OR ravint_osuus = 0) AND
            (tsto_osuus IS NULL OR tsto_osuus = 0) AND
            (liiken_osuus IS NULL OR liiken_osuus = 0) AND
            (hoito_osuus IS NULL OR hoito_osuus = 0) AND
            (kokoon_osuus IS NULL OR kokoon_osuus = 0) AND
            (opetus_osuus IS NULL OR opetus_osuus = 0) AND
            (teoll_osuus IS NULL OR teoll_osuus = 0) AND
            (varast_osuus IS NULL OR varast_osuus = 0) AND
            (muut_osuus IS NULL OR muut_osuus = 0);

        /* Puretaan rakennuksia  */
        /* Demolishing buildings */
        UPDATE rak b SET
            asuin_ala = (CASE WHEN asuin > b.asuin_ala THEN 0 ELSE b.asuin_ala - asuin END),
            erpien_ala = (CASE WHEN erpien > b.erpien_ala THEN 0 ELSE b.erpien_ala - erpien END),
            rivita_ala = (CASE WHEN rivita > b.rivita_ala THEN 0 ELSE b.rivita_ala - rivita END),
            askert_ala = (CASE WHEN askert > b.askert_ala THEN 0 ELSE b.askert_ala - askert END),
            liike_ala = (CASE WHEN liike > b.liike_ala THEN 0 ELSE b.liike_ala - liike END),
            myymal_ala = (CASE WHEN myymal > b.myymal_ala THEN 0 ELSE b.myymal_ala - myymal END),
            majoit_ala = (CASE WHEN majoit > b.majoit_ala THEN 0 ELSE b.majoit_ala - majoit END),
            asla_ala = (CASE WHEN asla > b.asla_ala THEN 0 ELSE b.asla_ala - asla END),
            ravint_ala = (CASE WHEN ravint > b.ravint_ala THEN 0 ELSE b.ravint_ala - ravint END),
            tsto_ala = (CASE WHEN tsto > b.tsto_ala THEN 0 ELSE b.tsto_ala - tsto END),
            liiken_ala = (CASE WHEN liiken > b.liiken_ala THEN 0 ELSE b.liiken_ala - liiken END),
            hoito_ala = (CASE WHEN hoito > b.hoito_ala THEN 0 ELSE b.hoito_ala - hoito END),
            kokoon_ala = (CASE WHEN kokoon > b.kokoon_ala THEN 0 ELSE b.kokoon_ala - kokoon END),
            opetus_ala = (CASE WHEN opetus > b.opetus_ala THEN 0 ELSE b.opetus_ala - opetus END),
            teoll_ala = (CASE WHEN teoll > b.teoll_ala THEN 0 ELSE b.teoll_ala - teoll END),
            varast_ala = (CASE WHEN varast > b.varast_ala THEN 0 ELSE b.varast_ala - varast END),
            muut_ala = (CASE WHEN muut > b.muut_ala THEN 0 ELSE b.muut_ala - muut END)
        FROM (
        WITH poistuma AS (
            SELECT ykr.xyind, SUM(k_poistuma) AS poistuma FROM ykr GROUP BY ykr.xyind
        ),
        buildings AS (
            SELECT rakennukset.xyind, rakennukset.rakv,
                rakennukset.asuin_ala :: real / NULLIF(grouped.rakyht_ala, 0) asuin,
                rakennukset.erpien_ala :: real / NULLIF(grouped.rakyht_ala, 0) erpien,
                rakennukset.rivita_ala :: real / NULLIF(grouped.rakyht_ala, 0) rivita,
                rakennukset.askert_ala :: real / NULLIF(grouped.rakyht_ala, 0) askert,
                rakennukset.liike_ala :: real / NULLIF(grouped.rakyht_ala, 0) liike,
                rakennukset.myymal_ala :: real / NULLIF(grouped.rakyht_ala, 0) myymal,
                rakennukset.majoit_ala :: real / NULLIF(grouped.rakyht_ala, 0) majoit,
                rakennukset.asla_ala :: real / NULLIF(grouped.rakyht_ala, 0) asla,
                rakennukset.ravint_ala :: real / NULLIF(grouped.rakyht_ala, 0) ravint,
                rakennukset.tsto_ala :: real / NULLIF(grouped.rakyht_ala, 0) tsto,
                rakennukset.liiken_ala :: real / NULLIF(grouped.rakyht_ala, 0) liiken,
                rakennukset.hoito_ala :: real / NULLIF(grouped.rakyht_ala, 0) hoito,
                rakennukset.kokoon_ala :: real / NULLIF(grouped.rakyht_ala, 0) kokoon,
                rakennukset.opetus_ala :: real / NULLIF(grouped.rakyht_ala, 0) opetus,
                rakennukset.teoll_ala :: real / NULLIF(grouped.rakyht_ala, 0) teoll,
                rakennukset.varast_ala:: real / NULLIF(grouped.rakyht_ala, 0) varast,
                rakennukset.muut_ala :: real / NULLIF(grouped.rakyht_ala, 0) muut
            FROM rak rakennukset JOIN
            (SELECT build2.xyind, SUM(build2.rakyht_ala) rakyht_ala FROM rak build2 GROUP BY build2.xyind) grouped
            ON grouped.xyind = rakennukset.xyind
            WHERE rakennukset.rakv != calculationYear
        )
        SELECT poistuma.xyind,
            buildings.rakv,
            poistuma * asuin asuin,
            poistuma * erpien erpien,
            poistuma * rivita rivita,
            poistuma * askert askert,
            poistuma * liike liike,
            poistuma * myymal myymal,
            poistuma * majoit majoit,
            poistuma * asla asla,
            poistuma * ravint ravint,
            poistuma * tsto tsto,
            poistuma * liiken liiken,
            poistuma * hoito hoito,
            poistuma * kokoon kokoon,
            poistuma * opetus opetus,
            poistuma * teoll teoll,
            poistuma * varast varast,
            poistuma * muut muut
        FROM poistuma LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
        WHERE poistuma > 0 AND buildings.rakv IS NOT NULL) poistumat
        WHERE b.xyind = poistumat.xyind AND b.rakv = poistumat.rakv;


        /* Rakennetaan uusia rakennuksia */
        /* Building new buildings */
        INSERT INTO rak(xyind, rakv, rakyht_ala, asuin_ala, erpien_ala, rivita_ala, askert_ala, liike_ala, myymal_ala, majoit_ala, asla_ala, ravint_ala, tsto_ala, liiken_ala, hoito_ala, kokoon_ala, opetus_ala, teoll_ala, varast_ala, muut_ala   )
        SELECT
            DISTINCT ON (ykr.xyind) ykr.xyind, -- xyind
            calculationYear, -- rakv
            (k_ap_ala + k_ar_ala + k_ak_ala + k_muu_ala)::int, -- rakyht_ala
            (k_ap_ala + k_ar_ala + k_ak_ala)::int, -- asuin_ala
            k_ap_ala::int, --erpien_ala
            k_ar_ala::int, -- rivita_ala
            k_ak_ala::int, -- askert_ala
            (liike_osuus * k_muu_ala)::int, -- liike_ala
            (myymal_osuus * k_muu_ala)::int, -- myymal_ala
            (majoit_osuus * k_muu_ala)::int, -- majoit_ala
            (asla_osuus * k_muu_ala)::int, -- asla_ala
            (ravint_osuus * k_muu_ala)::int, -- ravint_ala
            (tsto_osuus * k_muu_ala)::int, -- tsto_ala
            (liiken_osuus * k_muu_ala)::int, -- liiken_ala
            (hoito_osuus * k_muu_ala)::int, -- hoito_ala
            (kokoon_osuus * k_muu_ala)::int, -- kokoon_ala
            (opetus_osuus * k_muu_ala)::int, -- opetus_ala
            (teoll_osuus * k_muu_ala)::int, -- teoll_ala
            (varast_osuus * k_muu_ala)::int, -- varast_ala
            (muut_osuus * k_muu_ala)::int -- muut_ala
            FROM ykr;
        ALTER TABLE ykr DROP COLUMN IF EXISTS muu_ala;
        RETURN QUERY SELECT * FROM rak;
        DROP TABLE IF EXISTS ykr, rak;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_UpdateBuildingsLocal(
            rak_taulu text,
            ykr_taulu text,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            baseYear int,
            targetYear int,
            kehitysskenaario varchar -- PITKO:n mukainen kehitysskenaario
        )
        RETURNS TABLE (
            xyind varchar,
            rakv int,
            energiam varchar,
            rakyht_ala int, 
            asuin_ala int,
            erpien_ala int,
            rivita_ala int,
            askert_ala int,
            liike_ala int,
            myymal_ala int,
            majoit_ala int,
            asla_ala int,
            ravint_ala int,
            tsto_ala int,
            liiken_ala int,
            hoito_ala int,
            kokoon_ala int,
            opetus_ala int,
            teoll_ala int,
            varast_ala int,
            muut_ala int
        ) AS $$
        DECLARE
            calculationYear integer; 
            defaultdemolition boolean;
            energiamuoto varchar;
            laskentavuodet int[];
            laskenta_length int;
            step real;
            localweight real;
            globalweight real;
            teoll_koko real;
            varast_koko real;
        BEGIN

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
            WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
            ELSE calculationYears[1]
            END;

        -- energiamuodot := ARRAY [kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys];
        SELECT array(select generate_series(baseYear,targetYear)) INTO laskentavuodet;
        SELECT array_length(laskentavuodet,1) into laskenta_length;
        SELECT 1::real / laskenta_length INTO step;
        SELECT (calculationYear - baseYear + 1) * step INTO globalweight;
        SELECT 1 - globalweight INTO localweight;

        EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS ykr AS SELECT xyind, zone, k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala, k_poistuma FROM ' || quote_ident(ykr_taulu) || ' WHERE (k_ap_ala IS NOT NULL AND k_ap_ala != 0) OR (k_ar_ala IS NOT NULL AND k_ar_ala != 0) OR (k_ak_ala IS NOT NULL AND k_ak_ala != 0) OR (k_muu_ala IS NOT NULL AND k_muu_ala != 0) OR (k_poistuma IS NOT NULL AND k_poistuma != 0)';
        EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS rak AS SELECT xyind, rakv::int, energiam::varchar, rakyht_ala::int, asuin_ala::int, erpien_ala::int, rivita_ala::int, askert_ala::int, liike_ala::int, myymal_ala::int, majoit_ala::int, asla_ala::int, ravint_ala::int, tsto_ala::int, liiken_ala::int, hoito_ala::int, kokoon_ala::int, opetus_ala::int, teoll_ala::int, varast_ala::int, muut_ala::int FROM ' || quote_ident(rak_taulu) ||' WHERE rakv::int != 0'; -- AND xyind IN (SELECT ykr.xyind from ykr)

        /* Haetaan globaalit lämmitysmuotojakaumat laskentavuodelle ja -skenaariolle */
        /* Fetching global heating ratios for current calculation year and scenario */
        CREATE TEMP TABLE IF NOT EXISTS global_jakauma AS
            SELECT rakennus_tyyppi, kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
            FROM built.distribution_heating_systems dhs
            WHERE dhs.year = calculationYear AND dhs.rakv = calculationYear AND dhs.scenario = kehitysskenaario;

        INSERT INTO global_jakauma (rakennus_tyyppi, kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys)
            SELECT 'rakyht', avg(kaukolampo), avg(kevyt_oljy), avg(kaasu), avg(sahko), avg(puu), avg(maalampo), avg(muu_lammitys)
            FROM global_jakauma;

        /* Puretaan rakennuksia  */
        /* Demolishing buildings */
        SELECT CASE WHEN k_poistuma > 999998 AND k_poistuma < 1000000 THEN TRUE ELSE FALSE END FROM ykr LIMIT 1 INTO defaultdemolition;

        UPDATE rak b SET
            erpien_ala = (CASE WHEN erpien > b.erpien_ala THEN 0 ELSE b.erpien_ala - erpien END),
            rivita_ala = (CASE WHEN rivita > b.rivita_ala THEN 0 ELSE b.rivita_ala - rivita END),
            askert_ala = (CASE WHEN askert > b.askert_ala THEN 0 ELSE b.askert_ala - askert END),
            liike_ala = (CASE WHEN liike > b.liike_ala THEN 0 ELSE b.liike_ala - liike END),
            myymal_ala = (CASE WHEN myymal > b.myymal_ala THEN 0 ELSE b.myymal_ala - myymal END),
            majoit_ala = (CASE WHEN majoit > b.majoit_ala THEN 0 ELSE b.majoit_ala - majoit END),
            asla_ala = (CASE WHEN asla > b.asla_ala THEN 0 ELSE b.asla_ala - asla END),
            ravint_ala = (CASE WHEN ravint > b.ravint_ala THEN 0 ELSE b.ravint_ala - ravint END),
            tsto_ala = (CASE WHEN tsto > b.tsto_ala THEN 0 ELSE b.tsto_ala - tsto END),
            liiken_ala = (CASE WHEN liiken > b.liiken_ala THEN 0 ELSE b.liiken_ala - liiken END),
            hoito_ala = (CASE WHEN hoito > b.hoito_ala THEN 0 ELSE b.hoito_ala - hoito END),
            kokoon_ala = (CASE WHEN kokoon > b.kokoon_ala THEN 0 ELSE b.kokoon_ala - kokoon END),
            opetus_ala = (CASE WHEN opetus > b.opetus_ala THEN 0 ELSE b.opetus_ala - opetus END),
            teoll_ala = (CASE WHEN teoll > b.teoll_ala THEN 0 ELSE b.teoll_ala - teoll END),
            varast_ala = (CASE WHEN varast > b.varast_ala THEN 0 ELSE b.varast_ala - varast END),
            muut_ala = (CASE WHEN muut > b.muut_ala THEN 0 ELSE b.muut_ala - muut END)
        FROM (
        WITH poistuma AS (
            SELECT ykr.xyind, (CASE WHEN defaultdemolition = TRUE THEN 0.0015 ELSE SUM(k_poistuma) END) AS poistuma FROM ykr GROUP BY ykr.xyind
        ),
        buildings AS (
            SELECT rakennukset.xyind, rakennukset.rakv,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.erpien_ala :: real ELSE rakennukset.erpien_ala :: real / NULLIF(grouped.rakyht_ala, 0) END erpien,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.rivita_ala :: real ELSE rakennukset.rivita_ala :: real / NULLIF(grouped.rakyht_ala, 0) END rivita,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.askert_ala :: real ELSE rakennukset.askert_ala :: real / NULLIF(grouped.rakyht_ala, 0) END askert,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.liike_ala :: real ELSE rakennukset.liike_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liike,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_ala :: real ELSE rakennukset.myymal_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myymal,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.majoit_ala :: real ELSE rakennukset.majoit_ala :: real / NULLIF(grouped.rakyht_ala, 0) END majoit,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.asla_ala :: real ELSE rakennukset.asla_ala :: real / NULLIF(grouped.rakyht_ala, 0) END asla,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.ravint_ala :: real ELSE rakennukset.ravint_ala :: real / NULLIF(grouped.rakyht_ala, 0) END ravint,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.tsto_ala :: real ELSE rakennukset.tsto_ala :: real / NULLIF(grouped.rakyht_ala, 0) END tsto,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.liiken_ala :: real ELSE rakennukset.liiken_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liiken,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.hoito_ala :: real ELSE rakennukset.hoito_ala :: real / NULLIF(grouped.rakyht_ala, 0) END hoito,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.kokoon_ala :: real ELSE rakennukset.kokoon_ala :: real / NULLIF(grouped.rakyht_ala, 0) END kokoon,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.opetus_ala :: real ELSE rakennukset.opetus_ala :: real / NULLIF(grouped.rakyht_ala, 0) END opetus,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_ala :: real ELSE rakennukset.teoll_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.varast_ala :: real ELSE rakennukset.varast_ala:: real / NULLIF(grouped.rakyht_ala, 0) END varast,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.muut_ala :: real ELSE rakennukset.muut_ala :: real / NULLIF(grouped.rakyht_ala, 0) END muut
            FROM rak rakennukset JOIN
            (SELECT build2.xyind, SUM(build2.rakyht_ala) rakyht_ala FROM rak build2 GROUP BY build2.xyind) grouped
            ON grouped.xyind = rakennukset.xyind
            WHERE rakennukset.rakv != calculationYear
        )
        SELECT poistuma.xyind,
            buildings.rakv,
            poistuma * erpien erpien,
            poistuma * rivita rivita,
            poistuma * askert askert,
            poistuma * liike liike,
            poistuma * myymal myymal,
            poistuma * majoit majoit,
            poistuma * asla asla,
            poistuma * ravint ravint,
            poistuma * tsto tsto,
            poistuma * liiken liiken,
            poistuma * hoito hoito,
            poistuma * kokoon kokoon,
            poistuma * opetus opetus,
            poistuma * teoll teoll,
            poistuma * varast varast,
            poistuma * muut muut
        FROM poistuma LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
        WHERE poistuma > 0 AND buildings.rakv IS NOT NULL) poistumat
        WHERE b.xyind = poistumat.xyind AND b.rakv = poistumat.rakv;

        /* Lisätään puuttuvat sarakkeet väliaikaiseen YKR-dataan */
        /* Adding new columns into the temporary YKR data */
        ALTER TABLE ykr
            ADD COLUMN liike_osuus real,
            ADD COLUMN myymal_osuus real,
            ADD COLUMN majoit_osuus real,
            ADD COLUMN asla_osuus real,
            ADD COLUMN ravint_osuus real,
            ADD COLUMN tsto_osuus real,
            ADD COLUMN liiken_osuus real,
            ADD COLUMN hoito_osuus real,
            ADD COLUMN kokoon_osuus real,
            ADD COLUMN opetus_osuus real,
            ADD COLUMN teoll_osuus real,
            ADD COLUMN varast_osuus real,
            ADD COLUMN muut_osuus real,
            ADD COLUMN muu_ala real;

        /* Lasketaan myös vakiokäyttötapausjakaumat uusia alueita varten */
        /* Käyttöalaperusteinen käyttötapajakauma generoidaan rakennusdatasta UZ-vyöhykkeittäin */
        /* Calculate default proportions of building usage for new areas as well */
        CREATE TEMP TABLE IF NOT EXISTS kayttotapajakauma AS 
        SELECT ykr.zone,
            COALESCE(SUM(r.liike_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liike_osuus,
            COALESCE(SUM(r.myymal_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as myymal_osuus,
            COALESCE(SUM(r.majoit_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as majoit_osuus,
            COALESCE(SUM(r.asla_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as asla_osuus,
            COALESCE(SUM(r.ravint_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as ravint_osuus,
            COALESCE(SUM(r.tsto_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as tsto_osuus,
            COALESCE(SUM(r.liiken_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liiken_osuus,
            COALESCE(SUM(r.hoito_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as hoito_osuus,
            COALESCE(SUM(r.kokoon_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as kokoon_osuus,
            COALESCE(SUM(r.opetus_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as opetus_osuus,
            COALESCE(SUM(r.teoll_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as teoll_osuus,
            COALESCE(SUM(r.varast_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as varast_osuus,
            COALESCE(SUM(r.muut_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as muut_osuus
        FROM rak r JOIN ykr ON r.xyind = ykr.xyind
        GROUP BY ykr.zone;

        UPDATE kayttotapajakauma j SET 
            liike_osuus = ktj.liike_osuus,
            myymal_osuus = ktj.myymal_osuus,
            majoit_osuus = ktj.majoit_osuus,
            asla_osuus = ktj.asla_osuus,
            ravint_osuus = ktj.ravint_osuus,
            tsto_osuus = ktj.tsto_osuus,
            liiken_osuus = ktj.liiken_osuus,
            hoito_osuus = ktj.hoito_osuus,
            kokoon_osuus = ktj.kokoon_osuus,
            opetus_osuus = ktj.opetus_osuus,
            teoll_osuus = ktj.teoll_osuus,
            varast_osuus = ktj.varast_osuus,
            muut_osuus = ktj.muut_osuus
        FROM
        (SELECT
            AVG(k.liike_osuus) liike_osuus, AVG(k.myymal_osuus) myymal_osuus, AVG(k.majoit_osuus) majoit_osuus, AVG(k.asla_osuus) asla_osuus, AVG(k.ravint_osuus) ravint_osuus,
            AVG(k.tsto_osuus) tsto_osuus, AVG(k.liiken_osuus) liiken_osuus, AVG(k.hoito_osuus) hoito_osuus, AVG(k.kokoon_osuus) kokoon_osuus, AVG(k.opetus_osuus) opetus_osuus, AVG(k.teoll_osuus) teoll_osuus,
            AVG(k.varast_osuus) varast_osuus, AVG(k.muut_osuus) muut_osuus
        FROM kayttotapajakauma k
            WHERE k.liike_osuus + k.tsto_osuus + k.liiken_osuus + k.hoito_osuus + k.kokoon_osuus + k.opetus_osuus + k.teoll_osuus + k.varast_osuus + k.muut_osuus = 1
        ) ktj
        WHERE j.liike_osuus + j.tsto_osuus + j.liiken_osuus + j.hoito_osuus + j.kokoon_osuus + j.opetus_osuus + j.teoll_osuus + j.varast_osuus + j.muut_osuus < 0.99;

        UPDATE ykr y SET
            liike_osuus = ktj.liike_osuus,
            myymal_osuus = ktj.myymal_osuus,
            majoit_osuus = ktj.majoit_osuus,
            asla_osuus = ktj.asla_osuus,
            ravint_osuus = ktj.ravint_osuus,
            tsto_osuus = ktj.tsto_osuus,
            liiken_osuus = ktj.liiken_osuus,
            hoito_osuus = ktj.hoito_osuus,
            kokoon_osuus = ktj.kokoon_osuus,
            opetus_osuus = ktj.opetus_osuus,
            teoll_osuus = ktj.teoll_osuus,
            varast_osuus = ktj.varast_osuus,
            muut_osuus = ktj.muut_osuus
        FROM kayttotapajakauma ktj
        WHERE y.zone = ktj.zone;

        /* Lasketaan nykyisen paikallisesta rakennusdatasta muodostetun ruutuaineiston mukainen ruutukohtainen energiajakauma rakennustyypeittäin */
        /* Laskenta tehdään vain 2000-luvulta eteenpäin rakennetuille tai rakennettaville rakennuksille */
        CREATE TEMP TABLE IF NOT EXISTS local_jakauma AS
        WITH cte AS (
        WITH
            index AS (
            SELECT distinct on (ykr.xyind) ykr.xyind FROM ykr
            ), kaukolampo AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert,
                SUM(rak.liike_ala) as liike,
                SUM(rak.tsto_ala) as tsto,
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='kaukolampo' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), kevyt_oljy AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), kaasu AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='kaasu' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), sahko AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='sahko' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), puu AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='puu' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), maalampo AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='maalampo' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), muu_lammitys AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert,
                SUM(rak.liike_ala) as liike,
                SUM(rak.tsto_ala) as tsto,
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='muu_lammitys' AND rak.rakv > 2000
            GROUP BY rak.xyind
        )
            
        SELECT index.xyind, 'rakyht' as rakennus_tyyppi,
        kaukolampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0)  + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kaukolampo,
        kevyt_oljy.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kevyt_oljy,
        kaasu.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kaasu,
        sahko.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS sahko,
        puu.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS puu,
        maalampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS maalampo,
        muu_lammitys.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'erpien' as rakennus_tyyppi,
        kaukolampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kaukolampo,
        kevyt_oljy.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kevyt_oljy,
        kaasu.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kaasu,
        sahko.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS sahko,
        puu.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS puu,
        maalampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS maalampo,
        muu_lammitys.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'rivita' as rakennus_tyyppi,
        kaukolampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kaukolampo,
        kevyt_oljy.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kevyt_oljy,
        kaasu.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kaasu,
        sahko.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS sahko,
        puu.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS puu,
        maalampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS maalampo,
        muu_lammitys.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'askert' as rakennus_tyyppi,
        kaukolampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kaukolampo,
        kevyt_oljy.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kevyt_oljy,
        kaasu.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kaasu,
        sahko.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS sahko,
        puu.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS puu,
        maalampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS maalampo,
        muu_lammitys.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'liike' as rakennus_tyyppi,
        kaukolampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kaukolampo,
        kevyt_oljy.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kevyt_oljy,
        kaasu.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kaasu,
        sahko.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS sahko,
        puu.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS puu,
        maalampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS maalampo,
        muu_lammitys.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'tsto' as rakennus_tyyppi,
        kaukolampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kaukolampo,
        kevyt_oljy.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kevyt_oljy,
        kaasu.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kaasu,
        sahko.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS sahko,
        puu.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS puu,
        maalampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS maalampo,
        muu_lammitys.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'liiken' as rakennus_tyyppi,
        kaukolampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kaukolampo,
        kevyt_oljy.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kevyt_oljy,
        kaasu.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kaasu,
        sahko.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS sahko,
        puu.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS puu,
        maalampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS maalampo,
        muu_lammitys.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind  
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'hoito' as rakennus_tyyppi,
        kaukolampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kaukolampo,
        kevyt_oljy.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kevyt_oljy,
        kaasu.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kaasu,
        sahko.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS sahko,
        puu.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS puu,
        maalampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS maalampo,
        muu_lammitys.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'kokoon' as rakennus_tyyppi,
        kaukolampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kaukolampo,
        kevyt_oljy.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kevyt_oljy,
        kaasu.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kaasu,
        sahko.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS sahko,
        puu.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS puu,
        maalampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS maalampo,
        muu_lammitys.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'opetus' as rakennus_tyyppi,
        kaukolampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kaukolampo,
        kevyt_oljy.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kevyt_oljy,
        kaasu.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kaasu,
        sahko.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS sahko,
        puu.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS puu,
        maalampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS maalampo,
        muu_lammitys.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'teoll' as rakennus_tyyppi,
        kaukolampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kaukolampo,
        kevyt_oljy.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kevyt_oljy,
        kaasu.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kaasu,
        sahko.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS sahko,
        puu.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS puu,
        maalampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS maalampo,
        muu_lammitys.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind 
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind 
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind 

        UNION 
        SELECT index.xyind, 'varast' as rakennus_tyyppi,
        kaukolampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kaukolampo,
        kevyt_oljy.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kevyt_oljy,
        kaasu.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kaasu,
        sahko.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS sahko,
        puu.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS puu,
        maalampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS maalampo,
        muu_lammitys.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'muut' as rakennus_tyyppi,
        kaukolampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0)  + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kaukolampo,
        kevyt_oljy.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kevyt_oljy,
        kaasu.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kaasu,
        sahko.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS sahko,
        puu.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS puu,
        maalampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS maalampo,
        muu_lammitys.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind
        )
        SELECT * FROM cte;

        /* Päivitetään paikallisen lämmitysmuotojakauman ja kansallisen lämmitysmuotojakauman erot */
        /* Updating differences between local and "global" heating distributions */
        UPDATE local_jakauma l SET
        kaukolampo = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kaukolampo ELSE localweight * COALESCE(l.kaukolampo,0) + globalweight * g.kaukolampo END),
        kevyt_oljy = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kevyt_oljy ELSE localweight * COALESCE(l.kevyt_oljy,0) + globalweight * g.kevyt_oljy END),
        kaasu = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kaasu ELSE localweight * COALESCE(l.kaasu,0) + globalweight * g.kaasu END),
        sahko = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.sahko ELSE localweight * COALESCE(l.sahko,0) + globalweight * g.sahko END),
        puu = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.puu ELSE localweight* COALESCE(l.puu,0) + globalweight * g.puu END),
        maalampo = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.maalampo ELSE localweight * COALESCE(l.maalampo,0) + globalweight * g.maalampo END),
        muu_lammitys = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.muu_lammitys ELSE localweight * COALESCE(l.muu_lammitys,0) + globalweight * g.muu_lammitys END)
        FROM global_jakauma g
        WHERE l.rakennus_tyyppi =  g.rakennus_tyyppi;

        /* Rakennetaan uudet rakennukset energiamuodoittain */
        /* Building new buildings, per primary energy source */
        FOREACH energiamuoto IN ARRAY ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys']
        LOOP

            WITH cte AS (
            WITH
                indeksi AS (
                    SELECT DISTINCT ON (l.xyind) l.xyind FROM local_jakauma l
                ),
                erpien_lammitysmuoto AS ( SELECT l.xyind,
                    (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as erpien FROM local_jakauma l WHERE rakennus_tyyppi = 'erpien' ),
                rivita_lammitysmuoto AS ( SELECT l.xyind, 
                    (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as rivita FROM local_jakauma l WHERE rakennus_tyyppi = 'rivita' ),
                askert_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as askert FROM local_jakauma l WHERE rakennus_tyyppi = 'askert' ),
                liike_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as liike FROM local_jakauma l WHERE rakennus_tyyppi = 'liike' ),
                tsto_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN 
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as tsto FROM local_jakauma l WHERE rakennus_tyyppi = 'tsto' ),
                liiken_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as liiken FROM local_jakauma l WHERE rakennus_tyyppi = 'liiken' ),
                hoito_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as hoito FROM local_jakauma l WHERE rakennus_tyyppi = 'hoito' ),
                kokoon_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as kokoon FROM local_jakauma l WHERE rakennus_tyyppi = 'kokoon' ),
                opetus_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as opetus FROM local_jakauma l WHERE rakennus_tyyppi = 'opetus' ),
                teoll_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as teoll FROM local_jakauma l WHERE rakennus_tyyppi = 'teoll' ),
                varast_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as varast FROM local_jakauma l WHERE rakennus_tyyppi = 'varast' ),
                muut_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN
                            energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as muut FROM local_jakauma l WHERE rakennus_tyyppi = 'muut' )
            SELECT indeksi.*,
                    COALESCE(erpien,(SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'erpien')) AS erpien,
                    COALESCE(rivita, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'rivita')) AS rivita,
                    COALESCE(askert, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'askert')) AS askert,
                    COALESCE(liike, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'liike'))	AS liike,
                    COALESCE(tsto, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'tsto')) AS tsto,
                    COALESCE(liiken, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'liiken')) AS liiken,
                    COALESCE(hoito, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'hoito'))	AS hoito,
                    COALESCE(kokoon, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'kokoon')) AS kokoon,
                    COALESCE(opetus, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'opetus')) AS opetus,
                    COALESCE(teoll, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'teoll'))	AS teoll,
                    COALESCE(varast, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'varast')) AS varast,
                    COALESCE(muut, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto = 'kevyt_oljy' THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'muut')) AS muut
                FROM indeksi
                    LEFT JOIN erpien_lammitysmuoto ON erpien_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN rivita_lammitysmuoto ON rivita_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN askert_lammitysmuoto ON askert_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN liike_lammitysmuoto ON liike_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN tsto_lammitysmuoto ON tsto_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN liiken_lammitysmuoto ON liiken_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN hoito_lammitysmuoto ON hoito_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN kokoon_lammitysmuoto ON kokoon_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN opetus_lammitysmuoto ON opetus_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN teoll_lammitysmuoto ON teoll_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN varast_lammitysmuoto ON varast_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN muut_lammitysmuoto ON muut_lammitysmuoto.xyind = indeksi.xyind
            )
            INSERT INTO rak (xyind, rakv, energiam, rakyht_ala, asuin_ala, erpien_ala, rivita_ala, askert_ala, liike_ala, myymal_ala, majoit_ala, asla_ala, ravint_ala, tsto_ala, liiken_ala, hoito_ala, kokoon_ala, opetus_ala, teoll_ala, varast_ala, muut_ala)
            SELECT
                ykr.xyind, -- xyind
                calculationYear, -- rakv
                energiamuoto, -- energiam
                NULL::int, -- rakyht_ala
                NULL::int, --asuin_ala
                CASE WHEN k_ap_ala * erpien > 0.4 AND k_ap_ala * erpien < 1 THEN 1 ELSE k_ap_ala * erpien END, -- erpien_ala
                CASE WHEN k_ar_ala * rivita > 0.4 AND k_ar_ala * rivita < 1 THEN 1 ELSE k_ar_ala * rivita END, -- rivita_ala
                CASE WHEN k_ak_ala * askert > 0.4 AND k_ak_ala * askert < 1 THEN 1 ELSE k_ak_ala * askert END, -- askert_ala
                CASE WHEN liike_osuus * k_muu_ala * liike > 0.4 AND liike_osuus * k_muu_ala * liike < 1 THEN 1 ELSE liike_osuus * k_muu_ala * liike END, -- liike_ala
                CASE WHEN myymal_osuus * k_muu_ala * liike > 0.4 AND myymal_osuus * k_muu_ala * liike < 1 THEN 1 ELSE myymal_osuus * k_muu_ala * liike END, --myymal_ala
                CASE WHEN majoit_osuus * k_muu_ala * liike > 0.4 AND majoit_osuus * k_muu_ala * liike < 1 THEN 1 ELSE majoit_osuus * k_muu_ala * liike END, -- majoit_ala
                CASE WHEN asla_osuus * k_muu_ala * liike > 0.4 AND asla_osuus * k_muu_ala * liike < 1 THEN 1 ELSE asla_osuus * k_muu_ala * liike END, -- asla_ala
                CASE WHEN ravint_osuus * k_muu_ala * liike > 0.4 AND ravint_osuus * k_muu_ala * liike < 1 THEN 1 ELSE ravint_osuus * k_muu_ala * liike END, -- ravint_ala
                CASE WHEN tsto_osuus * k_muu_ala * tsto > 0.4 AND tsto_osuus * k_muu_ala * tsto < 1 THEN 1 ELSE tsto_osuus * k_muu_ala * tsto END, -- tsto_ala
                CASE WHEN liiken_osuus * k_muu_ala * liiken > 0.4 AND liiken_osuus * k_muu_ala * liiken < 1 THEN 1 ELSE liiken_osuus * k_muu_ala * liiken END, -- liiken_ala
                CASE WHEN hoito_osuus * k_muu_ala * hoito > 0.4 AND hoito_osuus * k_muu_ala * hoito < 1 THEN 1 ELSE hoito_osuus * k_muu_ala * hoito END, -- hoito_ala
                CASE WHEN kokoon_osuus * k_muu_ala * kokoon > 0.4 AND kokoon_osuus * k_muu_ala * kokoon < 1 THEN 1 ELSE kokoon_osuus * k_muu_ala * kokoon END, -- kokoon_ala
                CASE WHEN opetus_osuus * k_muu_ala * opetus > 0.4 AND opetus_osuus * k_muu_ala * opetus < 1 THEN 1 ELSE opetus_osuus * k_muu_ala * opetus END, -- opetus_ala
                CASE WHEN teoll_osuus * k_muu_ala * teoll > 0.4 AND teoll_osuus * k_muu_ala * teoll < 1 THEN 1 ELSE teoll_osuus * k_muu_ala * teoll END, -- teoll_ala
                CASE WHEN varast_osuus * k_muu_ala * varast > 0.4 AND varast_osuus * k_muu_ala * varast < 1 THEN 1 ELSE varast_osuus * k_muu_ala * varast END, -- varast_ala
                CASE WHEN muut_osuus * k_muu_ala * muut > 0.4 AND muut_osuus * k_muu_ala * muut < 1 THEN 1 ELSE muut_osuus * k_muu_ala * muut END -- muut_ala
            FROM ykr LEFT JOIN cte on ykr.xyind = cte.xyind;

        END LOOP;

        UPDATE rak SET
            asuin_ala = COALESCE(rak.erpien_ala,0) + COALESCE(rak.rivita_ala,0) + COALESCE(rak.askert_ala,0)
        WHERE rak.rakv = calculationYear AND rak.asuin_ala IS NULL;

        UPDATE rak SET
            rakyht_ala = COALESCE(rak.asuin_ala,0) + COALESCE(rak.liike_ala,0) + COALESCE(rak.tsto_ala,0) + COALESCE(rak.liiken_ala,0) +
            COALESCE(rak.hoito_ala,0) + COALESCE(rak.kokoon_ala,0) + COALESCE(rak.opetus_ala, 0) + COALESCE(rak.teoll_ala, 0) +
            COALESCE(rak.varast_ala, 0) + COALESCE(rak.muut_ala, 0) 
        WHERE rak.rakv = calculationYear AND rak.rakyht_ala IS NULL;

        DELETE FROM rak WHERE rak.rakyht_ala = 0;

        /* Päivitetään vanhojen pytinkien lämmitysmuodot */
        /* Updating heating characteristics of old buildings */

        CREATE TEMP TABLE IF NOT EXISTS rak_temp AS
        SELECT DISTINCT ON (r.xyind, r.rakv, energiam) r.xyind, r.rakv,
        UNNEST(CASE
        WHEN muu_lammitys IS NULL AND kevyt_oljy IS NULL AND kaasu IS NULL THEN
            ARRAY['kaukolampo', 'sahko', 'puu', 'maalampo'] 
        WHEN muu_lammitys IS NULL THEN
            ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo'] 
        ELSE ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys'] END)::varchar AS energiam,
        NULL::int AS rakyht_ala, NULL::int AS asuin_ala, NULL::int AS erpien_ala, NULL::int AS rivita_ala, NULL::int AS askert_ala,
        NULL::int AS liike_ala, NULL::int AS myymal_ala, NULL::int AS majoit_ala, NULL::int AS asla_ala, NULL::int AS ravint_ala, 
        NULL::int AS tsto_ala, NULL::int AS liiken_ala, NULL::int AS hoito_ala, NULL::int AS kokoon_ala, NULL::int AS opetus_ala,
        NULL::int AS teoll_ala, NULL::int AS varast_ala, NULL::int AS muut_ala
        from rak r
        LEFT JOIN 
        (WITH
            kaukolampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'kaukolampo'),
            kevyt_oljy AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili')),
            kaasu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'kaasu'),
            sahko AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'sahko'),
            puu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'puu'),
            maalampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'maalampo'),
            muu_lammitys AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'muu_lammitys')
        SELECT distinct on (r2.xyind, r2.rakv) r2.xyind, r2.rakv,
            kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
        FROM rak r2
            LEFT JOIN kaukolampo on r2.xyind = kaukolampo.xyind AND r2.rakv = kaukolampo.rakv 
            LEFT JOIN kevyt_oljy on r2.xyind = kevyt_oljy.xyind AND r2.rakv = kevyt_oljy.rakv 
            LEFT JOIN kaasu on r2.xyind = kaasu.xyind AND r2.rakv = kaasu.rakv 
            LEFT JOIN sahko on r2.xyind = sahko.xyind AND r2.rakv = sahko.rakv 
            LEFT JOIN puu on r2.xyind = puu.xyind AND r2.rakv = puu.rakv
            LEFT JOIN maalampo on r2.xyind = maalampo.xyind AND r2.rakv = maalampo.rakv 
            LEFT JOIN muu_lammitys on r2.xyind = muu_lammitys.xyind AND r2.rakv = muu_lammitys.rakv
        WHERE r2.rakv < 2019
            ) sq 
        ON sq.xyind = r.xyind AND sq.rakv = r.rakv where r.rakv < 2019;

        UPDATE rak_temp future set rakyht_ala = past.rakyht_ala,
            asuin_ala = past.asuin_ala, erpien_ala = past.erpien_ala, rivita_ala = past.rivita_ala, askert_ala = past.askert_ala, liike_ala = past.liike_ala, myymal_ala = past.myymal_ala,
            majoit_ala = past.majoit_ala, asla_ala = past.asla_ala, ravint_ala = past.ravint_ala,  tsto_ala = past.tsto_ala, liiken_ala = past.liiken_ala, hoito_ala = past.hoito_ala, kokoon_ala = past.kokoon_ala,
            opetus_ala = past.opetus_ala, teoll_ala = past.teoll_ala, varast_ala = past.varast_ala, muut_ala = past.muut_ala
        FROM rak past WHERE future.xyind = past.xyind AND future.rakv = past.rakv AND future.energiam = past.energiam;

        CREATE TEMP TABLE IF NOT EXISTS rak_new AS 
        SELECT * FROM
        (WITH
        muutos AS (
        SELECT sq.xyind, sq.rakv,
            ARRAY[sum(erpien[1]), sum(erpien[2]), sum(erpien[3]), sum(erpien[4]), sum(erpien[5]), sum(erpien[6])] as erpien,
            ARRAY[sum(rivita[1]), sum(rivita[2]), sum(rivita[3]), sum(rivita[4]), sum(rivita[5]), sum(rivita[6])] as rivita,
            ARRAY[sum(askert[1]), sum(askert[2]), sum(askert[3]), sum(askert[4]), sum(askert[5]), sum(askert[6])] as askert,
            ARRAY[sum(liike[1]), sum(liike[2]), sum(liike[3]), sum(liike[4]), sum(liike[5]), sum(liike[6])] as liike,
            ARRAY[sum(myymal[1]), sum(myymal[2]), sum(myymal[3]), sum(myymal[4]), sum(myymal[5]), sum(myymal[6])] as myymal,
            ARRAY[sum(majoit[1]), sum(majoit[2]), sum(majoit[3]), sum(majoit[4]), sum(majoit[5]), sum(majoit[6])] as majoit,
            ARRAY[sum(asla[1]), sum(asla[2]), sum(asla[3]), sum(asla[4]), sum(asla[5]), sum(asla[6])] as asla,
            ARRAY[sum(ravint[1]), sum(ravint[2]), sum(ravint[3]), sum(ravint[4]), sum(ravint[5]), sum(ravint[6])] as ravint,
            ARRAY[sum(tsto[1]), sum(tsto[2]), sum(tsto[3]), sum(tsto[4]), sum(tsto[5]), sum(tsto[6])] as tsto,
            ARRAY[sum(liiken[1]), sum(liiken[2]), sum(liiken[3]), sum(liiken[4]), sum(liiken[5]), sum(liiken[6])] as liiken,
            ARRAY[sum(hoito[1]), sum(hoito[2]), sum(hoito[3]), sum(hoito[4]), sum(hoito[5]), sum(hoito[6])] as hoito,
            ARRAY[sum(kokoon[1]), sum(kokoon[2]), sum(kokoon[3]), sum(kokoon[4]), sum(kokoon[5]), sum(kokoon[6])] as kokoon,
            ARRAY[sum(opetus[1]), sum(opetus[2]), sum(opetus[3]), sum(opetus[4]), sum(opetus[5]), sum(opetus[6])] as opetus,
            ARRAY[sum(teoll[1]), sum(teoll[2]), sum(teoll[3]), sum(teoll[4]), sum(teoll[5]), sum(teoll[6])] as teoll,
            ARRAY[sum(varast[1]), sum(varast[2]), sum(varast[3]), sum(varast[4]), sum(varast[5]), sum(varast[6])] as varast,
            ARRAY[sum(muut[1]), sum(muut[2]), sum(muut[3]), sum(muut[4]), sum(muut[5]), sum(muut[6])] as muut
        FROM (SELECT t.xyind, t.rakv, t.energiam,
        
                (CASE WHEN t.erpien_ala IS NOT NULL AND NOT(t.erpien_ala <= 0) THEN ARRAY(SELECT t.erpien_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'erpien' AND lammitysmuoto = t.energiam)
                )) END) as erpien,
                (CASE WHEN t.rivita_ala IS NOT NULL AND NOT(t.rivita_ala <= 0) THEN ARRAY(SELECT t.rivita_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'rivita' AND lammitysmuoto = t.energiam)
                )) END) as rivita,
                (CASE WHEN t.askert_ala IS NOT NULL AND NOT(t.askert_ala <= 0) THEN ARRAY(SELECT t.askert_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'askert' AND lammitysmuoto = t.energiam)
                )) END) as askert, 
                (CASE WHEN t.liike_ala IS NOT NULL AND NOT(t.liike_ala <= 0) THEN ARRAY(SELECT t.liike_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as liike,
                (CASE WHEN t.myymal_ala IS NOT NULL AND NOT(t.myymal_ala <= 0) THEN ARRAY(SELECT t.myymal_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as myymal,
                (CASE WHEN t.majoit_ala IS NOT NULL AND NOT(t.majoit_ala <= 0) THEN ARRAY(SELECT t.majoit_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as majoit,
                (CASE WHEN t.asla_ala IS NOT NULL AND NOT(t.asla_ala <= 0) THEN ARRAY(SELECT t.asla_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as asla,
                (CASE WHEN t.ravint_ala IS NOT NULL AND NOT(t.ravint_ala <= 0) THEN ARRAY(SELECT t.ravint_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as ravint,
                (CASE WHEN t.tsto_ala IS NOT NULL AND NOT(t.tsto_ala <= 0) THEN ARRAY(SELECT t.tsto_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'tsto' AND lammitysmuoto = t.energiam)
                )) END) as tsto, 
                (CASE WHEN t.liiken_ala IS NOT NULL AND NOT(t.liiken_ala <= 0) THEN ARRAY(SELECT t.liiken_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liiken' AND lammitysmuoto = t.energiam)
                )) END) as liiken,
                (CASE WHEN t.hoito_ala IS NOT NULL AND NOT(t.hoito_ala <= 0) THEN ARRAY(SELECT t.hoito_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'hoito' AND lammitysmuoto = t.energiam)
                )) END) as hoito,
                (CASE WHEN t.kokoon_ala IS NOT NULL AND NOT(t.kokoon_ala <= 0) THEN ARRAY(SELECT t.kokoon_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'kokoon' AND lammitysmuoto = t.energiam)
                )) END) as kokoon,
                (CASE WHEN t.opetus_ala IS NOT NULL AND NOT(t.opetus_ala <= 0) THEN ARRAY(SELECT t.opetus_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'opetus' AND lammitysmuoto = t.energiam)
                )) END) as opetus,
                (CASE WHEN t.teoll_ala IS NOT NULL AND NOT(t.teoll_ala <= 0) THEN ARRAY(SELECT t.teoll_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'teoll' AND lammitysmuoto = t.energiam)
                )) END) as teoll,
                (CASE WHEN t.varast_ala IS NOT NULL AND NOT(t.varast_ala <= 0) THEN ARRAY(SELECT t.varast_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'varast' AND lammitysmuoto = t.energiam)
                )) END) as varast,
                (CASE WHEN t.muut_ala IS NOT NULL AND NOT(t.muut_ala <= 0) THEN ARRAY(SELECT t.muut_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'muut' AND lammitysmuoto = t.energiam)
                )) END) as muut
            FROM rak_temp t WHERE t.rakv != 0
            ) sq
        GROUP BY sq.rakv, sq.xyind)

        SELECT rak_temp.xyind, rak_temp.rakv, rak_temp.energiam, -- Seuraaviin voisi rakentaa kytkimen, jolla alle nollan menevät NULLAtaan, mutta nyt jätetty pois koska moiset pudotetaan laskennassa pois joka tapauksessa
            NULL::int as rakyht_ala, 
            NULL::int as asuin_ala,
            NULLIF(COALESCE(rak_temp.erpien_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN erpien[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN erpien[2]
                WHEN rak_temp.energiam = 'kaasu' THEN erpien[3]
                WHEN rak_temp.energiam = 'sahko' THEN erpien[4]
                WHEN rak_temp.energiam = 'puu' THEN erpien[5]
                WHEN rak_temp.energiam = 'maalampo' THEN erpien[6]
                ELSE 0 END),0)::int
            as erpien_ala,
            NULLIF(COALESCE(rak_temp.rivita_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN rivita[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN rivita[2]
                WHEN rak_temp.energiam = 'kaasu' THEN rivita[3]
                WHEN rak_temp.energiam = 'sahko' THEN rivita[4]
                WHEN rak_temp.energiam = 'puu' THEN rivita[5]
                WHEN rak_temp.energiam = 'maalampo' THEN rivita[6]
                ELSE 0 END),0)::int
            as rivita_ala,
            NULLIF(COALESCE(rak_temp.askert_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN askert[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN askert[2]
                WHEN rak_temp.energiam = 'kaasu' THEN askert[3]
                WHEN rak_temp.energiam = 'sahko' THEN askert[4]
                WHEN rak_temp.energiam = 'puu' THEN askert[5]
                WHEN rak_temp.energiam = 'maalampo' THEN askert[6]
                ELSE 0 END),0)::int
            as askert_ala,
            NULLIF(COALESCE(rak_temp.liike_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN liike[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN liike[2]
                WHEN rak_temp.energiam = 'kaasu' THEN liike[3]
                WHEN rak_temp.energiam = 'sahko' THEN liike[4]
                WHEN rak_temp.energiam = 'puu' THEN liike[5]
                WHEN rak_temp.energiam = 'maalampo' THEN liike[6]
                ELSE 0 END),0)::int
            as liike_ala,
            NULLIF(COALESCE(rak_temp.myymal_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN myymal[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN myymal[2]
                WHEN rak_temp.energiam = 'kaasu' THEN myymal[3]
                WHEN rak_temp.energiam = 'sahko' THEN myymal[4]
                WHEN rak_temp.energiam = 'puu' THEN myymal[5]
                WHEN rak_temp.energiam = 'maalampo' THEN myymal[6]
                ELSE 0 END),0)::int
            as myymal_ala,
            NULLIF(COALESCE(rak_temp.majoit_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN majoit[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN majoit[2]
                WHEN rak_temp.energiam = 'kaasu' THEN majoit[3]
                WHEN rak_temp.energiam = 'sahko' THEN majoit[4]
                WHEN rak_temp.energiam = 'puu' THEN majoit[5]
                WHEN rak_temp.energiam = 'maalampo' THEN majoit[6]
                ELSE 0 END),0)::int
            as majoit_ala,
            NULLIF(COALESCE(rak_temp.asla_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN asla[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN asla[2]
                WHEN rak_temp.energiam = 'kaasu' THEN asla[3]
                WHEN rak_temp.energiam = 'sahko' THEN asla[4]
                WHEN rak_temp.energiam = 'puu' THEN asla[5]
                WHEN rak_temp.energiam = 'maalampo' THEN asla[6]
                ELSE 0 END),0)::int
            as asla_ala,
            NULLIF(COALESCE(rak_temp.ravint_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN ravint[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN ravint[2]
                WHEN rak_temp.energiam = 'kaasu' THEN ravint[3]
                WHEN rak_temp.energiam = 'sahko' THEN ravint[4]
                WHEN rak_temp.energiam = 'puu' THEN ravint[5]
                WHEN rak_temp.energiam = 'maalampo' THEN ravint[6]
                ELSE 0 END),0)::int
            as ravint_ala,
            NULLIF(COALESCE(rak_temp.tsto_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN tsto[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN tsto[2]
                WHEN rak_temp.energiam = 'kaasu' THEN tsto[3]
                WHEN rak_temp.energiam = 'sahko' THEN tsto[4]
                WHEN rak_temp.energiam = 'puu' THEN tsto[5]
                WHEN rak_temp.energiam = 'maalampo' THEN tsto[6]
                ELSE 0 END),0)::int
            as tsto_ala,
            NULLIF(COALESCE(rak_temp.liiken_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN liiken[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN liiken[2]
                WHEN rak_temp.energiam = 'kaasu' THEN liiken[3]
                WHEN rak_temp.energiam = 'sahko' THEN liiken[4]
                WHEN rak_temp.energiam = 'puu' THEN liiken[5]
                WHEN rak_temp.energiam = 'maalampo' THEN liiken[6]
                ELSE 0 END),0)::int
            as liiken_ala,
            NULLIF(COALESCE(rak_temp.hoito_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN hoito[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN hoito[2]
                WHEN rak_temp.energiam = 'kaasu' THEN hoito[3]
                WHEN rak_temp.energiam = 'sahko' THEN hoito[4]
                WHEN rak_temp.energiam = 'puu' THEN hoito[5]
                WHEN rak_temp.energiam = 'maalampo' THEN hoito[6]
                ELSE 0 END),0)::int
            as hoito_ala,
            NULLIF(COALESCE(rak_temp.kokoon_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN kokoon[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN kokoon[2]
                WHEN rak_temp.energiam = 'kaasu' THEN kokoon[3]
                WHEN rak_temp.energiam = 'sahko' THEN kokoon[4]
                WHEN rak_temp.energiam = 'puu' THEN kokoon[5]
                WHEN rak_temp.energiam = 'maalampo' THEN kokoon[6]
                ELSE 0 END),0)::int
            as kokoon_ala,
            NULLIF(COALESCE(rak_temp.opetus_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN opetus[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN opetus[2]
                WHEN rak_temp.energiam = 'kaasu' THEN opetus[3]
                WHEN rak_temp.energiam = 'sahko' THEN opetus[4]
                WHEN rak_temp.energiam = 'puu' THEN opetus[5]
                WHEN rak_temp.energiam = 'maalampo' THEN opetus[6]
                ELSE 0 END),0)::int
            as opetus_ala,
            NULLIF(COALESCE(rak_temp.teoll_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN teoll[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN teoll[2]
                WHEN rak_temp.energiam = 'kaasu' THEN teoll[3]
                WHEN rak_temp.energiam = 'sahko' THEN teoll[4]
                WHEN rak_temp.energiam = 'puu' THEN teoll[5]
                WHEN rak_temp.energiam = 'maalampo' THEN teoll[6]
                ELSE 0 END),0)::int
            as teoll_ala,
            NULLIF(COALESCE(rak_temp.varast_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN varast[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN varast[2]
                WHEN rak_temp.energiam = 'kaasu' THEN varast[3]
                WHEN rak_temp.energiam = 'sahko' THEN varast[4]
                WHEN rak_temp.energiam = 'puu' THEN varast[5]
                WHEN rak_temp.energiam = 'maalampo' THEN varast[6]
                ELSE 0 END),0)::int
            as varast_ala,
            NULLIF(COALESCE(rak_temp.muut_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN muut[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN muut[2]
                WHEN rak_temp.energiam = 'kaasu' THEN muut[3]
                WHEN rak_temp.energiam = 'sahko' THEN muut[4]
                WHEN rak_temp.energiam = 'puu' THEN muut[5]
                WHEN rak_temp.energiam = 'maalampo' THEN muut[6]
                ELSE 0 END),0)::int
            as muut_ala
        FROM rak_temp
        LEFT JOIN muutos ON rak_temp.xyind = muutos.xyind AND rak_temp.rakv = muutos.rakv) query
        WHERE NOT (query.erpien_ala IS NULL AND query.rivita_ala IS NULL and query.askert_ala IS NULL and query.liike_ala IS NULL and query.tsto_ala IS NULL and query.hoito_ala IS NULL and query.liiken_ala IS NULL AND
            query.kokoon_ala IS NULL and query.opetus_ala IS NULL and query.teoll_ala IS NULL AND query.varast_ala IS NULL AND query.muut_ala IS NULL);

        UPDATE rak_new SET asuin_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0),
        rakyht_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0) + COALESCE(rak_new.liike_ala,0) + COALESCE(rak_new.tsto_ala,0) + COALESCE(rak_new.liiken_ala,0) +
        COALESCE(rak_new.hoito_ala,0) + COALESCE(rak_new.kokoon_ala,0) + COALESCE(rak_new.opetus_ala,0) + COALESCE(rak_new.teoll_ala,0) + COALESCE(rak_new.varast_ala,0) + COALESCE(rak_new.muut_ala,0);

        RETURN QUERY SELECT * FROM rak_new UNION SELECT * FROM rak WHERE rak.rakv >= 2019;
        DROP TABLE IF EXISTS ykr, rak, rak_new, rak_temp, local_jakauma, global_jakauma, kayttotapajakauma;

        /*
        EXCEPTION WHEN OTHERS THEN
            DROP TABLE IF EXISTS ykr, rak, rak_new, rak_temp, local_jakauma, global_jakauma, kayttotapajakauma;
        */

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_UpdateBuildingsRefined(
            rak_taulu regclass,
            ykr_taulu regclass,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            baseYear int,
            targetYear int,
            kehitysskenaario varchar -- PITKO:n mukainen kehitysskenaario
        )
        RETURNS TABLE (
            xyind varchar,
            rakv int,
            energiam varchar,
            rakyht_ala int,
            asuin_ala int,
            erpien_ala int,
            rivita_ala int,
            askert_ala int,
            liike_ala int,
            myymal_ala int,
                myymal_hyper_ala int,
                myymal_super_ala int,
                myymal_pien_ala int,
                myymal_muu_ala int,
            majoit_ala int,
            asla_ala int,
            ravint_ala int,
            tsto_ala int,
            liiken_ala int,
            hoito_ala int,
            kokoon_ala int,
            opetus_ala int,
            teoll_ala int,
                teoll_kaivos_ala int,
                teoll_elint_ala int,
                teoll_tekst_ala int,
                teoll_puu_ala int,
                teoll_paper_ala int,
                teoll_kemia_ala int,
                teoll_miner_ala int,
                teoll_mjalos_ala int,
                teoll_metal_ala int,
                teoll_kone_ala int,
                teoll_muu_ala int,
                teoll_energ_ala int,
                teoll_vesi_ala int,
                teoll_yhdysk_ala int,
            varast_ala int,
            muut_ala int
        ) AS $$
        DECLARE
            calculationYear integer;
            defaultdemolition boolean;
            energiamuoto varchar;
            laskentavuodet int[];
            laskenta_length int;
            step real;
            localweight real;
            globalweight real;
            teoll_koko real;
            varast_koko real;
        BEGIN

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
            WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
            ELSE calculationYears[1]
            END;

        -- energiamuodot := ARRAY [kaukolampo, kevyt_oljy, raskas_oljy, kaasu, sahko, puu, turve, hiili, maalampo, muu_lammitys];
        SELECT array(select generate_series(baseYear,targetYear)) INTO laskentavuodet;
        SELECT array_length(laskentavuodet,1) into laskenta_length;
        SELECT 1::real / laskenta_length INTO step;
        SELECT (calculationYear - baseYear + 1) * step INTO globalweight;
        SELECT 1 - globalweight INTO localweight;

        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS ykr AS SELECT xyind::varchar, zone, k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala, k_poistuma FROM %s WHERE (k_ap_ala IS NOT NULL AND k_ap_ala != 0) OR (k_ar_ala IS NOT NULL AND k_ar_ala != 0) OR (k_ak_ala IS NOT NULL AND k_ak_ala != 0) OR (k_muu_ala IS NOT NULL AND k_muu_ala != 0) OR (k_poistuma IS NOT NULL AND k_poistuma != 0)', ykr_taulu);
        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS rak AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, myymal_hyper_ala :: int, myymal_super_ala :: int, myymal_pien_ala :: int, myymal_muu_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, teoll_kaivos_ala :: int, teoll_elint_ala :: int, teoll_tekst_ala :: int, teoll_puu_ala :: int, teoll_paper_ala :: int, teoll_kemia_ala :: int, teoll_miner_ala :: int, teoll_mjalos_ala :: int, teoll_metal_ala :: int, teoll_kone_ala :: int, teoll_muu_ala :: int, teoll_energ_ala :: int, teoll_vesi_ala :: int, teoll_yhdysk_ala :: int, varast_ala :: int, muut_ala :: int FROM %s WHERE rakv::int != 0', rak_taulu);

        /* Haetaan globaalit lämmitysmuotojakaumat laskentavuodelle ja -skenaariolle */
        /* Fetching global heating ratios for current calculation year and scenario */
        CREATE TEMP TABLE IF NOT EXISTS global_jakauma AS
            SELECT rakennus_tyyppi, kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
            FROM built.distribution_heating_systems dhs
            WHERE dhs.year = calculationYear AND dhs.rakv = calculationYear AND dhs.scenario = kehitysskenaario;

        INSERT INTO global_jakauma (rakennus_tyyppi, kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys)
            SELECT 'rakyht', avg(kaukolampo), avg(kevyt_oljy), avg(kaasu), avg(sahko), avg(puu), avg(maalampo), avg(muu_lammitys)
            FROM global_jakauma;

        /* Puretaan rakennuksia  */
        /* Demolishing buildings */
        SELECT CASE WHEN k_poistuma > 999998 AND k_poistuma < 1000000 THEN true ELSE false END FROM ykr LIMIT 1 INTO defaultdemolition;

        UPDATE rak b SET
            erpien_ala = (CASE WHEN erpien > b.erpien_ala THEN 0 ELSE b.erpien_ala - erpien END),
            rivita_ala = (CASE WHEN rivita > b.rivita_ala THEN 0 ELSE b.rivita_ala - rivita END),
            askert_ala = (CASE WHEN askert > b.askert_ala THEN 0 ELSE b.askert_ala - askert END),
            liike_ala = (CASE WHEN liike > b.liike_ala THEN 0 ELSE b.liike_ala - liike END),
            myymal_ala = (CASE WHEN myymal > b.myymal_ala THEN 0 ELSE b.myymal_ala - myymal END),
                myymal_hyper_ala = (CASE WHEN myy_hyper > b.myymal_hyper_ala THEN 0 ELSE b.myymal_hyper_ala - myy_hyper END),
                myymal_super_ala = (CASE WHEN myy_super > b.myymal_super_ala THEN 0 ELSE b.myymal_super_ala - myy_super END),
                myymal_pien_ala = (CASE WHEN myy_pien > b.myymal_pien_ala THEN 0 ELSE b.myymal_pien_ala - myy_pien END),
                myymal_muu_ala = (CASE WHEN myy_muu > b.myymal_muu_ala THEN 0 ELSE b.myymal_muu_ala - myy_muu END),
            majoit_ala = (CASE WHEN majoit > b.majoit_ala THEN 0 ELSE b.majoit_ala - majoit END),
            asla_ala = (CASE WHEN asla > b.asla_ala THEN 0 ELSE b.asla_ala - asla END),
            ravint_ala = (CASE WHEN ravint > b.ravint_ala THEN 0 ELSE b.ravint_ala - ravint END),
            tsto_ala = (CASE WHEN tsto > b.tsto_ala THEN 0 ELSE b.tsto_ala - tsto END),
            liiken_ala = (CASE WHEN liiken > b.liiken_ala THEN 0 ELSE b.liiken_ala - liiken END),
            hoito_ala = (CASE WHEN hoito > b.hoito_ala THEN 0 ELSE b.hoito_ala - hoito END),
            kokoon_ala = (CASE WHEN kokoon > b.kokoon_ala THEN 0 ELSE b.kokoon_ala - kokoon END),
            opetus_ala = (CASE WHEN opetus > b.opetus_ala THEN 0 ELSE b.opetus_ala - opetus END),
            teoll_ala = (CASE WHEN teoll > b.teoll_ala THEN 0 ELSE b.teoll_ala - teoll END),
                teoll_kaivos_ala = (CASE WHEN teoll_kaivos > b.teoll_kaivos_ala THEN 0 ELSE b.teoll_kaivos_ala - teoll_kaivos END),
                teoll_elint_ala = (CASE WHEN teoll_elint > b.teoll_elint_ala THEN 0 ELSE b.teoll_elint_ala - teoll_elint END),
                teoll_tekst_ala = (CASE WHEN teoll_tekst > b.teoll_tekst_ala THEN 0 ELSE b.teoll_tekst_ala - teoll_tekst END),
                teoll_puu_ala = (CASE WHEN teoll_puu > b.teoll_puu_ala THEN 0 ELSE b.teoll_puu_ala - teoll_puu END),
                teoll_paper_ala = (CASE WHEN teoll_paper > b.teoll_paper_ala THEN 0 ELSE b.teoll_paper_ala - teoll_paper END),
                teoll_kemia_ala = (CASE WHEN teoll_kemia > b.teoll_kemia_ala THEN 0 ELSE b.teoll_kemia_ala - teoll_kemia END),
                teoll_miner_ala = (CASE WHEN teoll_miner > b.teoll_miner_ala THEN 0 ELSE b.teoll_miner_ala - teoll_miner END),
                teoll_mjalos_ala = (CASE WHEN teoll_mjalos > b.teoll_mjalos_ala THEN 0 ELSE b.teoll_mjalos_ala - teoll_mjalos END),
                teoll_metal_ala = (CASE WHEN teoll_metal > b.teoll_metal_ala THEN 0 ELSE b.teoll_metal_ala - teoll_metal END),
                teoll_kone_ala = (CASE WHEN teoll_kone > b.teoll_kone_ala THEN 0 ELSE b.teoll_kone_ala - teoll_kone END),
                teoll_muu_ala = (CASE WHEN teoll_muu > b.teoll_muu_ala THEN 0 ELSE b.teoll_muu_ala - teoll_muu END),
                teoll_energ_ala = (CASE WHEN teoll_energ > b.teoll_energ_ala THEN 0 ELSE b.teoll_energ_ala - teoll_energ END),
                teoll_vesi_ala = (CASE WHEN teoll_vesi > b.teoll_vesi_ala THEN 0 ELSE b.teoll_vesi_ala - teoll_vesi END),
                teoll_yhdysk_ala = (CASE WHEN teoll_yhdysk > b.teoll_yhdysk_ala THEN 0 ELSE b.teoll_yhdysk_ala - teoll_yhdysk END),
            varast_ala = (CASE WHEN varast > b.varast_ala THEN 0 ELSE b.varast_ala - varast END),
            muut_ala = (CASE WHEN muut > b.muut_ala THEN 0 ELSE b.muut_ala - muut END)
        FROM (
        WITH poistuma AS (
            SELECT ykr.xyind::varchar, (CASE WHEN defaultdemolition = TRUE THEN 0.0015 ELSE SUM(k_poistuma) END) AS poistuma FROM ykr GROUP BY ykr.xyind
        ),
        buildings AS (
            SELECT rakennukset.xyind, rakennukset.rakv,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.erpien_ala :: real ELSE rakennukset.erpien_ala :: real / NULLIF(grouped.rakyht_ala, 0) END erpien,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.rivita_ala :: real ELSE rakennukset.rivita_ala :: real / NULLIF(grouped.rakyht_ala, 0) END rivita,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.askert_ala :: real ELSE rakennukset.askert_ala :: real / NULLIF(grouped.rakyht_ala, 0) END askert,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.liike_ala :: real ELSE rakennukset.liike_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liike,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_ala :: real ELSE rakennukset.myymal_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myymal,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_hyper_ala :: real ELSE rakennukset.myymal_hyper_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_hyper,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_super_ala :: real ELSE rakennukset.myymal_super_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_super,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_pien_ala :: real ELSE rakennukset.myymal_pien_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_pien,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.myymal_muu_ala :: real ELSE rakennukset.myymal_muu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_muu,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.majoit_ala :: real ELSE rakennukset.majoit_ala :: real / NULLIF(grouped.rakyht_ala, 0) END majoit,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.asla_ala :: real ELSE rakennukset.asla_ala :: real / NULLIF(grouped.rakyht_ala, 0) END asla,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.ravint_ala :: real ELSE rakennukset.ravint_ala :: real / NULLIF(grouped.rakyht_ala, 0) END ravint,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.tsto_ala :: real ELSE rakennukset.tsto_ala :: real / NULLIF(grouped.rakyht_ala, 0) END tsto,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.liiken_ala :: real ELSE rakennukset.liiken_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liiken,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.hoito_ala :: real ELSE rakennukset.hoito_ala :: real / NULLIF(grouped.rakyht_ala, 0) END hoito,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.kokoon_ala :: real ELSE rakennukset.kokoon_ala :: real / NULLIF(grouped.rakyht_ala, 0) END kokoon,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.opetus_ala :: real ELSE rakennukset.opetus_ala :: real / NULLIF(grouped.rakyht_ala, 0) END opetus,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_ala :: real ELSE rakennukset.teoll_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_kaivos_ala :: real ELSE rakennukset.teoll_kaivos_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kaivos,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_elint_ala :: real ELSE rakennukset.teoll_elint_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_elint,	
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_tekst_ala :: real ELSE rakennukset.teoll_tekst_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_tekst,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_puu_ala :: real ELSE rakennukset.teoll_puu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_puu,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_paper_ala :: real ELSE rakennukset.teoll_paper_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_paper,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_kemia_ala :: real ELSE rakennukset.teoll_kemia_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kemia,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_miner_ala :: real ELSE rakennukset.teoll_miner_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_miner,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_mjalos_ala :: real ELSE rakennukset.teoll_mjalos_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_mjalos,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_metal_ala :: real ELSE rakennukset.teoll_metal_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_metal,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_kone_ala :: real ELSE rakennukset.teoll_kone_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kone,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_muu_ala :: real ELSE rakennukset.teoll_muu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_muu,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_energ_ala :: real ELSE rakennukset.teoll_energ_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_energ,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_vesi_ala :: real ELSE rakennukset.teoll_vesi_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_vesi,
                    CASE WHEN defaultdemolition = TRUE THEN rakennukset.teoll_yhdysk_ala :: real ELSE rakennukset.teoll_yhdysk_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_yhdysk,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.varast_ala :: real ELSE rakennukset.varast_ala:: real / NULLIF(grouped.rakyht_ala, 0) END varast,
                CASE WHEN defaultdemolition = TRUE THEN rakennukset.muut_ala :: real ELSE rakennukset.muut_ala :: real / NULLIF(grouped.rakyht_ala, 0) END muut
            FROM rak rakennukset JOIN
            (SELECT build2.xyind::varchar, SUM(build2.rakyht_ala) rakyht_ala FROM rak build2 GROUP BY build2.xyind) grouped
            ON grouped.xyind = rakennukset.xyind
            WHERE rakennukset.rakv != calculationYear
        )
        SELECT poistuma.xyind,
            buildings.rakv,
            poistuma * erpien erpien,
            poistuma * rivita rivita,
            poistuma * askert askert,
            poistuma * liike liike,
            poistuma * myymal myymal,
                poistuma * myy_hyper myy_hyper,
                poistuma * myy_super myy_super,
                poistuma * myy_pien myy_pien,
                poistuma * myy_muu myy_muu,
            poistuma * majoit majoit,
            poistuma * asla asla,
            poistuma * ravint ravint,
            poistuma * tsto tsto,
            poistuma * liiken liiken,
            poistuma * hoito hoito,
            poistuma * kokoon kokoon,
            poistuma * opetus opetus,
            poistuma * teoll teoll,
                poistuma * teoll_kaivos teoll_kaivos,
                poistuma * teoll_elint teoll_elint,	
                poistuma * teoll_tekst teoll_tekst,
                poistuma * teoll_puu teoll_puu,
                poistuma * teoll_paper teoll_paper,
                poistuma * teoll_kemia teoll_kemia,
                poistuma * teoll_miner teoll_miner,
                poistuma * teoll_mjalos teoll_mjalos,
                poistuma * teoll_metal teoll_metal,
                poistuma * teoll_kone teoll_kone,
                poistuma * teoll_muu teoll_muu,
                poistuma * teoll_energ teoll_energ,
                poistuma * teoll_vesi teoll_vesi,
                poistuma * teoll_yhdysk teoll_yhdysk,
            poistuma * varast varast,
            poistuma * muut muut
        FROM poistuma LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
        WHERE poistuma > 0 AND buildings.rakv IS NOT NULL) poistumat
        WHERE b.xyind = poistumat.xyind AND b.rakv = poistumat.rakv;


        /* Lisätään puuttuvat sarakkeet väliaikaiseen YKR-dataan */
        /* Adding new columns into the temporary YKR data */
        ALTER TABLE ykr
            ADD COLUMN liike_osuus real,
            ADD COLUMN myymal_osuus real,
            ADD COLUMN majoit_osuus real,
            ADD COLUMN asla_osuus real,
            ADD COLUMN ravint_osuus real,
            ADD COLUMN tsto_osuus real,
            ADD COLUMN liiken_osuus real,
            ADD COLUMN hoito_osuus real,
            ADD COLUMN kokoon_osuus real,
            ADD COLUMN opetus_osuus real,
            ADD COLUMN teoll_osuus real,
            ADD COLUMN varast_osuus real,
            ADD COLUMN muut_osuus real,
            ADD COLUMN muu_ala real;

        /* Lasketaan myös vakiokäyttötapausjakaumat uusia alueita varten */
        /* Käyttöalaperusteinen käyttötapajakauma generoidaan rakennusdatasta UZ-vyöhykkeittäin */
        /* Calculate default proportions of building usage for new areas as well */
        CREATE TEMP TABLE IF NOT EXISTS kayttotapajakauma AS 
        SELECT ykr.zone,
            COALESCE(SUM(r.liike_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liike_osuus,
            COALESCE(SUM(r.myymal_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as myymal_osuus,
            COALESCE(SUM(r.majoit_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as majoit_osuus,
            COALESCE(SUM(r.asla_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as asla_osuus,
            COALESCE(SUM(r.ravint_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as ravint_osuus,
            COALESCE(SUM(r.tsto_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as tsto_osuus,
            COALESCE(SUM(r.liiken_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liiken_osuus,
            COALESCE(SUM(r.hoito_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as hoito_osuus,
            COALESCE(SUM(r.kokoon_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as kokoon_osuus,
            COALESCE(SUM(r.opetus_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as opetus_osuus,
            COALESCE(SUM(r.teoll_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as teoll_osuus,
            COALESCE(SUM(r.varast_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as varast_osuus,
            COALESCE(SUM(r.muut_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as muut_osuus
        FROM rak r JOIN ykr ON r.xyind = ykr.xyind
        GROUP BY ykr.zone;

        UPDATE kayttotapajakauma j SET 
            liike_osuus = ktj.liike_osuus,
            myymal_osuus = ktj.myymal_osuus,
            majoit_osuus = ktj.majoit_osuus,
            asla_osuus = ktj.asla_osuus,
            ravint_osuus = ktj.ravint_osuus,
            tsto_osuus = ktj.tsto_osuus,
            liiken_osuus = ktj.liiken_osuus,
            hoito_osuus = ktj.hoito_osuus,
            kokoon_osuus = ktj.kokoon_osuus,
            opetus_osuus = ktj.opetus_osuus,
            teoll_osuus = ktj.teoll_osuus,
            varast_osuus = ktj.varast_osuus,
            muut_osuus = ktj.muut_osuus
        FROM
        (SELECT
            AVG(k.liike_osuus) liike_osuus, AVG(k.myymal_osuus) myymal_osuus, AVG(k.majoit_osuus) majoit_osuus, AVG(k.asla_osuus) asla_osuus, AVG(k.ravint_osuus) ravint_osuus,
            AVG(k.tsto_osuus) tsto_osuus, AVG(k.liiken_osuus) liiken_osuus, AVG(k.hoito_osuus) hoito_osuus, AVG(k.kokoon_osuus) kokoon_osuus, AVG(k.opetus_osuus) opetus_osuus,
            AVG(k.teoll_osuus) teoll_osuus, AVG(k.varast_osuus) varast_osuus, AVG(k.muut_osuus) muut_osuus
        FROM kayttotapajakauma k
            WHERE k.liike_osuus + k.tsto_osuus + k.liiken_osuus + k.hoito_osuus + k.kokoon_osuus + k.opetus_osuus + k.teoll_osuus + k.varast_osuus + k.muut_osuus = 1
        ) ktj
        WHERE j.liike_osuus + j.tsto_osuus + j.liiken_osuus + j.hoito_osuus + j.kokoon_osuus + j.opetus_osuus + j.teoll_osuus + j.varast_osuus + j.muut_osuus < 0.99;

        UPDATE ykr y SET
            liike_osuus = ktj.liike_osuus,
            myymal_osuus = ktj.myymal_osuus,
            majoit_osuus = ktj.majoit_osuus,
            asla_osuus = ktj.asla_osuus,
            ravint_osuus = ktj.ravint_osuus,
            tsto_osuus = ktj.tsto_osuus,
            liiken_osuus = ktj.liiken_osuus,
            hoito_osuus = ktj.hoito_osuus,
            kokoon_osuus = ktj.kokoon_osuus,
            opetus_osuus = ktj.opetus_osuus,
            teoll_osuus = ktj.teoll_osuus,
            varast_osuus = ktj.varast_osuus,
            muut_osuus = ktj.muut_osuus
        FROM kayttotapajakauma ktj
        WHERE y.zone = ktj.zone;

        /* Lasketaan nykyisen paikallisesta rakennusdatasta muodostetun ruutuaineiston mukainen ruutukohtainen energiajakauma rakennustyypeittäin */
        /* Laskenta tehdään vain 2000-luvulta eteenpäin rakennetuille tai rakennettaville rakennuksille */
        CREATE TEMP TABLE IF NOT EXISTS local_jakauma AS
        WITH cte AS (
        WITH
            index AS (
            SELECT distinct on (ykr.xyind) ykr.xyind::varchar FROM ykr
            ), kaukolampo AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert,
                SUM(rak.liike_ala) as liike,
                SUM(rak.tsto_ala) as tsto,
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='kaukolampo' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), kevyt_oljy AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='kevyt_oljy' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), kaasu AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='kaasu' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), sahko AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='sahko' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), puu AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='puu' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), maalampo AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert, 
                SUM(rak.liike_ala) as liike, 
                SUM(rak.tsto_ala) as tsto, 
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,		 
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='maalampo' AND rak.rakv > 2000
            GROUP BY rak.xyind
            ), muu_lammitys AS (
            SELECT rak.xyind,
                SUM(rak.rakyht_ala) as rakyht,
                SUM(rak.erpien_ala) as erpien,
                SUM(rak.rivita_ala) as rivita,
                SUM(rak.askert_ala) as askert,
                SUM(rak.liike_ala) as liike,
                SUM(rak.tsto_ala) as tsto,
                SUM(rak.liiken_ala) as liiken,
                SUM(rak.hoito_ala) as hoito,
                SUM(rak.kokoon_ala) as kokoon,
                SUM(rak.opetus_ala) as opetus,
                SUM(rak.teoll_ala) as teoll,
                SUM(rak.varast_ala) as varast,
                SUM(rak.muut_ala) as muut
            FROM rak WHERE rak.energiam='muu_lammitys' AND rak.rakv > 2000
            GROUP BY rak.xyind
        )
            
        SELECT index.xyind, 'rakyht' as rakennus_tyyppi,
        kaukolampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kaukolampo,
        kevyt_oljy.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kevyt_oljy,
        kaasu.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kaasu,
        sahko.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS sahko,
        puu.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS puu,
        maalampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS maalampo,
        muu_lammitys.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(kevyt_oljy.rakyht,0) + COALESCE(kaasu.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'erpien' as rakennus_tyyppi,
        kaukolampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kaukolampo,
        kevyt_oljy.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kevyt_oljy,
        kaasu.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kaasu,
        sahko.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS sahko,
        puu.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS puu,
        maalampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS maalampo,
        muu_lammitys.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(kevyt_oljy.erpien,0) + COALESCE(kaasu.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'rivita' as rakennus_tyyppi,
        kaukolampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kaukolampo,
        kevyt_oljy.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kevyt_oljy,
        kaasu.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kaasu,
        sahko.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS sahko,
        puu.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS puu,
        maalampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS maalampo,
        muu_lammitys.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(kevyt_oljy.rivita,0) + COALESCE(kaasu.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind
            
        UNION
        SELECT index.xyind, 'askert' as rakennus_tyyppi,
        kaukolampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kaukolampo,
        kevyt_oljy.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kevyt_oljy,
        kaasu.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kaasu,
        sahko.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS sahko,
        puu.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS puu,
        maalampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS maalampo,
        muu_lammitys.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(kevyt_oljy.askert,0) + COALESCE(kaasu.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind
            
        UNION
        SELECT index.xyind, 'liike' as rakennus_tyyppi,
        kaukolampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kaukolampo,
        kevyt_oljy.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kevyt_oljy,
        kaasu.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kaasu,
        sahko.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS sahko,
        puu.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS puu,
        maalampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS maalampo,
        muu_lammitys.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(kevyt_oljy.liike,0) + COALESCE(kaasu.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'tsto' as rakennus_tyyppi,
        kaukolampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kaukolampo,
        kevyt_oljy.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kevyt_oljy,
        kaasu.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kaasu,
        sahko.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS sahko,
        puu.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS puu,
        maalampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS maalampo,
        muu_lammitys.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(kevyt_oljy.tsto,0) + COALESCE(kaasu.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'liiken' as rakennus_tyyppi,
        kaukolampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kaukolampo,
        kevyt_oljy.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kevyt_oljy,
        kaasu.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kaasu,
        sahko.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS sahko,
        puu.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS puu,
        maalampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS maalampo,
        muu_lammitys.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(kevyt_oljy.liiken,0) + COALESCE(kaasu.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind  
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'hoito' as rakennus_tyyppi,
        kaukolampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kaukolampo,
        kevyt_oljy.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kevyt_oljy,
        kaasu.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kaasu,
        sahko.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS sahko,
        puu.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS puu,
        maalampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS maalampo,
        muu_lammitys.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(kevyt_oljy.hoito,0) + COALESCE(kaasu.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'kokoon' as rakennus_tyyppi,
        kaukolampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kaukolampo,
        kevyt_oljy.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kevyt_oljy,
        kaasu.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kaasu,
        sahko.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS sahko,
        puu.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS puu,
        maalampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS maalampo,
        muu_lammitys.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(kevyt_oljy.kokoon,0) + COALESCE(kaasu.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'opetus' as rakennus_tyyppi,
        kaukolampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kaukolampo,
        kevyt_oljy.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kevyt_oljy,
        kaasu.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kaasu,
        sahko.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS sahko,
        puu.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS puu,
        maalampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS maalampo,
        muu_lammitys.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(kevyt_oljy.opetus,0) + COALESCE(kaasu.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION 
        SELECT index.xyind, 'teoll' as rakennus_tyyppi,
        kaukolampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kaukolampo,
        kevyt_oljy.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kevyt_oljy,
        kaasu.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kaasu,
        sahko.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS sahko,
        puu.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS puu,
        maalampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS maalampo,
        muu_lammitys.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(kevyt_oljy.teoll,0) + COALESCE(kaasu.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind 
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind 
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind 

        UNION 
        SELECT index.xyind, 'varast' as rakennus_tyyppi,
        kaukolampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kaukolampo,
        kevyt_oljy.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kevyt_oljy,
        kaasu.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kaasu,
        sahko.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS sahko,
        puu.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS puu,
        maalampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS maalampo,
        muu_lammitys.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(kevyt_oljy.varast,0) + COALESCE(kaasu.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind 
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind 
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind

        UNION
        SELECT index.xyind, 'muut' as rakennus_tyyppi,
        kaukolampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kaukolampo,
        kevyt_oljy.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kevyt_oljy,
        kaasu.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kaasu,
        sahko.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS sahko,
        puu.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS puu,
        maalampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS maalampo,
        muu_lammitys.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(kevyt_oljy.muut,0) + COALESCE(kaasu.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS muu_lammitys
        FROM index
            FULL OUTER JOIN kaukolampo ON kaukolampo.xyind = index.xyind
            FULL OUTER JOIN kevyt_oljy ON kevyt_oljy.xyind = index.xyind
            FULL OUTER JOIN kaasu ON kaasu.xyind = index.xyind
            FULL OUTER JOIN sahko ON sahko.xyind = index.xyind
            FULL OUTER JOIN puu ON puu.xyind = index.xyind
            FULL OUTER JOIN maalampo ON maalampo.xyind = index.xyind
            FULL OUTER JOIN muu_lammitys ON muu_lammitys.xyind = index.xyind
        )
        SELECT * FROM cte;

        /* Päivitetään paikallisen lämmitysmuotojakauman ja kansallisen lämmitysmuotojakauman erot */
        /* Updating differences between local and "global" heating distributions */
        UPDATE local_jakauma l SET
        kaukolampo = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kaukolampo ELSE localweight * COALESCE(l.kaukolampo,0) + globalweight * g.kaukolampo END),
        kevyt_oljy = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kevyt_oljy ELSE localweight * COALESCE(l.kevyt_oljy,0) + globalweight * g.kevyt_oljy END),
        kaasu = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.kaasu ELSE localweight * COALESCE(l.kaasu,0) + globalweight * g.kaasu END),
        sahko = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.sahko ELSE localweight * COALESCE(l.sahko,0) + globalweight * g.sahko END),
        puu = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.puu ELSE localweight* COALESCE(l.puu,0) + globalweight * g.puu END),
        maalampo = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.maalampo ELSE localweight * COALESCE(l.maalampo,0) + globalweight * g.maalampo END),
        muu_lammitys = (CASE WHEN
            l.kaukolampo IS NULL AND l.kevyt_oljy IS NULL AND l.kaasu IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN
            g.muu_lammitys ELSE localweight * COALESCE(l.muu_lammitys,0) + globalweight * g.muu_lammitys END)
        FROM global_jakauma g
        WHERE l.rakennus_tyyppi =  g.rakennus_tyyppi;


        /* Rakennetaan uudet rakennukset energiamuodoittain */
        /* Building new buildings, per primary energy source */
        FOREACH energiamuoto IN ARRAY ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys']
        LOOP

            WITH cte AS (
            WITH
                indeksi AS (
                    SELECT DISTINCT ON (l.xyind) l.xyind FROM local_jakauma l
                ),
                erpien_lammitysmuoto AS (
                    SELECT l.xyind,
                        (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as erpien FROM local_jakauma l WHERE rakennus_tyyppi = 'erpien' ),
                rivita_lammitysmuoto AS ( SELECT l.xyind, 
                    (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as rivita FROM local_jakauma l WHERE rakennus_tyyppi = 'rivita' ),
                askert_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as askert FROM local_jakauma l WHERE rakennus_tyyppi = 'askert' ),
                liike_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as liike FROM local_jakauma l WHERE rakennus_tyyppi = 'liike' ),
                tsto_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as tsto FROM local_jakauma l WHERE rakennus_tyyppi = 'tsto' ),
                liiken_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as liiken FROM local_jakauma l WHERE rakennus_tyyppi = 'liiken' ),
                hoito_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as hoito FROM local_jakauma l WHERE rakennus_tyyppi = 'hoito' ),
                kokoon_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as kokoon FROM local_jakauma l WHERE rakennus_tyyppi = 'kokoon' ),
                opetus_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as opetus FROM local_jakauma l WHERE rakennus_tyyppi = 'opetus' ),
                teoll_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as teoll FROM local_jakauma l WHERE rakennus_tyyppi = 'teoll' ),
                varast_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as varast FROM local_jakauma l WHERE rakennus_tyyppi = 'varast' ),
                muut_lammitysmuoto AS ( SELECT l.xyind, (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) as muut FROM local_jakauma l WHERE rakennus_tyyppi = 'muut' )
            SELECT indeksi.*,
                    COALESCE(erpien,(SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'erpien'))	AS erpien,
                    COALESCE(rivita, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'rivita'))	AS rivita,
                    COALESCE(askert, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'askert'))	AS askert,
                    COALESCE(liike, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'liike'))	AS liike,
                    COALESCE(tsto, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'tsto'))	AS tsto,
                    COALESCE(liiken, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'liiken'))	AS liiken,
                    COALESCE(hoito, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'hoito'))	AS hoito,
                    COALESCE(kokoon, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'kokoon'))	AS kokoon,
                    COALESCE(opetus, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'opetus'))	AS opetus,
                    COALESCE(teoll, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'teoll'))	AS teoll,
                    COALESCE(varast, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'varast'))	AS varast,
                    COALESCE(muut, (SELECT (CASE WHEN energiamuoto = 'kaukolampo' THEN kaukolampo WHEN
                            energiamuoto IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN kevyt_oljy WHEN
                            energiamuoto = 'kaasu' THEN kaasu WHEN
                            energiamuoto = 'sahko' THEN sahko WHEN
                            energiamuoto = 'puu' THEN puu WHEN
                            energiamuoto = 'maalampo' THEN maalampo WHEN
                            energiamuoto = 'muu_lammitys' THEN muu_lammitys END
                        ) FROM global_jakauma WHERE rakennus_tyyppi = 'muut'))	AS muut
                FROM indeksi
                    LEFT JOIN erpien_lammitysmuoto ON erpien_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN rivita_lammitysmuoto ON rivita_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN askert_lammitysmuoto ON askert_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN liike_lammitysmuoto ON liike_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN tsto_lammitysmuoto ON tsto_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN liiken_lammitysmuoto ON liiken_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN hoito_lammitysmuoto ON hoito_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN kokoon_lammitysmuoto ON kokoon_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN opetus_lammitysmuoto ON opetus_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN teoll_lammitysmuoto ON teoll_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN varast_lammitysmuoto ON varast_lammitysmuoto.xyind = indeksi.xyind
                    LEFT JOIN muut_lammitysmuoto ON muut_lammitysmuoto.xyind = indeksi.xyind
            )
            INSERT INTO rak (xyind, rakv, energiam, rakyht_ala, asuin_ala, erpien_ala, rivita_ala, askert_ala, liike_ala, myymal_ala, myymal_hyper_ala, myymal_super_ala, myymal_pien_ala, myymal_muu_ala, majoit_ala, asla_ala, ravint_ala, tsto_ala, liiken_ala, hoito_ala, kokoon_ala, opetus_ala, teoll_ala, teoll_kaivos_ala, teoll_elint_ala, teoll_tekst_ala, teoll_puu_ala, teoll_paper_ala, teoll_kemia_ala, teoll_miner_ala, teoll_mjalos_ala, teoll_metal_ala, teoll_kone_ala, teoll_muu_ala, teoll_energ_ala, teoll_vesi_ala, teoll_yhdysk_ala, varast_ala, muut_ala)
            SELECT
                ykr.xyind, -- xyind
                calculationYear, -- rakv
                energiamuoto, -- energiam
                NULL::int, -- rakyht_ala
                NULL::int, -- asuin_ala
                CASE WHEN k_ap_ala * erpien > 0.4 AND k_ap_ala * erpien < 1 THEN 1 ELSE k_ap_ala * erpien END, -- erpien_ala
                CASE WHEN k_ar_ala * rivita > 0.4 AND k_ar_ala * rivita < 1 THEN 1 ELSE k_ar_ala * rivita END, -- rivita_ala
                CASE WHEN k_ak_ala * askert > 0.4 AND k_ak_ala * askert < 1 THEN 1 ELSE k_ak_ala * askert END, -- askert_ala
                CASE WHEN liike_osuus * k_muu_ala * liike > 0.4 AND liike_osuus * k_muu_ala * liike < 1 THEN 1 ELSE liike_osuus * k_muu_ala * liike END, -- liike_ala
                CASE WHEN myymal_osuus * k_muu_ala * liike > 0.4 AND myymal_osuus * k_muu_ala * liike < 1 THEN 1 ELSE myymal_osuus * k_muu_ala * liike END, --myymal_ala
                    NULL::int, -- myymal_hyper_ala
                    NULL::int, -- myymal_super_ala
                    NULL::int, -- myymal_pien_ala
                    NULL::int, -- myymal_muu_ala	
                CASE WHEN majoit_osuus * k_muu_ala * liike > 0.4 AND majoit_osuus * k_muu_ala * liike < 1 THEN 1 ELSE majoit_osuus * k_muu_ala * liike END, -- majoit_ala
                CASE WHEN asla_osuus * k_muu_ala * liike > 0.4 AND asla_osuus * k_muu_ala * liike < 1 THEN 1 ELSE asla_osuus * k_muu_ala * liike END, -- asla_ala
                CASE WHEN ravint_osuus * k_muu_ala * liike > 0.4 AND ravint_osuus * k_muu_ala * liike < 1 THEN 1 ELSE ravint_osuus * k_muu_ala * liike END, -- ravint_ala
                CASE WHEN tsto_osuus * k_muu_ala * tsto > 0.4 AND tsto_osuus * k_muu_ala * tsto < 1 THEN 1 ELSE tsto_osuus * k_muu_ala * tsto END, -- tsto_ala
                CASE WHEN liiken_osuus * k_muu_ala * liiken > 0.4 AND liiken_osuus * k_muu_ala * liiken < 1 THEN 1 ELSE liiken_osuus * k_muu_ala * liiken END, -- liiken_ala
                CASE WHEN hoito_osuus * k_muu_ala * hoito > 0.4 AND hoito_osuus * k_muu_ala * hoito < 1 THEN 1 ELSE hoito_osuus * k_muu_ala * hoito END, -- hoito_ala
                CASE WHEN kokoon_osuus * k_muu_ala * kokoon > 0.4 AND kokoon_osuus * k_muu_ala * kokoon < 1 THEN 1 ELSE kokoon_osuus * k_muu_ala * kokoon END, -- kokoon_ala
                CASE WHEN opetus_osuus * k_muu_ala * opetus > 0.4 AND opetus_osuus * k_muu_ala * opetus < 1 THEN 1 ELSE opetus_osuus * k_muu_ala * opetus END, -- opetus_ala
                CASE WHEN teoll_osuus * k_muu_ala * teoll > 0.4 AND teoll_osuus * k_muu_ala * teoll < 1 THEN 1 ELSE teoll_osuus * k_muu_ala * teoll END, -- teoll_ala
                    NULL::int, -- teoll_kaivos_ala,
                    NULL::int, -- teoll_elint_ala,
                    NULL::int, -- teoll_tekst_ala,
                    NULL::int, -- teoll_puu_ala,
                    NULL::int, -- teoll_paper_ala,
                    NULL::int, -- teoll_kemia_ala,
                    NULL::int, -- teoll_miner_ala,
                    NULL::int, -- teoll_mjalos_ala,
                    NULL::int, -- teoll_metal_ala,
                    NULL::int, -- teoll_kone_ala,
                    NULL::int, -- teoll_muu_ala,
                    NULL::int, -- teoll_energ_ala,
                    NULL::int, -- teoll_vesi_ala,
                    NULL::int, -- teoll_yhdysk_ala,
                CASE WHEN varast_osuus * k_muu_ala * varast > 0.4 AND varast_osuus * k_muu_ala * varast < 1 THEN 1 ELSE varast_osuus * k_muu_ala * varast END, -- varast_ala
                CASE WHEN muut_osuus * k_muu_ala * muut > 0.4 AND muut_osuus * k_muu_ala * muut < 1 THEN 1 ELSE muut_osuus * k_muu_ala * muut END -- muut_ala
            FROM ykr LEFT JOIN cte on ykr.xyind = cte.xyind;

        END LOOP;

        UPDATE rak SET
            asuin_ala = COALESCE(rak.erpien_ala,0) + COALESCE(rak.rivita_ala,0) + COALESCE(rak.askert_ala,0)
        WHERE rak.rakv = calculationYear AND rak.asuin_ala IS NULL;

        UPDATE rak SET
            rakyht_ala = COALESCE(rak.asuin_ala,0) + COALESCE(rak.liike_ala,0) + COALESCE(rak.tsto_ala,0) + COALESCE(rak.liiken_ala,0) +
            COALESCE(rak.hoito_ala,0) + COALESCE(rak.kokoon_ala,0) + COALESCE(rak.opetus_ala, 0) + COALESCE(rak.teoll_ala, 0) +
            COALESCE(rak.varast_ala, 0) + COALESCE(rak.muut_ala, 0) 
        WHERE rak.rakv = calculationYear AND rak.rakyht_ala IS NULL;

        DELETE FROM rak WHERE rak.rakyht_ala = 0;

        CREATE TEMP TABLE IF NOT EXISTS tol_osuudet AS SELECT
            DISTINCT ON (rak.xyind) rak.xyind,
            COALESCE(SUM(rak.myymal_hyper_ala) / NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_hyper_osuus,
            COALESCE(SUM(rak.myymal_super_ala) / NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_super_osuus,
            COALESCE(SUM(rak.myymal_pien_ala) /  NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_pien_osuus,
            COALESCE(SUM(rak.myymal_muu_ala) /  NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_muu_osuus,
            COALESCE(SUM(rak.teoll_kaivos_ala) /  NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kaivos_osuus,
            COALESCE(SUM(rak.teoll_elint_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_elint_osuus,
            COALESCE(SUM(rak.teoll_tekst_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_tekst_osuus,
            COALESCE(SUM(rak.teoll_puu_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_puu_osuus,
            COALESCE(SUM(rak.teoll_paper_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_paper_osuus,
            COALESCE(SUM(rak.teoll_kemia_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kemia_osuus,
            COALESCE(SUM(rak.teoll_miner_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_miner_osuus,
            COALESCE(SUM(rak.teoll_mjalos_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_mjalos_osuus,
            COALESCE(SUM(rak.teoll_metal_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_metal_osuus,
            COALESCE(SUM(rak.teoll_kone_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kone_osuus,
            COALESCE(SUM(rak.teoll_muu_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_muu_osuus,
            COALESCE(SUM(rak.teoll_energ_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_energ_osuus,
            COALESCE(SUM(rak.teoll_vesi_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_vesi_osuus,
            COALESCE(SUM(rak.teoll_yhdysk_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_yhdys_osuus
        FROM rak WHERE rak.rakv < calculationYear GROUP BY rak.xyind;

        UPDATE rak SET
            myymal_hyper_ala = rak.myymal_ala * COALESCE(tol.myymal_hyper_osuus, 0.065),
            myymal_super_ala = rak.myymal_ala * COALESCE(tol.myymal_super_osuus, 0.075),
            myymal_pien_ala = rak.myymal_ala * COALESCE(tol.myymal_pien_osuus, 0.04),
            myymal_muu_ala = rak.myymal_ala * COALESCE(tol.myymal_muu_osuus, 0.82),
            teoll_kaivos_ala = rak.teoll_ala * COALESCE(tol.teoll_kaivos_osuus, 0),
            teoll_elint_ala = rak.teoll_ala * COALESCE(tol.teoll_elint_osuus, 0.02),
            teoll_tekst_ala = rak.teoll_ala * COALESCE(tol.teoll_tekst_osuus, 0.015),
            teoll_puu_ala = rak.teoll_ala * COALESCE(tol.teoll_puu_osuus, 0.0015),
            teoll_paper_ala = rak.teoll_ala * COALESCE(tol.teoll_paper_osuus, 0.005),
            teoll_kemia_ala = rak.teoll_ala * COALESCE(tol.teoll_kemia_osuus, 0.009),
            teoll_miner_ala = rak.teoll_ala * COALESCE(tol.teoll_miner_osuus, 0.002),
            teoll_mjalos_ala = rak.teoll_ala * COALESCE(tol.teoll_mjalos_osuus, 0.0007),
            teoll_metal_ala = rak.teoll_ala * COALESCE(tol.teoll_metal_osuus, 0.05),
            teoll_kone_ala = rak.teoll_ala * COALESCE(tol.teoll_kone_osuus, 0.115),
            teoll_muu_ala = rak.teoll_ala * COALESCE(tol.teoll_muu_osuus, 0.777),
            teoll_energ_ala = rak.teoll_ala * COALESCE(tol.teoll_energ_osuus, 0.0037),
            teoll_vesi_ala = rak.teoll_ala * COALESCE(tol.teoll_vesi_osuus, 0.0001),
            teoll_yhdysk_ala = rak.teoll_ala * COALESCE(tol.teoll_yhdys_osuus, 0.01)
        FROM tol_osuudet tol WHERE rak.rakv = calculationYear AND tol.xyind = rak.xyind;

        /* Päivitetään vanhojen pytinkien lämmitysmuodot */
        /* Updating heating characteristics of old buildings */

        CREATE TEMP TABLE IF NOT EXISTS rak_temp AS
        SELECT DISTINCT ON (r.xyind, r.rakv, energiam) r.xyind, r.rakv,
        UNNEST(
            CASE WHEN muu_lammitys IS NULL AND kevyt_oljy IS NULL AND kaasu IS NULL THEN
                ARRAY['kaukolampo', 'sahko', 'puu', 'maalampo'] 
            WHEN muu_lammitys IS NULL AND kaasu IS NULL THEN
                ARRAY['kaukolampo', 'kevyt_oljy', 'sahko', 'puu', 'maalampo'] 
            WHEN muu_lammitys IS NULL THEN
                ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo']
            ELSE ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys'] END
        )::varchar AS energiam,
        NULL::int AS rakyht_ala,
        NULL::int AS asuin_ala,
        NULL::int AS erpien_ala,
        NULL::int AS rivita_ala,
        NULL::int AS askert_ala,
        NULL::int AS liike_ala,
        NULL::int AS myymal_ala,
            NULL::int AS myymal_hyper_ala,
            NULL::int AS myymal_super_ala,
            NULL::int AS myymal_pien_ala,
            NULL::int AS myymal_muu_ala,
        NULL::int AS majoit_ala,
        NULL::int AS asla_ala,
        NULL::int AS ravint_ala, 
        NULL::int AS tsto_ala,
        NULL::int AS liiken_ala,
        NULL::int AS hoito_ala,
        NULL::int AS kokoon_ala,
        NULL::int AS opetus_ala,
        NULL::int AS teoll_ala,
            NULL::int AS teoll_kaivos_ala,
            NULL::int AS teoll_elint_ala,
            NULL::int AS teoll_tekst_ala,
            NULL::int AS teoll_puu_ala,
            NULL::int AS teoll_paper_ala,
            NULL::int AS teoll_kemia_ala,
            NULL::int AS teoll_miner_ala,
            NULL::int AS teoll_mjalos_ala,
            NULL::int AS teoll_metal_ala,
            NULL::int AS teoll_kone_ala,
            NULL::int AS teoll_muu_ala,
            NULL::int AS teoll_energ_ala,
            NULL::int AS teoll_vesi_ala,
            NULL::int AS teoll_yhdysk_ala,
        NULL::int AS varast_ala,
        NULL::int AS muut_ala 
        FROM rak r
        LEFT JOIN 
        (WITH
            kaukolampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='kaukolampo'),
            kevyt_oljy AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili')),
            kaasu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='kaasu'),
            sahko AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='sahko'),
            puu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='puu'),
            maalampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='maalampo'),
            muu_lammitys AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='muu_lammitys')
        SELECT distinct on (r2.xyind, r2.rakv) r2.xyind, r2.rakv,
            kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
        FROM rak r2
            LEFT JOIN kaukolampo on r2.xyind = kaukolampo.xyind AND r2.rakv = kaukolampo.rakv AND r2.xyind IN (SELECT kaukolampo.xyind FROM kaukolampo) AND r2.rakv IN (SELECT kaukolampo.rakv FROM kaukolampo)
            LEFT JOIN kevyt_oljy on r2.xyind = kevyt_oljy.xyind AND r2.rakv = kevyt_oljy.rakv AND r2.xyind IN (SELECT kevyt_oljy.xyind FROM kevyt_oljy) AND r2.rakv IN (SELECT kevyt_oljy.rakv FROM kevyt_oljy)
            LEFT JOIN kaasu on r2.xyind = kaasu.xyind AND r2.rakv = kaasu.rakv AND r2.xyind IN (SELECT kaasu.xyind FROM kaasu) AND r2.rakv IN (SELECT kaasu.rakv FROM kaasu)
            LEFT JOIN sahko on r2.xyind = sahko.xyind AND r2.rakv = sahko.rakv AND r2.xyind IN (SELECT sahko.xyind FROM sahko) AND r2.rakv IN (SELECT sahko.rakv FROM sahko)
            LEFT JOIN puu on r2.xyind = puu.xyind AND r2.rakv = puu.rakv AND r2.xyind IN (SELECT puu.xyind FROM puu) AND r2.rakv IN (SELECT puu.rakv FROM puu)
            LEFT JOIN maalampo on r2.xyind = maalampo.xyind AND r2.rakv = maalampo.rakv AND r2.xyind IN (SELECT maalampo.xyind FROM maalampo) AND r2.rakv IN (SELECT maalampo.rakv FROM maalampo)
            LEFT JOIN muu_lammitys on r2.xyind = muu_lammitys.xyind AND r2.rakv = muu_lammitys.rakv AND r2.xyind IN (SELECT muu_lammitys.xyind FROM muu_lammitys) AND r2.rakv IN (SELECT muu_lammitys.rakv FROM muu_lammitys)
        WHERE r2.rakv < 2019
            ) sq 
        ON sq.xyind = r.xyind AND sq.rakv = r.rakv where r.rakv < 2019;

        UPDATE rak_temp set rakyht_ala = past.rakyht_ala,
            asuin_ala = past.asuin_ala, erpien_ala = past.erpien_ala, rivita_ala = past.rivita_ala, askert_ala = past.askert_ala, liike_ala = past.liike_ala, myymal_ala = past.myymal_ala,
            myymal_hyper_ala = past.myymal_hyper_ala, myymal_super_ala = past.myymal_super_ala, myymal_pien_ala = past.myymal_pien_ala, myymal_muu_ala = past.myymal_muu_ala,
            majoit_ala = past.majoit_ala, asla_ala = past.asla_ala, ravint_ala = past.ravint_ala,  tsto_ala = past.tsto_ala, liiken_ala = past.liiken_ala, hoito_ala = past.hoito_ala, kokoon_ala = past.kokoon_ala,
            opetus_ala = past.opetus_ala, teoll_ala = past.teoll_ala, 
            teoll_kaivos_ala = past.teoll_kaivos_ala, teoll_elint_ala = past.teoll_elint_ala, teoll_tekst_ala = past.teoll_tekst_ala, teoll_puu_ala = past.teoll_puu_ala,
            teoll_paper_ala = past.teoll_paper_ala, teoll_kemia_ala = past.teoll_kemia_ala, teoll_miner_ala = past.teoll_miner_ala, teoll_mjalos_ala = past.teoll_mjalos_ala,
            teoll_metal_ala = past.teoll_metal_ala, teoll_kone_ala = past.teoll_kone_ala, teoll_muu_ala = past.teoll_muu_ala, teoll_energ_ala = past.teoll_energ_ala, 
            teoll_vesi_ala = past.teoll_vesi_ala, teoll_yhdysk_ala = past.teoll_yhdysk_ala,
            varast_ala = past.varast_ala, muut_ala = past.muut_ala
        FROM rak past WHERE rak_temp.xyind = past.xyind AND rak_temp.rakv = past.rakv AND rak_temp.energiam = past.energiam;

        CREATE TEMP TABLE IF NOT EXISTS rak_new AS 
        SELECT * FROM
        (WITH
        muutos AS (
        SELECT sq.xyind, sq.rakv,
            ARRAY[sum(erpien[1]), sum(erpien[2]), sum(erpien[3]), sum(erpien[4]), sum(erpien[5]), sum(erpien[6]), sum(erpien[7])] as erpien,
            ARRAY[sum(rivita[1]), sum(rivita[2]), sum(rivita[3]), sum(rivita[4]), sum(rivita[5]), sum(rivita[6]), sum(rivita[7])] as rivita,
            ARRAY[sum(askert[1]), sum(askert[2]), sum(askert[3]), sum(askert[4]), sum(askert[5]), sum(askert[6]), sum(askert[7])] as askert,
            ARRAY[sum(liike[1]), sum(liike[2]), sum(liike[3]), sum(liike[4]), sum(liike[5]), sum(liike[6]), sum(liike[7])] as liike,
            ARRAY[sum(myymal[1]), sum(myymal[2]), sum(myymal[3]), sum(myymal[4]), sum(myymal[5]), sum(myymal[6]), sum(myymal[7])] as myymal,
            ARRAY[sum(majoit[1]), sum(majoit[2]), sum(majoit[3]), sum(majoit[4]), sum(majoit[5]), sum(majoit[6]), sum(majoit[7])] as majoit,
            ARRAY[sum(asla[1]), sum(asla[2]), sum(asla[3]), sum(asla[4]), sum(asla[5]), sum(asla[6]), sum(asla[7])] as asla,
            ARRAY[sum(ravint[1]), sum(ravint[2]), sum(ravint[3]), sum(ravint[4]), sum(ravint[5]), sum(ravint[6]), sum(ravint[7])] as ravint,
            ARRAY[sum(tsto[1]), sum(tsto[2]), sum(tsto[3]), sum(tsto[4]), sum(tsto[5]), sum(tsto[6]), sum(tsto[7])] as tsto,
            ARRAY[sum(liiken[1]), sum(liiken[2]), sum(liiken[3]), sum(liiken[4]), sum(liiken[5]), sum(liiken[6]), sum(liiken[7])] as liiken,
            ARRAY[sum(hoito[1]), sum(hoito[2]), sum(hoito[3]), sum(hoito[4]), sum(hoito[5]), sum(hoito[6]), sum(hoito[7])] as hoito,
            ARRAY[sum(kokoon[1]), sum(kokoon[2]), sum(kokoon[3]), sum(kokoon[4]), sum(kokoon[5]), sum(kokoon[6]), sum(kokoon[7])] as kokoon,
            ARRAY[sum(opetus[1]), sum(opetus[2]), sum(opetus[3]), sum(opetus[4]), sum(opetus[5]), sum(opetus[6]), sum(opetus[7])] as opetus,
            ARRAY[sum(teoll[1]), sum(teoll[2]), sum(teoll[3]), sum(teoll[4]), sum(teoll[5]), sum(teoll[6]), sum(teoll[7])] as teoll,
            ARRAY[sum(varast[1]), sum(varast[2]), sum(varast[3]), sum(varast[4]), sum(varast[5]), sum(varast[6]), sum(varast[7])] as varast,
            ARRAY[sum(muut[1]), sum(muut[2]), sum(muut[3]), sum(muut[4]), sum(muut[5]), sum(muut[6]), sum(muut[7])] as muut
        FROM (SELECT t.xyind, t.rakv, t.energiam,
        
                (CASE WHEN t.erpien_ala IS NOT NULL AND NOT(t.erpien_ala <= 0) THEN ARRAY(SELECT t.erpien_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'erpien' AND lammitysmuoto = t.energiam)
                )) END) as erpien,
                (CASE WHEN t.rivita_ala IS NOT NULL AND NOT(t.rivita_ala <= 0) THEN ARRAY(SELECT t.rivita_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'rivita' AND lammitysmuoto = t.energiam)
                )) END) as rivita,
                (CASE WHEN t.askert_ala IS NOT NULL AND NOT(t.askert_ala <= 0) THEN ARRAY(SELECT t.askert_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'askert' AND lammitysmuoto = t.energiam)
                )) END) as askert, 
                (CASE WHEN t.liike_ala IS NOT NULL AND NOT(t.liike_ala <= 0) THEN ARRAY(SELECT t.liike_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as liike,
                (CASE WHEN t.myymal_ala IS NOT NULL AND NOT(t.myymal_ala <= 0) THEN ARRAY(SELECT t.myymal_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as myymal,
                (CASE WHEN t.majoit_ala IS NOT NULL AND NOT(t.majoit_ala <= 0) THEN ARRAY(SELECT t.majoit_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as majoit,
                (CASE WHEN t.asla_ala IS NOT NULL AND NOT(t.asla_ala <= 0) THEN ARRAY(SELECT t.asla_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as asla,
                (CASE WHEN t.ravint_ala IS NOT NULL AND NOT(t.ravint_ala <= 0) THEN ARRAY(SELECT t.ravint_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
                )) END) as ravint,
                (CASE WHEN t.tsto_ala IS NOT NULL AND NOT(t.tsto_ala <= 0) THEN ARRAY(SELECT t.tsto_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'tsto' AND lammitysmuoto = t.energiam)
                )) END) as tsto, 
                (CASE WHEN t.liiken_ala IS NOT NULL AND NOT(t.liiken_ala <= 0) THEN ARRAY(SELECT t.liiken_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liiken' AND lammitysmuoto = t.energiam)
                )) END) as liiken,
                (CASE WHEN t.hoito_ala IS NOT NULL AND NOT(t.hoito_ala <= 0) THEN ARRAY(SELECT t.hoito_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'hoito' AND lammitysmuoto = t.energiam)
                )) END) as hoito,
                (CASE WHEN t.kokoon_ala IS NOT NULL AND NOT(t.kokoon_ala <= 0) THEN ARRAY(SELECT t.kokoon_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'kokoon' AND lammitysmuoto = t.energiam)
                )) END) as kokoon,
                (CASE WHEN t.opetus_ala IS NOT NULL AND NOT(t.opetus_ala <= 0) THEN ARRAY(SELECT t.opetus_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'opetus' AND lammitysmuoto = t.energiam)
                )) END) as opetus,
                (CASE WHEN t.teoll_ala IS NOT NULL AND NOT(t.teoll_ala <= 0) THEN ARRAY(SELECT t.teoll_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'teoll' AND lammitysmuoto = t.energiam)
                )) END) as teoll,
                (CASE WHEN t.varast_ala IS NOT NULL AND NOT(t.varast_ala <= 0) THEN ARRAY(SELECT t.varast_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'varast' AND lammitysmuoto = t.energiam)
                )) END) as varast,
                (CASE WHEN t.muut_ala IS NOT NULL AND NOT(t.muut_ala <= 0) THEN ARRAY(SELECT t.muut_ala * 
                    UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'muut' AND lammitysmuoto = t.energiam)
                )) END) as muut
            FROM rak_temp t WHERE t.rakv != 0
            ) sq
        GROUP BY sq.rakv, sq.xyind)

        SELECT rak_temp.xyind, rak_temp.rakv, rak_temp.energiam, -- Seuraaviin voisi rakentaa kytkimen, jolla alle nollan menevät NULLAtaan, mutta nyt jätetty pois koska moiset pudotetaan laskennassa pois joka tapauksessa
            NULL::int as rakyht_ala, 
            NULL::int as asuin_ala,
            NULLIF(COALESCE(rak_temp.erpien_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN erpien[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN erpien[2]
                WHEN rak_temp.energiam = 'kaasu' THEN erpien[3]
                WHEN rak_temp.energiam = 'sahko' THEN erpien[4]
                WHEN rak_temp.energiam = 'puu' THEN erpien[5]
                WHEN rak_temp.energiam = 'maalampo' THEN erpien[6]
                ELSE 0 END),0)::int
            as erpien_ala,
            NULLIF(COALESCE(rak_temp.rivita_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN rivita[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN rivita[2]
                WHEN rak_temp.energiam = 'kaasu' THEN rivita[3]
                WHEN rak_temp.energiam = 'sahko' THEN rivita[4]
                WHEN rak_temp.energiam = 'puu' THEN rivita[5]
                WHEN rak_temp.energiam = 'maalampo' THEN rivita[6]
                ELSE 0 END),0)::int
            as rivita_ala,
            NULLIF(COALESCE(rak_temp.askert_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN askert[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN askert[2]
                WHEN rak_temp.energiam = 'kaasu' THEN askert[3]
                WHEN rak_temp.energiam = 'sahko' THEN askert[4]
                WHEN rak_temp.energiam = 'puu' THEN askert[5]
                WHEN rak_temp.energiam = 'maalampo' THEN askert[6]
                ELSE 0 END),0)::int
            as askert_ala,
            NULLIF(COALESCE(rak_temp.liike_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN liike[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN liike[2]
                WHEN rak_temp.energiam = 'kaasu' THEN liike[3]
                WHEN rak_temp.energiam = 'sahko' THEN liike[4]
                WHEN rak_temp.energiam = 'puu' THEN liike[5]
                WHEN rak_temp.energiam = 'maalampo' THEN liike[6]
                ELSE 0 END),0)::int
            as liike_ala,
            NULLIF(COALESCE(rak_temp.myymal_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN myymal[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN myymal[2]
                WHEN rak_temp.energiam = 'kaasu' THEN myymal[3]
                WHEN rak_temp.energiam = 'sahko' THEN myymal[4]
                WHEN rak_temp.energiam = 'puu' THEN myymal[5]
                WHEN rak_temp.energiam = 'maalampo' THEN myymal[6]
                ELSE 0 END),0)::int
            as myymal_ala,
            NULL::int AS myymal_hyper_ala,
            NULL::int AS myymal_super_ala,
            NULL::int AS myymal_pien_ala,
            NULL::int AS myymal_muu_ala,
            NULLIF(COALESCE(rak_temp.majoit_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN majoit[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN majoit[2]
                WHEN rak_temp.energiam = 'kaasu' THEN majoit[3]
                WHEN rak_temp.energiam = 'sahko' THEN majoit[4]
                WHEN rak_temp.energiam = 'puu' THEN majoit[5]
                WHEN rak_temp.energiam = 'maalampo' THEN majoit[6]
                ELSE 0 END),0)::int
            as majoit_ala,
            NULLIF(COALESCE(rak_temp.asla_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN asla[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN asla[2]
                WHEN rak_temp.energiam = 'kaasu' THEN asla[3]
                WHEN rak_temp.energiam = 'sahko' THEN asla[4]
                WHEN rak_temp.energiam = 'puu' THEN asla[5]
                WHEN rak_temp.energiam = 'maalampo' THEN asla[6]
                ELSE 0 END),0)::int
            as asla_ala,
            NULLIF(COALESCE(rak_temp.ravint_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN ravint[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN ravint[2]
                WHEN rak_temp.energiam = 'kaasu' THEN ravint[3]
                WHEN rak_temp.energiam = 'sahko' THEN ravint[4]
                WHEN rak_temp.energiam = 'puu' THEN ravint[5]
                WHEN rak_temp.energiam = 'maalampo' THEN ravint[6]
                ELSE 0 END),0)::int
            as ravint_ala,
            NULLIF(COALESCE(rak_temp.tsto_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN tsto[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN tsto[2]
                WHEN rak_temp.energiam = 'kaasu' THEN tsto[3]
                WHEN rak_temp.energiam = 'sahko' THEN tsto[4]
                WHEN rak_temp.energiam = 'puu' THEN tsto[5]
                WHEN rak_temp.energiam = 'maalampo' THEN tsto[6]
                ELSE 0 END),0)::int
            as tsto_ala,
            NULLIF(COALESCE(rak_temp.liiken_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN liiken[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN liiken[2]
                WHEN rak_temp.energiam = 'kaasu' THEN liiken[3]
                WHEN rak_temp.energiam = 'sahko' THEN liiken[4]
                WHEN rak_temp.energiam = 'puu' THEN liiken[5]
                WHEN rak_temp.energiam = 'maalampo' THEN liiken[6]
                ELSE 0 END),0)::int
            as liiken_ala,
            NULLIF(COALESCE(rak_temp.hoito_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN hoito[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN hoito[2]
                WHEN rak_temp.energiam = 'kaasu' THEN hoito[3]
                WHEN rak_temp.energiam = 'sahko' THEN hoito[4]
                WHEN rak_temp.energiam = 'puu' THEN hoito[5]
                WHEN rak_temp.energiam = 'maalampo' THEN hoito[6]
                ELSE 0 END),0)::int
            as hoito_ala,
            NULLIF(COALESCE(rak_temp.kokoon_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN kokoon[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN kokoon[2]
                WHEN rak_temp.energiam = 'kaasu' THEN kokoon[3]
                WHEN rak_temp.energiam = 'sahko' THEN kokoon[4]
                WHEN rak_temp.energiam = 'puu' THEN kokoon[5]
                WHEN rak_temp.energiam = 'maalampo' THEN kokoon[6]
                ELSE 0 END),0)::int
            as kokoon_ala,
            NULLIF(COALESCE(rak_temp.opetus_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN opetus[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN opetus[2]
                WHEN rak_temp.energiam = 'kaasu' THEN opetus[3]
                WHEN rak_temp.energiam = 'sahko' THEN opetus[4]
                WHEN rak_temp.energiam = 'puu' THEN opetus[5]
                WHEN rak_temp.energiam = 'maalampo' THEN opetus[6]
                ELSE 0 END),0)::int
            as opetus_ala,
            NULLIF(COALESCE(rak_temp.teoll_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN teoll[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN teoll[2]
                WHEN rak_temp.energiam = 'kaasu' THEN teoll[3]
                WHEN rak_temp.energiam = 'sahko' THEN teoll[4]
                WHEN rak_temp.energiam = 'puu' THEN teoll[5]
                WHEN rak_temp.energiam = 'maalampo' THEN teoll[6]
                ELSE 0 END),0)::int
            as teoll_ala,
            NULL::int AS teoll_kaivos_ala,
            NULL::int AS teoll_elint_ala,
            NULL::int AS teoll_tekst_ala,
            NULL::int AS teoll_puu_ala,
            NULL::int AS teoll_paper_ala,
            NULL::int AS teoll_kemia_ala,
            NULL::int AS teoll_miner_ala,
            NULL::int AS teoll_mjalos_ala,
            NULL::int AS teoll_metal_ala,
            NULL::int AS teoll_kone_ala,
            NULL::int AS teoll_muu_ala,
            NULL::int AS teoll_energ_ala,
            NULL::int AS teoll_vesi_ala,
            NULL::int AS teoll_yhdysk_ala,
            NULLIF(COALESCE(rak_temp.varast_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN varast[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN varast[2]
                WHEN rak_temp.energiam = 'kaasu' THEN varast[3]
                WHEN rak_temp.energiam = 'sahko' THEN varast[4]
                WHEN rak_temp.energiam = 'puu' THEN varast[5]
                WHEN rak_temp.energiam = 'maalampo' THEN varast[6]
                ELSE 0 END),0)::int
            as varast_ala,
            NULLIF(COALESCE(rak_temp.muut_ala, 0) + (CASE
                WHEN rak_temp.energiam = 'kaukolampo' THEN muut[1]
                WHEN rak_temp.energiam = 'kevyt_oljy' THEN muut[2]
                WHEN rak_temp.energiam = 'kaasu' THEN muut[3]
                WHEN rak_temp.energiam = 'sahko' THEN muut[4]
                WHEN rak_temp.energiam = 'puu' THEN muut[5]
                WHEN rak_temp.energiam = 'maalampo' THEN muut[6]
                ELSE 0 END),0)::int
            as muut_ala
            
        FROM rak_temp
        LEFT JOIN muutos ON rak_temp.xyind = muutos.xyind AND rak_temp.rakv = muutos.rakv) query
        WHERE NOT (query.erpien_ala IS NULL AND query.rivita_ala IS NULL and query.askert_ala IS NULL and query.liike_ala IS NULL and query.tsto_ala IS NULL and query.hoito_ala IS NULL and query.liiken_ala IS NULL AND
            query.kokoon_ala IS NULL and query.opetus_ala IS NULL and query.teoll_ala IS NULL AND query.varast_ala IS NULL AND query.muut_ala IS NULL);

        UPDATE rak_new SET asuin_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0),
        rakyht_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0) + COALESCE(rak_new.liike_ala,0) + COALESCE(rak_new.tsto_ala,0) + COALESCE(rak_new.liiken_ala,0) +
        COALESCE(rak_new.hoito_ala,0) + COALESCE(rak_new.kokoon_ala,0) + COALESCE(rak_new.opetus_ala,0) + COALESCE(rak_new.teoll_ala,0) + COALESCE(rak_new.varast_ala,0) + COALESCE(rak_new.muut_ala,0);

        UPDATE rak_new SET
            myymal_hyper_ala = rak_new.myymal_ala * rak.myymal_hyper_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0), 
            myymal_super_ala = rak_new.myymal_ala * rak.myymal_super_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
            myymal_pien_ala = rak_new.myymal_ala * rak.myymal_pien_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
            myymal_muu_ala = rak_new.myymal_ala * rak.myymal_muu_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
            teoll_kaivos_ala = rak_new.teoll_ala * rak.teoll_kaivos_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_elint_ala = rak_new.teoll_ala * rak.teoll_elint_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_tekst_ala = rak_new.teoll_ala * rak.teoll_tekst_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_puu_ala = rak_new.teoll_ala * rak.teoll_puu_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_paper_ala = rak_new.teoll_ala * rak.teoll_paper_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_kemia_ala = rak_new.teoll_ala * rak.teoll_kemia_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_miner_ala = rak_new.teoll_ala * rak.teoll_miner_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_mjalos_ala = rak_new.teoll_ala * rak.teoll_mjalos_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_metal_ala = rak_new.teoll_ala * rak.teoll_metal_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_kone_ala = rak_new.teoll_ala * rak.teoll_kone_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_muu_ala = rak_new.teoll_ala * rak.teoll_muu_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_energ_ala = rak_new.teoll_ala * rak.teoll_energ_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_vesi_ala = rak_new.teoll_ala * rak.teoll_vesi_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
            teoll_yhdysk_ala = rak_new.teoll_ala * rak.teoll_yhdysk_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0)
        FROM rak WHERE rak.xyind = rak_new.xyind AND rak.energiam = rak_new.energiam AND rak.rakv = rak_new.rakv;

        UPDATE rak_new SET myymal_muu_ala = rak_new.myymal_ala
            WHERE rak_new.myymal_ala IS NOT NULL AND rak_new.myymal_hyper_ala IS NULL AND rak_new.myymal_super_ala IS NULL AND rak_new.myymal_pien_ala IS NULL AND rak_new.myymal_muu_ala IS NULL;

        UPDATE rak SET myymal_muu_ala = rak.myymal_ala
            WHERE rak.myymal_ala IS NOT NULL AND rak.myymal_hyper_ala IS NULL AND rak.myymal_super_ala IS NULL AND rak.myymal_pien_ala IS NULL AND rak.myymal_muu_ala IS NULL;

        UPDATE rak_new SET
            teoll_muu_ala = rak_new.teoll_ala WHERE
            (rak_new.teoll_kaivos_ala IS NULL OR rak_new.teoll_kaivos_ala = 0) AND
            (rak_new.teoll_elint_ala IS NULL OR rak_new.teoll_elint_ala = 0) AND
            (rak_new.teoll_tekst_ala IS NULL OR rak_new.teoll_tekst_ala = 0) AND
            (rak_new.teoll_puu_ala IS NULL OR rak_new.teoll_puu_ala = 0) AND
            (rak_new.teoll_paper_ala IS NULL OR rak_new.teoll_paper_ala = 0) AND
            (rak_new.teoll_kemia_ala IS NULL OR rak_new.teoll_kemia_ala = 0) AND
            (rak_new.teoll_miner_ala IS NULL OR rak_new.teoll_miner_ala = 0) AND
            (rak_new.teoll_mjalos_ala IS NULL OR rak_new.teoll_mjalos_ala = 0) AND
            (rak_new.teoll_metal_ala IS NULL OR rak_new.teoll_metal_ala = 0) AND
            (rak_new.teoll_kone_ala IS NULL OR rak_new.teoll_kone_ala = 0) AND
            (rak_new.teoll_energ_ala IS NULL OR rak_new.teoll_energ_ala = 0) AND
            (rak_new.teoll_vesi_ala IS NULL OR rak_new.teoll_vesi_ala = 0) AND
            (rak_new.teoll_yhdysk_ala IS NULL OR rak_new.teoll_yhdysk_ala = 0);

        UPDATE rak SET
            teoll_muu_ala = rak.teoll_ala WHERE
            (rak.teoll_kaivos_ala IS NULL OR rak.teoll_kaivos_ala = 0) AND
            (rak.teoll_elint_ala IS NULL OR rak.teoll_elint_ala = 0) AND
            (rak.teoll_tekst_ala IS NULL OR rak.teoll_tekst_ala = 0) AND
            (rak.teoll_puu_ala IS NULL OR rak.teoll_puu_ala = 0) AND
            (rak.teoll_paper_ala IS NULL OR rak.teoll_paper_ala = 0) AND
            (rak.teoll_kemia_ala IS NULL OR rak.teoll_kemia_ala = 0) AND
            (rak.teoll_miner_ala IS NULL OR rak.teoll_miner_ala = 0) AND
            (rak.teoll_mjalos_ala IS NULL OR rak.teoll_mjalos_ala = 0) AND
            (rak.teoll_metal_ala IS NULL OR rak.teoll_metal_ala = 0) AND
            (rak.teoll_kone_ala IS NULL OR rak.teoll_kone_ala = 0) AND
            (rak.teoll_energ_ala IS NULL OR rak.teoll_energ_ala = 0) AND
            (rak.teoll_vesi_ala IS NULL OR rak.teoll_vesi_ala = 0) AND
            (rak.teoll_yhdysk_ala IS NULL OR rak.teoll_yhdysk_ala = 0);

        RETURN QUERY SELECT * FROM rak_new UNION SELECT * FROM rak WHERE rak.rakv >= 2019;
        DROP TABLE IF EXISTS ykr, rak, rak_new, rak_temp, local_jakauma, global_jakauma, kayttotapajakauma, tol_osuudet;

        END;
        $$ LANGUAGE plpgsql;         
    """)
    op.execute("""
        /* Uudisrakentaminen (energia) | Construction of new buildings (energy)

        YKR-ruudun laskentavuoden uudisrakentamisen energian kasvihuonekaasupäästöt [CO2-ekv/a] lasketaan seuraavasti:

            rak_uusi_energia_co2 = rakennus_ala * rak_energia_gco2m2

        YKR-ruudun laskentavuoden uudisrakentamisen rakennustuotteiden kasvihuonekaasupäästöt rak_uusi_materia_co2 [CO2-ekv/a] lasketaan seuraavasti:
        
            rak_uusi_materia_co2 = rakennus_ala * rak_materia_gco2m2
        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildConstruct(
            floorSpace real, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna [m2]. Lukuarvo riippuu laskentavuodesta ja rakennuksen tyypistä.
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar, -- Rakennustyyppi, esim. 'erpien', 'rivita'
            calculationScenario varchar -- PITKO:n mukainen kehitysskenaario
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            construction_energy_gco2m2 real; -- Rakennustyypin rakentamisvaiheen työmaatoimintojen ja kuljetusten kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
            construction_materials_gco2m2 real; -- Rakennustyypin rakentamiseen tarvittujen rakennustuotteiden tuotantoprosessin välillisiä kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
        BEGIN

        /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
        IF floorSpace <= 0 OR floorSpace IS NULL THEN RETURN 0;
        /* In other cases continue with the calculation */
        ELSE
            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
        END;

        /* If the year of construction is not the current year of calculation, return 0 */
        --      IF rakennusvuosi != year THEN
        --        RETURN 0;
                /* Muussa tapauksessa jatka laskentaan */
                /* In other cases, continue */
        --    ELSE

            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen energiankulutuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for energy consumption of construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || buildingType || ' FROM built.build_new_construction_energy_gco2m2
                WHERE year = $1 AND scenario = $2 LIMIT 1'
                INTO construction_energy_gco2m2 USING calculationYear, calculationScenario;
            
            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen materiaalien valmistuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for production of materials for construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || CASE WHEN buildingType IN ('erpien', 'rivita', 'askert')
                THEN buildingType
                    ELSE 'muut'
                END || ' 
                    FROM built.build_materia_gco2m2
                    WHERE year = $1 AND scenario = $2 LIMIT 1'
                INTO construction_materials_gco2m2
                    USING calculationYear, calculationScenario;

            /* Lasketaan ja palautetaan päästöt CO2-ekvivalenttia [gCO2-ekv/v] */
            /* Calculate and return emissions as CO2-equivalents [gCO2-ekv/a] */
            RETURN floorSpace * 
                (COALESCE(construction_energy_gco2m2,0) + COALESCE(construction_materials_gco2m2, 0));
        --    END IF;
        END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten purkaminen (energia) | Demolition of buildings (energy)
        Rakennuksen elinkaaren katsotaan päättyvän, kun rakennus on purettu ja tontilta on
        kuljetettu pois kaikki rakennusmateriaalit ja tontti on valmis seuraavaa käyttöä varten.
        Päästölaskennassa huomioidaan rakennuksen purkutyön, puretun materiaalin jatkokäsittelykuljetusten
        ja sen loppukäsittelyn ja -sijoituksen energiaperäiset kasvihuonekaasupäästöt rak_purku_energia_co2 [CO2-ekv/a] seuraavasti

            rak_purku_energia_co2 = rakennukset_poistuma * rak_purku_energia_gco2m2
        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildDemolish(
            buildingsRemoval real, -- rakennustyypin (erpien, rivita, askert, liike, tsto, liiken, hoito, kokoon, opetus, teoll, varast, muut) kerrosalan poistuma YKR-ruudussa laskentavuonna [m2].
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            calculationScenario varchar -- PITKO-kehitysskenaario | PITKO development scenario
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            rak_purku_energia_gco2m2 real; -- [gCO2-ekv/m2] on rakennustyypin purkamisen, puretun materiaalin kuljetusten ja niiden käsittelyn kasvihuonekaasujen ominaispäästöt yhtä purettua kerroskerrosneliötä kohti. Lukuarvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
        BEGIN

        /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
        /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
        IF buildingsRemoval <= 0 OR buildingsRemoval IS NULL THEN
            RETURN 0;
        /* Muussa tapauksessa jatka laskentaan */
        /* In other cases continue with the calculation */
        ELSE
            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
            END;
            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen energiankulutuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for energy consumption of construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || buildingType || ' 
                FROM built.build_demolish_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                INTO rak_purku_energia_gco2m2
                    USING calculationScenario, calculationYear;
            
            /* Lasketaan ja palautetaan päästöt CO2-ekvivalentteina [gCO2-ekv/v] */
            /* Calculate and return emissions as CO2-equivalents [gCO2-ekv/a] */
            RETURN buildingsRemoval * COALESCE(rak_purku_energia_gco2m2, 0);

        END IF;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Korjausrakentamisen ja saneeraamisen päästöt | Emissions from renovations and large scale overhauls of buildings

        Rakennusten käytön aikana tehtävien tavanomaisten korjausten ja rakennustuotteiden vaihtojen energian käytön kasvihuonekaasupäästöt rak_korj_energia_co2 [CO2-ekv/a] ovat

            rak_korj_energia_co2= rakennus_ala* rak_korj_energia_gco2m2

        YKR-ruudun rakennusten laajamittaisen korjausten energian käytön laskentavuonna aiheuttamat kasvihuonekaasupäästöt rak_saneer_energia_co2 [t CO2-ekv/a] lasketaan kaavalla

            rak_saneer_energia_co2 = rakennus_ala * rak_saneer_osuus * rak_saneer_energia_gco2m2 * muunto_massa

        Kummassakaan tarkastelussa ei oteta vielä tässä vaiheessa huomioon korjaamisessa tarvittavien materiaalien valmistuksen aiheuttamia välillisiä kasvihuonekaasupäästöjä.

        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildRenovate(
            floorSpace real, -- Rakennustyypin (erpien, rivita, askert, liike, tsto, liiken, hoito, kokoon, opetus, teoll, varast, muut) ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna [m2]. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta.
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar,  -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer, -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
            calculationScenario varchar) -- PITKO-kehitysskenaario | PITKO development scenario
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            rak_korj_energia_gco2m2 real; -- Tarkasteltavan rakennustyypin pienimuotoisten korjausten työmaatoimintojen ja kuljetusten kasvihuonekaasun ominaispäästöt yhtä kerrosneliötä kohti laskentavuonna [gCO2-ekv/m2]. Riippuu taustaskenaariosta, laskentavuodesta ja rakennustyypistä.
            rak_saneer_energia_gco2m2  real; -- Tarkasteltavan rakennustyypin laajamittaisen korjausrakentamisen työmaatoimintojen ja kuljetusten kasvihuonekaasun ominaispäästöt yhtä kerroskerrosneliötä kohti laskentavuonna [gCO2-ekv/m2]. Riippuu taustaskenaariosta, laskentavuodesta ja rakennustyypistä.
            rak_saneer_osuus real; -- Rakennustyypin ikäluokkakohtainen kerrosalaosuus, johon tehdään laskentavuoden aikana laajamittaisia korjausrakentamista [ei yksikköä]. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta sekä rakennuksen ikäluokasta ja tyypistä.
        BEGIN
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            ELSE
            
                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

                /* Korjausrakentamisen ominaispäästöt */
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_renovation_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                    INTO rak_korj_energia_gco2m2  USING calculationScenario, calculationYear;
                /* Saneerauksen ominaispäästöt ja vuosittainen kattavuus */
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_rebuilding_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                    INTO rak_saneer_energia_gco2m2  USING calculationScenario, calculationYear;
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_rebuilding_share WHERE scenario = $1 AND rakv = $2 AND year = $3'
                    INTO rak_saneer_osuus USING calculationScenario, buildingYear, calculationYear;

                RETURN floorSpace *
                    (COALESCE(rak_korj_energia_gco2m2, 0) + COALESCE(rak_saneer_energia_gco2m2, 0) * COALESCE(rak_saneer_osuus,0));
                
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Sähkön käyttö, kotitaloudet | Electricity consumption, households

        Kotitalouksien sähkön käyttö muuhun kuin asuinrakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin sahko_koti_kwh [kWh/a] lasketaan kaavalla

            sahko_koti_kwh = rakennus_ala * (sahko_koti_laite + sahko_koti_valo) + v_yht * sahko_koti_as

        Kotitalouksien muuhun kuin lämmitykseen ja kiinteistösähköön käytetyn sähkön kasvihuonekaasupäästöt sahko_koti_co2 [CO2-ekv/a] ovat 

            sahko_koti_co2 = sahko_koti_kwh  * sahko_gco2kwh
        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityHousehold(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            area_or_pop real, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna [m2] tai väestö laskentavuonna.
            buildingType varchar -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
        BEGIN
            IF area_or_pop <= 0 OR area_or_pop IS NULL THEN
                RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

            IF buildingType IS NULL THEN
                    EXECUTE FORMAT(
                        'WITH electricity_home_percapita AS (
                            -- Asukkaiden lisävaikutus asunnon sähkön kulutukseen. [kWh/as/a].
                            SELECT sahko_koti_as AS kwh
                            FROM energy.electricity_home_percapita sas
                            WHERE sas.year = %1$L
                                AND sas.scenario = %2$L
                                AND sas.mun = %4$L
                        ), electricity_gco2kwh AS (
                            -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                            SELECT el.gco2kwh::int AS gco2
                            FROM energy.electricity el
                                WHERE el.year = %1$L
                                AND el.scenario = %2$L
                                AND el.metodi = ''em''
                                AND el.paastolaji = ''tuotanto''
                        )
                        SELECT %3$L * percapita.kwh * gco2kwh.gco2
                        FROM electricity_home_percapita percapita, electricity_gco2kwh gco2kwh
                        '
                    , calculationYear, calculationScenario, area_or_pop, municipality
                    ) INTO result_gco2;
            
            ELSE 
                    EXECUTE FORMAT(
                        'WITH electricity_home_devices AS (
                            -- Rakennustyyppikohtainen laitesähkön keskimääräinen peruskulutus [kWh/m2/a]
                            SELECT %3$I::int AS kwh
                            FROM built.electricity_home_device WHERE scenario = %2$L AND year = %1$L
                        ), electricity_home_lighting AS (
                            -- Rakennustyyppikohtainen sisävalaistuksen sähkön käyttö kerrosneliötä kohti huomioiden tekniikan ja muuhun valaistukseen liittyvän sähkön käytön kehityksen [kWh/m2/a]
                            SELECT %3$I::int AS kwh
                            FROM built.electricity_home_light WHERE scenario = %2$L AND year = %1$L
                        ), electricity_gco2kwh AS (
                            SELECT el.gco2kwh::int AS gco2 -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                            FROM energy.electricity el
                                WHERE el.year = %1$L
                                AND el.scenario = %2$L
                                AND el.metodi = ''em''
                                AND el.paastolaji = ''tuotanto''
                        )
                        SELECT  %4$L * (devices.kwh + lights.kwh) * gco2kwh.gco2
                        FROM electricity_home_devices devices,   
                            electricity_home_lighting lights,
                            electricity_gco2kwh gco2kwh
                        '
                    , calculationYear,
                    calculationScenario,
                    buildingType,
                    area_or_pop
                    ) INTO result_gco2;
            
            END IF;

            END IF;
            RETURN result_gco2;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Sähkön käyttö, teollisuus, varastot ja palvelut | Electricity consumption, industry, warehouses and services

        Palvelusektorin sekä teollisuuden ja varastojen sähkön käyttö muuhun kuin rakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin sahko_palv_kwh [kWh/a] perustuu kaavaan

            sahko_ptv_kwh  = rakennus_ala * sahko_ptv_kwhm2

        Palvelusektorin sekä teollisuuden ja varastojen muuhun lämmitykseen ja kiinteistöshköön käytetyn sähkön kasvihuonekaasupäästöt sahko_palv_co2 [CO2-ekv/a] ovat 

            sahko_ptv_co2 = sahko_ptv_kwh  * sahko_gco2kwh

        Teollisuus- ja varastorakennusten sähkön käyttö sisältää myös niiden kiinteistösähkön kulutuksen.

        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityIWHS(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace real, -- rakennustyypin kerrosala YKR-ruudussa laskentavuonna [m2]. Riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta.
            buildingType varchar -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            services varchar[] default ARRAY['myymal_hyper', 'myymal_super', 'myymal_pien', 'myymal_muu', 'myymal', 'majoit', 'asla', 'ravint', 'tsto', 'liiken', 'hoito', 'kokoon', 'opetus', 'muut'];
            result_gco2 real;
        BEGIN

            IF floorSpace <= 0
                OR floorSpace IS NULL THEN
                RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

                EXECUTE FORMAT('
                    WITH 
                    electricity_gco2kwh AS (
                        -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                        SELECT el.gco2kwh::real AS gco2 
                        FROM energy.electricity el
                            WHERE el.year = %3$L 
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto'' LIMIT 1
                    )
                    -- rakennustyypissä tapahtuvan toiminnan sähköintensiteetti kerrosneliömetriä kohti [kWh/m2]
                    SELECT ry.%1$I * %4$L::int * el.gco2
                    FROM built.electricity_iwhs_kwhm2 ry, electricity_gco2kwh el
                        WHERE ry.scenario = %2$L AND ry.year = %3$L LIMIT 1',
                    buildingType,
                    calculationScenario,
                    calculationYear,
                    floorSpace
                ) INTO result_gco2;
                
                RETURN result_gco2;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Kiinteistösähkön kulutus | Consupmtion of property tech electricity

        YKR-ruudun rakennusten liittyvä kiinteistösähkön käyttö sahko_kiinteisto_kwh [kWh/a] lasketaan kaavalla:
            sahko_kiinteisto_kwh = rakennus_ala * sahko_kiinteisto_kwhm2 * sahko_kiinteisto_muutos

        Kiinteistösähkön kasvihuonekaasupäästöt sahko_kiinteisto_co2 [CO2-ekv/a] ovat:
            sahko_kiinteisto_co2 = sahko_kiinteisto_kwh * sahko_gco2kwh

        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityProperty(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace real, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
            sahko_kiinteisto_muutos real; -- Rakennustyypin ikäluokkakohtainen keskimääräisen kiinteistösähkön kulutuksen muutos tarkasteluvuonna [Ei yksikköä]. Lukuarvo riippuu laskentavuodesta ja rakennuksen ikäluokasta
        BEGIN
            
            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                EXECUTE FORMAT(
                'WITH electricity_property_khwm2 AS (
                    -- Kiinteistöjen sähkönkulutus kerrosalaa kohti
                    -- Electricity consumption of integrated property technology
                    SELECT sahko_kiinteisto_kwhm2 AS kwh
                    FROM built.electricity_property_kwhm2
                    WHERE scenario = %2$L
                        AND rakennus_tyyppi = %3$L
                        AND rakv = %4$L
                        LIMIT 1
                ), electricity_property_change AS (
                    -- Kiinteistöjen sähkönkulutuksen muutos rakennusten rakennusvuosikymmenittäin
                    -- Change of property electricity consumption according to year of building
                
                    SELECT %4$I as change
                        FROM built.electricity_property_change
                        WHERE scenario = %2$L AND year = %1$L
                        LIMIT 1
                ),
                electricity_gco2kwh AS (
                    -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                    SELECT el.gco2kwh::int AS gco2
                    FROM energy.electricity el
                        WHERE el.year = %1$L
                        AND el.scenario = %2$L
                        AND el.metodi = ''em''
                        AND el.paastolaji = ''tuotanto''
                )
                -- Lasketaan päästöt CO2-ekvivalentteina | Calculate emissions as gCO2-equivalents 
                SELECT %5$L * kwhm2.kwh * gco2kwh.gco2 * change.change
                FROM electricity_property_khwm2 kwhm2, electricity_gco2kwh gco2kwh, electricity_property_change change
                '
            , calculationYear,
            calculationScenario,
            buildingType,
            CASE WHEN buildingYear > 2010 THEN 2010 ELSE buildingYear end,
            floorSpace
            ) INTO result_gco2;
            
            RETURN result_gco2;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten jäähdytys | Cooling of buildings 

        YKR-ruudun rakennusten jäähdytystarve jaahdytys_kwh [kWh/a] on:
            jaahdytys_kwh = rakennus_ala * jaahdytys_osuus * jaahdytys_kwhm2 * jaahdytys_muoto * jaahdytys_muutos

        Rakennusten jäähdytykseen tarvitun ostoenergian kasvihuonekaasupäästöt [CO2/a] ovat:
            jaahdytys_co2 = jaahdytys_kwh * (jmuoto_apu1 * sahko_gco2kwh + jmuoto_apu2 * jaahdytys_gco2kwh)

        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyCooling(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace integer, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
            jaahdytys_kwhm2 real[]; -- Rakennustyypin ikäluokan jäähdytysenergian tarve yhtä kerrosneliötä kohti. Arvo riippuu taustaskenaariosta, rakennuksen tyypistä ja ikäluokasta [kWh/m2/a]
            jaahdytys_kwh real[]; -- Jäähdytyksen energiankulutus
            jaahdytys_co2 real[]; -- Jäähdytyksen kasvihuonekaasupäästöt [gCO2]
        BEGIN

            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

            /* Dummy-kertoimet jäähdytysmuodoille | Dummy multipliers by method of cooling */
            /* Jäähdytyksen ominaispäästökertoimet | Emission values for cooling */

            -- SELECT array[kaukok, sahko, pumput, muu] FROM energy.cooling_gco2kwh ej WHERE ej.year = calculationYear AND ej.scenario = calculationScenario INTO j_gco2kwh;
            -- SELECT array(SELECT unnest(array[0, 1, 1, 0]) * sahko_gco2kwh + unnest(j_gco2kwh) * unnest(array[1, 0, 0, 1])) INTO jaahdytys_gco2kwh;

                -- Tällä hetkellä luvut sähkön osalta, jaahdytys_sahko = aina 1
                EXECUTE FORMAT(
                    'WITH coolingchange AS
                        (SELECT 
                        CASE WHEN %1$L = ANY(%7$L) THEN (1 + (%3$L - 2017 - 1) * 0.0118) ELSE (1 + (%3$L - 2017 - 1) * 0.0273) END
                            AS change -- Jäähdytyksen määrän kasvu rakennustyypeittäin. [ei yksikköä]
                    ), coolingkwhm2 AS (
                        SELECT
                            jaahdytys_osuus -- Rakennusten jäähdytettävät osuudet | Proportion of different types of buildings cooled 
                            * jaahdytys_kwhm2 AS kwhm2 -- Jäähdytyksen energiankulutus kerrosalaa kohden || Energy consumption of cooling buildings per floor area
                        FROM built.cooling_proportions_kwhm2
                        WHERE scenario = %2$L AND rakennus_tyyppi = %4$L AND rakv = %5$L LIMIT 1
                    ), gco2kwh AS (
                        SELECT el.gco2kwh::int AS gco2
                        FROM energy.electricity el
                            WHERE el.year = %3$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    )
                    SELECT coolingchange.change * coolingkwhm2.kwhm2 * %6$L * gco2kwh.gco2 
                        FROM coolingchange, coolingkwhm2, gco2kwh
                    ',
                    buildingType, calculationScenario, calculationYear, buildingType, buildingYear, floorSpace, ARRAY['erpien', 'rivita', 'askert', 'teoll', 'varast', 'muut']
                ) INTO result_gco2;
            
                RETURN result_gco2;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten lämmitys | Heating of buildings

        Rakennusten lämmityksen kasvihuonekaasupäästöjen laskennalla tarkoitetaan tässä rakennusten nettomääräisen lämmitysenergian tarpeen arviointia.
        Tämä tarkoittaa rakennusten tilojen lämmittämiseen tarvittavaa energiaa, josta on vähennetty henkilöistä, valaistuksesta ja sähkölaitteista syntyvien lämpökuormien energia,
        poistoilmasta ja muista energiavirroista talteen otettu tilojen lämmityksessä hyödynnetty energia ja ikkunoiden kautta tuleva auringon säteilyenergia.

        Lämmitysmuotoihin – tai oikeammin lämmönlähteisiin – sisältyvät kauko- ja aluelämpö, kevyt polttoöljy, raskas polttoöljy, maakaasu, sähkölämmitys, puupolttoaineet, turve,
        kivihiili ja koksi, maalämpö ja muut vastaavat lämpöpumput sekä muut lämmitysmuodot. Jälkimmäiseen ryhmään sisältyvät myös tilastojen tuntemattomat lämmitysmuodot.

        YKR-ruudun buildingTypeen eri ikäluokkien lämmitysmuotojen tilojen nettolämmitystarpeet tilat_lammitystarve [kWh/a] lasketaan seuraavalla kaavalla.
        
            tilat_lammitystarve =  floorSpace * tilat_kwhm2  * lammitystarve_vuosi / lammitystarve_vertailu / lammitystarve_korjaus_vkunta

        Jos tarkasteltavan alueen rakennusten tyyppi-, ikäluokka- ja lämmitysmuotojakauma perustuu kunnan omaan paikkatietopohjaiseen aineistoon,
        floorSpace -tieto on lämmitysmuotokohtainen. Tämä tarkempi laskentatapa ottaa huomioon keskimääräiseen jakaumaan perustuvaa laskentaa paremmin huomioon lämmitysmuotojakauman ruutukohtaiset erot.
        Muutoin voidaan käyttää esilaskettua buildingType- ja ikäluokkakohtaista keskimääristä lämmitysmuotojakaumaa, joka on tarkasteltavasta YKR-ruudusta riippumaton.
        
        YKR-ruudun buildingTypeen tilojen lämmitykseen vuoden aikana tarvittu ostoenergia tilat_kwh [kWh/a] on
            
            tilat_kwh = tilat_lammitystarve / tilat_hyotysuhde

        buildingTypeen tilojen lämmityksen tarvitseman ostoenergian kasvihuonekaasupäästöt tilat_co2 [CO2-ekv/a] saadaan kaavalla
        
            tilat_co2 = tilat_kwh * (lmuoto_apu1 * klampo_gco2kwh + lmuoto_apu2 * sahko_gco2kwh + lmuoto_apu3 * tilat_gco2kwh)

        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyHeat(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace int, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna. Arvo riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta ja paikallista aineistoa käytettäessä lämmitysmuodosta [m2]
            buildingType varchar, -- buildingType, esim. 'erpien', 'rivita'S
            buildingYear int, -- buildingYear decade tai -vuosi (2017 alkaen)
            method varchar,
            heatSource varchar default null -- Rakennuksen lämmityksessä käytettävä primäärinen energiamuoto 'energiam', mikäli tällainen on lisätty YKR/rakennusdataan
        )
        RETURNS real AS
        $$
        DECLARE -- Joillekin muuttujille on sekä yksittäiset että array-tyyppiset muuttujat, riippuen siitä, onko lähtödatana YKR-dataa (array) vai paikallisesti jalostettua rakennusdataa
            calculationYear integer;
            heating_kwh real; -- Raw heating of spaces without efficiency ratio
            hyotysuhde real; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            hyotysuhde_a real[]; -- Rakennustyypin ikäluokan keskimääräiset vuosihyötysuhteet eri lämmitysjärjestelmille. Lukuarvo riippuu rakennuksen ikäluokasta ja tyypistä [ei yksikköä].
            lammitys_kwh_a real[]; -- Lämmityksen energiankulutus (array)
            lammitys_co2_a real[]; -- Lämmityksen kasvihuonekaasupäästöt [gCO2]
            lammitysosuus real[]; -- Lämmitysmuotojen keskimääräiset osuudet rakennustyypin kerrosalasta tietyssä ikäluokassa laskentavuonna. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta, rakennuksen ikäluokasta ja tyypistä.
            gco2kwh_a real[];
            gco2kwh real; -- Lopulliset ominaispäästökertoimet
            result_gco2 real;
        BEGIN

            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                /* Used when local building register data has been used to derive grid level information incl. heating methods of building */
                IF heatSource IS NOT NULL THEN
                    EXECUTE FORMAT('
                        SELECT %1$I::real
                            FROM built.spaces_efficiency
                            WHERE rakennus_tyyppi = %2$L
                                AND rakv::int = %3$s::int LIMIT 1
                        ', heatSource, buildingType, buildingYear, calculationScenario
                    ) INTO hyotysuhde;
                ELSE
                    /* Used when basing the analysis on pure YKR data */
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO lammitysosuus
                            FROM built.distribution_heating_systems
                            WHERE scenario = calculationScenario
                            AND rakennus_tyyppi = buildingType
                            AND rakv = buildingYear
                            AND year = calculationYear;
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO hyotysuhde_a
                            FROM built.spaces_efficiency
                                WHERE rakennus_tyyppi = buildingType AND 
                                    rakv = buildingYear;
                END IF;

                    /* Energy demand for different building types, per square meter floor space */

                /* Ilmaston lämpenemisen myötä tilojen lämmitystarve pienenee, välillä 2015-2050 noin -17% eli n. 0.5% per vuosi. 
                    Lineaariseksi määritetty kehitys perustuu tutkimukseen:
                    P. Pirinen, H. Simola, S. Nevala, P. Karlsson ja S. Ruuhela, ”Ilmastonmuutos ja lämmitystarveluku paikkatietoarvioina Suomessa,” Ilmastieteen laitos, Helsinki, 2014.
                    ja tässä valittu  aiemman ilmastonmuutosmallinnuksen IPCC:n SRES-kasvihuonekaasuinventaarion A1B-skenaario;
                    Tämä vastaa uusien kasvihuonekaasujen pitoisuuksien kehityskulkuja mallintavien RCP-päästöskenaarioiden optimistisimman RCP4.5- ja pessimistisen RCP8.5-skenaarion välimaastoa.
                */
                EXECUTE FORMAT('
                    WITH spaces AS (
                        -- Rakennustyypin ikäluokkakohtainen kerrosneliömetrin lämmittämiseen vuodessa tarvittu nettolämmitysenergia.
                        -- Kerroin huomioi olevan rakennuskannan energiatehokkuuden kehityksen [kWh/m2/a].
                        SELECT %6$I as kwhm2
                        FROM built.spaces_kwhm2
                            WHERE scenario = %1$L AND rakv = %2$L AND year = %4$L LIMIT 1),
                        heating as (
                            SELECT ((1 - 0.005 * (%4$L::int - 2015)) * multiplier)::real as scaler
                                FROM energy.heating_degree_days dd
                                    WHERE dd.mun::int = %3$L
                        ) SELECT spaces.kwhm2 * heating.scaler * %5$L
                            FROM spaces, heating
                        ', calculationScenario, buildingYear, municipality, calculationYear, floorSpace, buildingType
                ) INTO heating_kwh;

                /* Kaukolämmön ominaispäästökertoimet  */
                /* Emission values for district heating (first finding out the name of the correct district heating table) */
                EXECUTE FORMAT(
                    'WITH district_heating AS (
                        SELECT %3$I as gco2kwh -- Laskentavuonna kulutetun kaukolämmön ominaispäästökerroin [gCO2-ekv/kWh]
                        FROM energy.district_heating heat
                        WHERE heat.year = %1$L
                        AND heat.scenario = %2$L
                        AND heat.mun::int = %4$L
                        ORDER BY %3$I DESC LIMIT 1
                    ), electricity AS (
                        SELECT el.gco2kwh::int AS gco2kwh
                        FROM energy.electricity el
                            WHERE el.year = %1$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    ), spaces AS (
                        --  Lämmönlähteiden kasvihuonekaasupäästöjen ominaispäästökertoimet [gCO2-ekv/kWh]
                        SELECT array[kevyt_oljy, kaasu, puu, muu_lammitys] as gco2kwh 
                        FROM energy.spaces_gco2kwh t
                        WHERE t.vuosi = %1$L
                    ) SELECT
                        array[
                            district_heating.gco2kwh, -- kaukolämpö
                            spaces.gco2kwh[1], -- kevyt_oljy
                            spaces.gco2kwh[2], -- kaasu
                            electricity.gco2kwh, -- sahko
                            spaces.gco2kwh[3], -- puu
                            electricity.gco2kwh, -- maalampo
                            spaces.gco2kwh[4] -- muu_lammitys
                        ] FROM district_heating, spaces, electricity
                    ',
                    calculationYear, calculationScenario, method, municipality
                ) INTO gco2kwh_a;

                    /* Lasketaan päästöt tilanteessa, jossa käytetään paikallista rakennusaineistoa */
                    /* Calculating final emission when using local building data */
                    IF heatSource IS NOT NULL THEN
                        -- Lämmityksen energiankulutus (kwh) * gco2 per kwh
                        SELECT heating_kwh / COALESCE(hyotysuhde, 1)::real *
                            CASE WHEN heatSource = 'kaukolampo' THEN gco2kwh_a[1]
                            WHEN heatSource IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN gco2kwh_a[2]
                            WHEN heatSource = 'kaasu' THEN gco2kwh_a[3]
                            WHEN heatSource = 'sahko' THEN gco2kwh_a[4]
                            WHEN heatSource = 'puu' THEN gco2kwh_a[5]
                            WHEN heatSource = 'maalampo' THEN gco2kwh_a[6]
                            WHEN heatSource = 'muu_lammitys' THEN gco2kwh_a[7] ELSE 1 END
                        INTO result_gco2;
                        RETURN result_gco2;
                    ELSE
                    
                    /* Lasketaan päästöt tilanteessa, jossa käytetään YKR-rakennusaineistoa */
                    /* Calculating final emissions when using YKR-based building data */
                        SELECT array(SELECT(heating_kwh / unnest(hyotysuhde_a))) INTO lammitys_kwh_a;
                        SELECT array(SELECT unnest(gco2kwh_a) * unnest(lammitys_kwh_a) * unnest(lammitysosuus)) INTO lammitys_co2_a;

                        /* Palauta CO2-ekvivalenttia */
                        /* Return CO2-equivalents */
                        SELECT SUM(a) FROM unnest(lammitys_co2_a) a INTO result_gco2;
                        RETURN result_gco2;
                    END IF;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Käyttöveden lämmitys | Heating of water

        YKR-ruudun rakennusten vuoden aikana kuluttaman lämpimän käyttöveden lämmitystarve vesi_lammitystarve [kWh/a] on:
            vesi_lammitystarve = rakennus_ala * vesi_kwhm2

        Lämpimän käyttöveden lämmittämiseen tarvittavan ostoenergian tarve vesi_kwh [kWh/a] on:
            vesi_kwh =  vesi_lammitystarve / (tilat_hyotysuhde - 0.05)

        buildingTypeen käyttöveden lämmityksen tarvitseman ostoenergian kasvihuonekaasupäästöt vesi_co2 [CO2-ekv/a] ovat YKR-ruudussa:
            vesi_co2 = vesi_kwh * (lmuoto_apu1 * klampo_gco2kwh + lmuoto_apu2 * sahko_gco2kwh + lmuoto_apu3 * tilat_gco2kwh)
            
        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyWater(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace int, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- buildingType, esim. 'erpien', 'rivita'
            buildingYear integer, -- buildingYearkymmen tai -vuosi (2017 alkaen)
            method varchar, 
            heatSource varchar default null -- Rakennuksen lämmityksessä käytettävä primäärinen energiamuoto 'energiam', mikäli tällainen on lisätty YKR/rakennusdataan
        )
        RETURNS real AS
        $$
        DECLARE -- Joillekin muuttujille on sekä yksittäiset että array-tyyppiset muuttujat, riippuen siitä, onko lähtödatana YKR-dataa (array) vai paikallisesti jalostettua rakennusdataa
            calculationYear integer; 
            vesi_kwhm2 real; -- Rakennustyypin ikäluokan kerrosalaa kohti vesikuutiometrittäin lasketun lämpimän käyttöveden ominaiskulutuksen [m3/m2/a] ja yhden vesikuution lämmittämiseen tarvittavan energiamäärän 58,3 kWh/m3 tulo. Arvo riippuu laskentaskenaariosta sekä rakennuksen ikäluokasta ja tyypistä [kWh/m2,a].
            hyotysuhde real; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            hyotysuhde_a real[]; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            vesi_kwh real; -- Veden lämmityksen energiankulutus
            vesi_kwh_a real[]; -- Veden lämmityksen energiankulutus
            vesi_co2_a real[]; -- Veden lämmityksen kasvihuonekaasupäästöt [gCO2]
            lammitysosuus real[]; -- Lämmitysmuotojen keskimääräiset osuudet rakennustyypin kerrosalasta tietyssä ikäluokassa laskentavuonna. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta, rakennuksen ikäluokasta ja tyypistä.
            gco2kwh_a real[];
            gco2kwh real; -- Käytettävä ominaispäästökerroin
        BEGIN
            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL
                THEN RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                /* Käytetään kun on johdettu paikallisesta aineistosta lämmitys/energiamuototiedot ruututasolle */
                /* Used when local building register data has been used to derive grid level information incl. heating methods of building */
                IF heatSource IS NOT NULL THEN
                    EXECUTE FORMAT('
                        SELECT %1$I::real
                            FROM built.spaces_efficiency
                            WHERE rakennus_tyyppi = %2$L
                                AND rakv::int = %3$s::int LIMIT 1
                        ', heatSource, buildingType, buildingYear, calculationScenario
                    ) INTO hyotysuhde;
                ELSE

                /* Käytetään kun käytössä on pelkkää YKR-dataa */
                /* Used when basing the analysis on pure YKR data */
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO lammitysosuus
                            FROM built.distribution_heating_systems
                                WHERE scenario = calculationScenario
                                AND rakennus_tyyppi = buildingType
                                AND rakv = buildingYear
                                AND year = calculationYear;
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO hyotysuhde_a
                            FROM built.spaces_efficiency
                                WHERE rakennus_tyyppi = buildingType
                                AND rakv = buildingYear;
                END IF;

                /* Veden lämmityksen energiankulutus per kerrosneliö */
                /* Water heating power consumption per floor space, square meter */
                SELECT vesi_kwh_m2 INTO vesi_kwhm2
                    FROM built.water_kwhm2 vesi_kwhm2
                    WHERE vesi_kwhm2.scenario = calculationScenario
                    AND vesi_kwhm2.rakennus_tyyppi = buildingType
                    AND vesi_kwhm2.rakv = buildingYear;
            
                /* Kaukolämmön ominaispäästökertoimet  */
                /* Emission values for district heating (first finding out the name of the correct district heating table) */
                EXECUTE FORMAT(
                    'WITH district_heating AS (
                        SELECT %3$I as gco2kwh
                        FROM energy.district_heating heat
                        WHERE heat.year = %1$L
                        AND heat.scenario = %2$L
                        AND heat.mun::int = %4$L::int
                    ), electricity AS (
                        SELECT el.gco2kwh::int AS gco2kwh
                        FROM energy.electricity el
                            WHERE el.year = %1$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    ), spaces AS (
                        SELECT array[kevyt_oljy, kaasu, puu, muu_lammitys] as gco2kwh
                        FROM energy.spaces_gco2kwh t
                        WHERE t.vuosi = %1$L LIMIT 1
                    ) SELECT
                        array[
                            district_heating.gco2kwh, -- kaukolampö
                            spaces.gco2kwh[1], -- kevyt_oljy
                            spaces.gco2kwh[2], -- kaasu
                            electricity.gco2kwh, -- sahko
                            spaces.gco2kwh[3], -- puu
                            electricity.gco2kwh, -- maalampo
                            spaces.gco2kwh[4] -- muu_lammitys
                        ]
                        FROM district_heating, spaces, electricity
                    ',
                    calculationYear, calculationScenario, method, municipality
                ) INTO gco2kwh_a;
            

                /* Lasketaan päästöt tilanteessa, jossa käytetään paikallista rakennusaineistoa */
                /* Calculating final emission when using local building data */
                IF heatSource IS NOT NULL THEN
                    SELECT (floorSpace * vesi_kwhm2) / (hyotysuhde::real - 0.05) INTO vesi_kwh;

                        SELECT CASE
                            WHEN heatSource = 'kaukolampo' THEN gco2kwh_a[1]
                            WHEN heatSource IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN gco2kwh_a[2]
                            WHEN heatSource = 'kaasu' THEN gco2kwh_a[3]
                            WHEN heatSource = 'sahko' THEN gco2kwh_a[4]
                            WHEN heatSource = 'puu' THEN gco2kwh_a[5]
                            WHEN heatSource = 'maalampo' THEN gco2kwh_a[6]
                            WHEN heatSource = 'muu_lammitys' THEN gco2kwh_a[7]
                            END INTO gco2kwh;

                    RETURN vesi_kwh * gco2kwh; -- vesi_co2
                ELSE
                    /* Lasketaan päästöt tilanteessa, jossa käytetään YKR-rakennusaineistoa */
                    /* Calculating final emissions when using YKR-based building data */
                    SELECT array(SELECT(floorSpace * vesi_kwhm2) / (unnest(hyotysuhde_a) - 0.05)) INTO vesi_kwh_a;
                    SELECT array(SELECT unnest(gco2kwh_a) * unnest(vesi_kwh_a) * unnest(lammitysosuus)) INTO vesi_co2_a;

                    /* Palauta CO2-ekvivalentteja */
                    /* Return CO2-equivalents */
                    RETURN SUM(a) FROM unnest(vesi_co2_a) a;
                END IF;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Tavaraliikenne palvelu- ja teollisuuden rakennuksiin
        Goods traffic for service and industry buildings

        Palvelurakennukset luokitellaan kasvihuonekaasupäästölaskelmissa myymälärakennuksiin (myymal_), majoitusliikerakennuksiin (majoit),
        asuntolarakennuksiin (asla), ravintoloihin ja ruokaloihin (ravint), toimistorakennuksiin (tsto), liikenteen rakennuksiin (liiken),
        hoitoalan rakennuksiin (hoito), kookoontumisrakennuksiin (kokoon), opetusrakennuksiin (opetus) ja muihin rakennuksiin (muut).
        Teollisuus- ja varastorakennuksiin sisältyvät teollisuusrakennukset (teoll) ja varastorakennukset (varast).
        */

        /*  Test : 
            SELECT co2_traffic_iwhs_co2('837', 2021::int, 'wem', 3000::int, 'myymal_hyper', array[23, 53, 25, 43, 66, 22, 11, 5, 4])
        */
        CREATE OR REPLACE FUNCTION
        functions.CO2_TrafficIWHS(
            municipality integer, -- Municipality, for which the values are calculated
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace integer, -- Rakennusten kerrosala tai lukumäärä (vain teoll ja varast - tapauksissa)
            buildingType varchar -- buildingType | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer; 
            services varchar[] default ARRAY['myymal_hyper', 'myymal_super', 'myymal_pien', 'myymal_muu', 'myymal', 'majoit', 'asla', 'ravint', 'tsto', 'liiken', 'hoito', 'kokoon', 'opetus', 'muut'];
            gco2_output real;

        BEGIN
            IF  floorSpace <= 0
                OR floorSpace IS NULL
                THEN RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;
            
            /*  Tavarakuljetusten vuosisuorite palv_km [km/a] on laskentavuonna
                    palv_km = rakennus_ala * muunto_ala_tliikenne * palv_suorite * palv_kuljetus_km * arkipaivat
                Paketti- ja kuorma-autojen käyttövoimien suoriteosuuksilla painotettu keskikulutus kmuoto_kwhkm [kWh/km] lasketaan
                    kmuoto_kwhkm = mode_power_distribution * kvoima_kwhkm
                Paketti- ja kuorma-autoilla tehdyn tavaraliikenteen vuosittainen energian käyttö [kWh/a] lasketaan kaavoilla
                    ptv_liikenne_kwh = ptv_km * kmuoto_kwhkm
                Laskentavuoden palvelu- ja teollisuusrakennusten paketti- ja kuorma-autojen tavarakuljetussuoritteiden aiheuttamat kasvihuonekaasupäästöt [CO2-ekv/a] ovat
                    ptv_liikenne_co2 = ptvliikenne_palv_kwh * kmuoto_gco2kwh
            */

            EXECUTE FORMAT(
                'WITH RECURSIVE
                mode_power_distribution AS
                (SELECT kmuoto,
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as distribution
                    FROM traffic.mode_power_distribution
                        WHERE year = %1$L
                            AND scenario = %2$L
                            AND mun = %3$L
                            AND kmuoto = ANY(%4L)
                ), power_kwhkm as (
                SELECT kmuoto,
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as kwhkm
                    FROM traffic.power_kwhkm
                        WHERE year = %1$L AND scenario = %2$L AND kmuoto = ANY(%4$L)
                ),
                fossils as (
                    -- Käyttövoimien fossiiliset osuudet [ei yksikköä].
                    SELECT array[share, 1, share, 1, share, share, 1, 1, share] as share
                    FROM traffic.power_fossil_share pfs
                        WHERE pfs.year = %1$L
                        AND pfs.scenario =  %2$L LIMIT 1
                ), electricity_gco2kwh AS (
                    -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                    SELECT el.gco2kwh::int AS gco2
                    FROM energy.electricity el
                        WHERE el.year = %1$L
                        AND el.scenario = %2$L
                        AND el.metodi = ''em''
                        AND el.paastolaji = ''tuotanto'' LIMIT 1
                ),
                gco2kwh_matrix as (
                    SELECT 
                    -- Käyttövoimien  kasvihuonekaasujen ominaispäästökerroin käytettyä energiayksikköä kohti [gCO2-ekv/kWh].
                    array( SELECT el.gco2 *
                        -- Dummy, jolla huomioidaan sähkön käyttö sähköautoissa, pistokehybrideissä ja polttokennoautojen vedyn tuotannossa [ei yksikköä].
                        unnest(array[0, 0, 0, 0, 0.5, 0.5, 1, 2.5, 0]) +
                        -- phev_b ja phev_d saavat bensiinin ja dieselin ominaispäästöt = 241 & 237 gco2/kwh
                        -- Etanolin päästöt vuonna 2017 = 49, tuotannon kehityksen myötä n. 0.8 parannus per vuosi
                        unnest(array[241, (49 - (%1$L - 2017) * 0.8), 237, 80, 241, 237, 0, 0, 189]) *
                        unnest(fossils.share) *
                        unnest(array[1, 1, 1, 1, 0.5, 0.5, 0, 0, 1])
                    ) as arr FROM electricity_gco2kwh el, fossils
                ),
                kwh_distribution as (
                    SELECT a.kmuoto,
                        unnest(distribution) * unnest(kwhkm) as kwh,
                        unnest(gco2kwh_matrix.arr) as gco2
                    FROM mode_power_distribution a
                        NATURAL JOIN power_kwhkm b,
                        gco2kwh_matrix
                ),
                distance as 
                -- Apply polynomial regression for estimating size to visits ratio of industry, scale suorite to industry-type weighted average (13.5)
                -- According to Turunen V. TAVARALIIKENTEEN MALLINTAMISESTA HELSINGIN SEUDULLA,
                -- These original traffic estimates create approximately twice the observed amount. Thus half everything.
                (SELECT f.kmuoto, f.%5$I::real *
                    CASE WHEN %8$L = ''industr_performance'' THEN d.%5$I / (CASE WHEN %5$L != ''varast'' THEN 13.5 ELSE 46 END)::real
                        * (0.000000000245131 * %6$L^2 -0.000026867899351 * %6$L + 0.801629386363636)
                        ELSE d.%5$I END
                    * %9$L * 0.01 as km
                FROM traffic.%7$I f
                    LEFT JOIN traffic.%8$I d
                    ON d.kmuoto = f.kmuoto
                    AND d.year = f.year
                    AND d.scenario = f.scenario
                    WHERE f.kmuoto = ANY(%4$L)
                    AND f.year = %1$L
                    AND f.scenario = %2$L)
                SELECT sum(kwh * gco2 * km / 2) * %6$L
                FROM kwh_distribution kwh
                    NATURAL JOIN distance',
            calculationYear, -- 1
            calculationScenario, -- 2
            municipality, -- 3 
            ARRAY['kauto', 'pauto'], -- 4
            buildingType, -- 5
            CASE WHEN floorSpace >= 100000 THEN 100000::real ELSE floorSpace end, -- 6 - kerrosneliömetrit
            CASE WHEN buildingType = ANY(services) THEN 'services_transport_km' ELSE 'industr_transport_km' END, -- 7
            CASE WHEN buildingType = ANY(services) THEN 'service_performance' ELSE 'industr_performance' END, -- 8
            260) INTO gco2_output; -- 9 - Arkipäivien lukumäärä vuodessa (260) [vrk/a].
            
            RETURN gco2_output;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION functions.CO2_TrafficPersonal(
            municipality integer,
            pop_or_employ integer, -- Population or number of workplaces
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            mode varchar, -- Mode of transportation
            centdist integer,
            zone bigint,
            calculationScenario varchar,
            traffictype varchar,
            includeLongDistance boolean default false,
            includeBusinessTravel boolean default false
        ) RETURNS real AS $$

        DECLARE
        calculationYear integer; 
        trafficTable varchar;
        km_muutos_bussi real default 0;
        km_muutos_hlauto real default 0;
        kmuoto_hkmvrk real;
        bussi real ;
        hlauto real ;
        raide real ;
        muu real ;
        gco2_km real;
        km real;

        BEGIN 
            IF pop_or_employ <= 0 OR pop_or_employ IS NULL
        THEN RETURN 0;

        else

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
            WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
            ELSE calculationYears[1]
            END;

        /* Matkat ja kuormitukset */
        EXECUTE format('SELECT hlt_table FROM traffic.hlt_lookup WHERE mun::int = %L', municipality)
            INTO trafficTable;

        IF zone::bigint NOT IN (1, 2, 6, 10, 837101) THEN
            EXECUTE FORMAT('SELECT bussi
                FROM traffic.hlt_kmchange WHERE zone = CASE
                    WHEN LEFT(%1$L::varchar, 5)::int IN (3, 99931, 99932) THEN 3
                    WHEN LEFT(%1$L::varchar, 5)::int IN (4, 99941, 99942) THEN 4
                    WHEN LEFT(%1$L::varchar, 5)::int IN (5, 99951, 99952) THEN 5
                    ELSE 5 END', zone)
                INTO km_muutos_bussi;

            EXECUTE FORMAT('SELECT hlauto
                FROM traffic.hlt_kmchange WHERE zone = CASE
                    WHEN LEFT(%1$L::varchar, 5)::int IN (3, 99931, 99932) THEN 3
                    WHEN LEFT(%1$L::varchar, 5)::int IN (4, 99941, 99942) THEN 4
                    WHEN LEFT(%1$L::varchar, 5)::int IN (5, 99951, 99952) THEN 5
                    ELSE 5 END', zone)
                INTO km_muutos_hlauto;
        END IF;

        EXECUTE FORMAT('SELECT bussi
        FROM traffic.%1$I
        WHERE zone = CASE
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO bussi;

        EXECUTE FORMAT(
            'SELECT raide
                FROM traffic.%1$I
                WHERE zone = CASE 
                WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO raide;

        EXECUTE FORMAT('SELECT hlauto
        FROM traffic.%1$I
        WHERE zone = CASE 
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO hlauto;

        EXECUTE FORMAT('SELECT muu
        FROM traffic.%1$I
        WHERE zone = CASE 
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO muu;

        muu := CASE WHEN includeLongDistance THEN muu * 1.6 ELSE 1 END;

        bussi := (
            CASE WHEN centdist > 2 AND centdist < 10
                    AND zone IN (3, 5, 99931, 99932, 99951, 99952, 81, 82, 83, 84, 85, 86, 87)
                    THEN COALESCE(bussi + (centdist - 2) * km_muutos_bussi, 0)
                WHEN centdist > 2
                    AND zone IN (4, 99941, 99942)
                THEN COALESCE(bussi - (centdist - 2) * km_muutos_bussi, 0)
            ELSE bussi END
        ) * CASE WHEN includeLongDistance THEN 3.3 ELSE 1 END; -- HLT-based multipliers for 

        hlauto := (
            CASE WHEN centdist > 2 AND centdist < 10
                    AND zone IN (3, 5, 99931, 99932, 99951, 99952, 81, 82, 83, 84, 85, 86, 87)
                    THEN COALESCE(hlauto + (centdist - 2) * km_muutos_hlauto, 0)
                WHEN centdist > 2 AND zone IN (4, 99941, 99942)
                    THEN COALESCE(hlauto - (centdist - 2) * km_muutos_hlauto, 0)
            ELSE hlauto END
        ) * CASE WHEN includeLongDistance THEN 1.2 ELSE 1 END;

        IF mode = 'raide' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901)
                    THEN $3 + $4 * 0.4 + ($5 * (1.01 ^ ($2 - RIGHT($1::varchar,4)::int + 1)) - $5)
                WHEN LEFT($1::varchar,5)::int IN (99912, 99922, 99932, 99942, 99952, 99962, 99902)
                    THEN $3 + $4 * 0.5 + ($5 * (1.01 ^ ($2 - RIGHT($1::varchar,4)::int + 1)) - $5)
                ELSE $3 END'
                INTO kmuoto_hkmvrk
                USING zone, calculationYear, raide, bussi, hlauto;
        ELSIF mode = 'bussi' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901)
                    THEN $2 * 0.6
                WHEN LEFT($1::varchar,5)::int IN (99912, 99922, 99932, 99942, 99952, 99962, 99902)
                    THEN $2 * 0.5
                ELSE $2 END'
                INTO kmuoto_hkmvrk
                USING zone, bussi;
        ELSIF mode = 'hlauto' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901, 99912, 99922, 99932, 99942, 99952, 99962, 99902) THEN
                $3 * (0.99 ^ ($2 - RIGHT($1::varchar,4)::int + 1))
            ELSE $3 END'
            INTO kmuoto_hkmvrk USING zone,
            calculationYear, hlauto;
        ELSIF mode = 'muu' THEN
            kmuoto_hkmvrk := muu;
        END IF;

        -- mode_power_distribution: Kulkumuotojen käyttövoimajakauma.
        -- power_kwhkm: Energian keskikulutus käyttövoimittain [kWh/km].
        EXECUTE FORMAT(
            'WITH RECURSIVE
            power_distribution AS (
                SELECT
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut]
                        as distribution
                    FROM traffic.mode_power_distribution
                        WHERE year = %1$L
                            AND scenario = %2$L::varchar
                            AND mun = %3$L::int
                            AND kmuoto = %4$L::varchar
            ), power_kwhkm as (
                SELECT 
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as kwhkm
                    FROM traffic.power_kwhkm
                        WHERE year = %1$L
                            AND scenario = %2$L::varchar
                            AND kmuoto = %4$L::varchar
                LIMIT 1
            ), 
            -- Kasvihuonekaasupäästöjen keskimääräiset ominaispäästökertoimet [gCO2-ekv/kWh] määritellään
            -- käyttövoimien ominaispäästökertoimien suoriteosuuksilla painotettuna keskiarvona huomioiden samalla niiden bio-osuudet.
            fossils as (
                -- Käyttövoimien fossiiliset osuudet [ei yksikköä].
                SELECT array[share, 1, share, 1, share, share, 1, 1, share] as share
                    FROM traffic.power_fossil_share pfs
                        WHERE pfs.year = %1$L
                        AND pfs.scenario =  %2$L LIMIT 1
            ), electricity_gco2kwh AS (
                -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                SELECT el.gco2kwh::int AS gco2
                FROM energy.electricity el
                    WHERE el.year::int = %1$s::int
                    AND el.scenario::varchar = %2$L
                    AND el.metodi = ''em''
                    AND el.paastolaji = ''tuotanto'' LIMIT 1
            ), gco2kwh_matrix as (
                SELECT 
                -- Käyttövoimien  kasvihuonekaasujen ominaispäästökerroin käytettyä energiayksikköä kohti [gCO2-ekv/kWh].
                array( SELECT 
                    -- Dummy, jolla huomioidaan sähkön käyttö sähköautoissa, pistokehybrideissä ja polttokennoautojen vedyn tuotannossa [ei yksikköä].
                    el.gco2 * unnest(array[0, 0, 0, 0, 0.5, 0.5, 1, 2.5, 0]) +
                    -- phev_b ja phev_d saavat bensiinin ja dieselin ominaispäästöt = 241 & 237 gco2/kwh
                    -- Etanolin päästöt vuonna 2017 = 49, tuotannon kehityksen myötä n. 0.8 parannus per vuosi
                    unnest(array[241, (49 - (%1$s::int - 2017) * 0.8), 237, 80, 241, 237, 0, 0, 189]) *
                    unnest(fossils.share) *
                    unnest(array[1, 1, 1, 1, 0.5, 0.5, 0, 0, 1])
                ) as arr FROM electricity_gco2kwh el, fossils
            ), co2_km as (
                SELECT
                    unnest(distribution) * unnest(kwhkm) * unnest(gco2kwh_matrix.arr) as gco2km
                FROM power_distribution, power_kwhkm, gco2kwh_matrix
            ) SELECT SUM(gco2km)::real FROM co2_km',
                calculationYear, -- 1
                calculationScenario, -- 2
                municipality, -- 3 
                mode -- 4
            ) INTO gco2_km;
            
        EXECUTE FORMAT('
            WITH RECURSIVE 
                traffic_load as (
                SELECT %4$I as unitload
                    FROM traffic.%8$I
                        WHERE year::int = %1$L::int
                            AND scenario = %2$L
                            AND mun::int = %3$L::int
                        LIMIT 1
            ),  work_share as (
                SELECT %4$I::real as share_w
                FROM traffic.hlt_workshare
                WHERE zone = CASE
                    WHEN LEFT(%5$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%5$L::varchar, 3)::int = 999
                        THEN left(right(%5$L, 2), 1)::int
                    WHEN %5$s::bigint = 837101 THEN 6
                    WHEN %5$s::bigint IN (81,82,83,84,85,86,87) THEN 5
                    ELSE %5$s::bigint END LIMIT 1
            ),  distance as (
                SELECT 
                    %7$s::int * %9$L::real * %10$L::real *
                    COALESCE(CASE WHEN %6$L = ''pop'' THEN   (1 - COALESCE(share_w, 0.1) - CASE WHEN %11$L = TRUE THEN 0.05 ELSE 0 END)::real ELSE COALESCE(share_w + CASE WHEN %11$L = TRUE THEN 0.05 ELSE 0 END, 0.1)::real END, 0)
                    / unitload::real
                as km
                    FROM traffic_load, work_share
            ) SELECT SUM(km)::real FROM distance',
                calculationYear, -- 1
                calculationScenario, -- 2
                municipality, -- 3 
                mode, -- 4
                zone, -- 5
                traffictype, -- 6
                COALESCE(pop_or_employ,0), -- 7
                CASE WHEN traffictype = 'pop' THEN 'citizen_traffic_stress' ELSE 'workers_traffic_stress' END, -- 8, asukkaiden tai työssäkäyvien kulkumuotojen keskikuormitukset laskentavuonna [hkm/km].
                kmuoto_hkmvrk, -- 9
                CASE WHEN traffictype = 'pop' THEN 365 ELSE 365 END, -- 10, kuormitus?  Tilastojen mukaan tehollisia työpäiviä keskimäärin noin 228-230 per vuosi ?
                includeBusinessTravel -- 11
            ) INTO km;

        RETURN gco2_km * km;

        END IF;

        END;

        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_CalculateEmissions(
            municipalities integer[],
            aoi regclass, -- Tutkimusalue | area of interest
            includeLongDistance boolean default false,
            includeBusinessTravel boolean default true,
            calculationYears integer[] default array[date_part('year', now()),2017,2050], -- Laskennan viitearvojen year || calculation reference year
            calculationScenario varchar default 'wem', -- PITKO-kehitysskenaario
            method varchar default 'em', -- Päästöallokoinnin laskentamenetelmä
            electricityType varchar default 'tuotanto', -- Sähkön päästölaji
            baseYear integer default NULL, -- Laskennan lähtövuosi
            targetYear integer default NULL, -- Laskennan tavoitevuosi
            plan_areas regclass default NULL, -- Taulu, jossa käyttötarkoitusalueet tai vastaavat
            plan_centers regclass default NULL, -- Taulu, jossa kkreskusverkkotiedot 
            plan_transit regclass default NULL -- Taulu, jossa intensiivinen joukkoliikennejärjestelmä
        )    
        RETURNS TABLE(
            geom geometry(MultiPolygon, 3067),
            xyind varchar(13),
            mun int,
            zone bigint,
            year date,
            floorspace int,
            pop smallint,
            employ smallint,
            tilat_vesi_tco2 real,
            tilat_lammitys_tco2 real,
            tilat_jaahdytys_tco2 real,
            sahko_kiinteistot_tco2 real,
            sahko_kotitaloudet_tco2 real,
            sahko_palv_tco2 real,
            sahko_tv_tco2 real,
            liikenne_as_tco2 real,
            liikenne_tp_tco2 real,
            liikenne_tv_tco2 real,
            liikenne_palv_tco2 real,
            rak_korjaussaneeraus_tco2 real,
            rak_purku_tco2 real,
            rak_uudis_tco2 real,
            sum_yhteensa_tco2 real,
            sum_lammonsaato_tco2 real,
            sum_liikenne_tco2 real,
            sum_sahko_tco2 real,
            sum_rakentaminen_tco2 real
        )
        AS $$
        DECLARE
            calculationYear integer;
            localbuildings boolean;
            refined boolean;
            defaultdemolition boolean;
            initialScenario varchar;
            initialYear integer;
            grams_to_tons real default 0.000001; -- Muuntaa grammat tonneiksi (0.000001) [t/g].
        BEGIN

            /* Jos valitaan 'static'-skenaario, eli huomioidaan laskennassa vain yhdyskuntarakenteen muutos, asetetaan PITKO-skenaarioksi 'wem'.
                Samalla sidotaan laskennan referenssivuodeksi laskennan aloitusyear.
                If the 'static' skenaario is selected, i.e. only changes in the urban structure are taken into account, set the PITKO skenaario to 'wem'.
                At the same time, fix the calculation reference year into current year / baseYear */
            IF calculationScenario = 'static'
                THEN
                    calculationScenario := 'wem';
                    initialScenario := 'static';
            END IF;

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
            END;

            IF baseYear IS NULL
                THEN baseYear := calculationYear;
            END IF;

            /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää energiamuototiedon */
            /* Checking, whether or not local building data with energy source information is present */
            SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'energiam'
                AND NOT attisdropped
            ) INTO localbuildings;

            /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää tarkemmat TOL-johdannaiset */
            /* Checking, whether or not local building data with detailed usage source information is present */
            SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'myymal_pien_ala'
                AND NOT attisdropped
            ) INTO refined;

            /* Numeeristetaan suunnitelma-aineistoa | 'Numerizing' the given plan data */
            DROP TABLE IF EXISTS grid_temp;
            CREATE TEMP TABLE grid_temp AS
                SELECT * FROM functions.CO2_GridProcessing(municipalities, aoi, calculationYear, baseYear, 1.25, targetYear, plan_areas, plan_centers, plan_transit);
            DROP TABLE IF EXISTS grid;
            ALTER TABLE grid_temp RENAME TO grid;

            --------------------------------------------------------

            IF targetYear IS NOT NULL THEN

                /* Luodaan pohja-aineisto rakennusdatan työstölle */
                /* Building a template for manipulating building data */
                IF calculationYear = baseYear
                    THEN
                        EXECUTE format(
                            'CREATE TEMP TABLE IF NOT EXISTS rak_initial AS
                                SELECT * FROM grid_globals.buildings
                                WHERE rakv::int != 0
                                    AND xyind::varchar IN
                                        (SELECT grid.xyind::varchar FROM grid)
                                    AND rakv::int < %L',
                        calculationYear);
                    ELSE 
                        ALTER TABLE grid2 RENAME to rak_initial;
                END IF;

                SELECT CASE WHEN k_poistuma > 999998 AND k_poistuma < 1000000 THEN TRUE ELSE FALSE END FROM grid LIMIT 1 INTO defaultdemolition;

                /* Luodaan väliaikainen taulu rakennusten purkamisen päästölaskentaa varten
                Creating a temporary table for emission calculations of demolishing buildings
                Default demolishing rate: 0.15% annually of existing building stock.
                Huuhka, S. & Lahdensivu J. Statistical and geographical study on demolish buildings. Building research and information vol 44:1, 73-96. */
                IF defaultdemolition = TRUE THEN
                CREATE TEMP TABLE poistuma_alat AS 
                    SELECT rak_initial.xyind, 
                        0.0015 * SUM(rakyht_ala)::real rakyht,
                        0.0015 * SUM(erpien_ala)::real erpien,
                        0.0015 * SUM(rivita_ala)::real rivita,
                        0.0015 * SUM(askert_ala)::real askert,
                        0.0015 * SUM(liike_ala)::real liike,
                        0.0015 * SUM(tsto_ala)::real tsto,
                        0.0015 * SUM(liiken_ala)::real liiken,
                        0.0015 * SUM(hoito_ala)::real hoito,
                        0.0015 * SUM(kokoon_ala)::real kokoon,
                        0.0015 * SUM(opetus_ala)::real opetus,
                        0.0015 * SUM(teoll_ala)::real teoll,
                        0.0015 * SUM(varast_ala)::real varast,
                        0.0015 * SUM(muut_ala)::real muut
                    FROM rak_initial
                    WHERE rakyht_ala > 0
                    GROUP BY rak_initial.xyind;

                ELSE

                    CREATE TEMP TABLE poistuma_alat AS 
                    WITH poistuma AS (
                        SELECT grid.xyind::varchar, SUM(k_poistuma) AS poistuma FROM grid GROUP BY grid.xyind
                    ),
                    buildings AS (
                        SELECT rak_initial.xyind, 
                            SUM(rakyht_ala) rakyht_ala,
                            SUM(erpien_ala) erpien_ala,
                            SUM(rivita_ala) rivita_ala,
                            SUM(askert_ala) askert_ala,
                            SUM(liike_ala) liike_ala,
                            SUM(tsto_ala) tsto_ala,
                            SUM(liiken_ala) liiken_ala,
                            SUM(hoito_ala) hoito_ala,
                            SUM(kokoon_ala) kokoon_ala,
                            SUM(opetus_ala) opetus_ala,
                            SUM(teoll_ala) teoll_ala,
                            SUM(varast_ala) varast_ala,
                            SUM(muut_ala) muut_ala
                        FROM rak_initial GROUP BY rak_initial.xyind
                    )
                    SELECT poistuma.xyind,
                        COALESCE(poistuma * (erpien_ala::real / NULLIF(rakyht_ala::real,0)),0) erpien,
                        COALESCE(poistuma * (rivita_ala::real / NULLIF(rakyht_ala::real,0)),0) rivita,
                        COALESCE(poistuma * (askert_ala::real / NULLIF(rakyht_ala::real,0)),0) askert,
                        COALESCE(poistuma * (liike_ala::real / NULLIF(rakyht_ala::real,0)),0) liike,
                        COALESCE(poistuma * (tsto_ala::real / NULLIF(rakyht_ala::real,0)),0) tsto,
                        COALESCE(poistuma * (liiken_ala::real / NULLIF(rakyht_ala::real,0)),0) liiken,
                        COALESCE(poistuma * (hoito_ala::real / NULLIF(rakyht_ala::real,0)),0) hoito,
                        COALESCE(poistuma * (kokoon_ala::real / NULLIF(rakyht_ala::real,0)),0) kokoon,
                        COALESCE(poistuma * (opetus_ala::real / NULLIF(rakyht_ala::real,0)),0) opetus,
                        COALESCE(poistuma * (teoll_ala::real / NULLIF(rakyht_ala::real,0)),0) teoll,
                        COALESCE(poistuma * (varast_ala::real / NULLIF(rakyht_ala::real,0)),0) varast,
                        COALESCE(poistuma * (muut_ala::real / NULLIF(rakyht_ala::real,0)),0) muut
                    FROM poistuma
                        LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
                    WHERE poistuma > 0;
                END IF;

                /* Kyselyt: Puretaan rakennukset datasta ja rakennetaan uusia */
                /* Valitaan ajettava kysely sen perusteella, millaista rakennusdataa on käytössä */
                /* Queries: Demolishing and buildings buildings from the building data */
                /* Choose correct query depending on the type of building data in use */
                RAISE NOTICE 'Updating building data';
                IF localbuildings = true THEN
                    IF refined = true THEN 
                        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, myymal_pien_ala :: int, myymal_super_ala :: int, myymal_hyper_ala :: int, myymal_muu_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, teoll_elint_ala :: int, teoll_tekst_ala :: int, teoll_puu_ala :: int, teoll_paper_ala :: int, teoll_miner_ala :: int, teoll_kemia_ala :: int, teoll_kone_ala :: int, teoll_mjalos_ala :: int, teoll_metal_ala :: int, teoll_vesi_ala :: int, teoll_energ_ala :: int, teoll_yhdysk_ala :: int, teoll_kaivos_ala :: int, teoll_muu_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM functions.CO2_UpdateBuildingsRefined(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYears, baseYear, targetYear, calculationScenario);
                    ELSE 
                        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM functions.CO2_UpdateBuildingsLocal(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYears, baseYear, targetYear, calculationScenario);
                    END IF;
                    CREATE INDEX ON grid2 (rakv, energiam);
                ELSE
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM functions.CO2_UpdateBuildings(''rak_initial'', ''grid'', %L)) updatedbuildings', year);
                    CREATE INDEX ON grid2 (rakv);        
                END IF;
                DROP TABLE IF EXISTS rak_initial;

            ELSE

                /* Valitaan rakennustietojen väliaikaisen taulun generointikysely ajettavaksi sen perusteella, millaista rakennusdataa on käytössä */
                /* Choose correct query for creating a temporary building data table depending on the type of building data in use */
                IF localbuildings = true THEN
                    IF refined = true THEN

                        CREATE TEMP TABLE IF NOT EXISTS
                            grid2 AS SELECT
                            b.xyind::varchar,
                            rakv::int,
                            energiam::varchar,
                            rakyht_ala::int,
                            asuin_ala :: int,
                            erpien_ala :: int,
                            rivita_ala :: int,
                            askert_ala :: int,
                            liike_ala :: int,
                            myymal_ala :: int,
                            myymal_pien_ala :: int,
                            myymal_super_ala :: int,
                            myymal_hyper_ala :: int,
                            myymal_muu_ala :: int,
                            majoit_ala :: int,
                            asla_ala :: int,
                            ravint_ala :: int,
                            tsto_ala :: int,
                            liiken_ala :: int,
                            hoito_ala :: int,
                            kokoon_ala :: int,
                            opetus_ala :: int,
                            teoll_ala :: int,
                            teoll_elint_ala :: int,
                            teoll_tekst_ala :: int,
                            teoll_puu_ala :: int,
                            teoll_paper_ala :: int,
                            teoll_miner_ala :: int,
                            teoll_kemia_ala :: int,
                            teoll_kone_ala :: int,
                            teoll_mjalos_ala :: int,
                            teoll_metal_ala :: int,
                            teoll_vesi_ala :: int,
                            teoll_energ_ala :: int,
                            teoll_yhdysk_ala :: int,
                            teoll_kaivos_ala :: int,
                            teoll_muu_ala :: int,
                            varast_ala :: int,
                            muut_ala :: int
                            FROM grid_globals.buildings b
                                WHERE rakv::int != 0
                                AND b.xyind::varchar IN
                                    (SELECT grid.xyind::varchar FROM grid);
                    ELSE 
                        CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT b.xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM grid_globals.buildings b WHERE rakv::int != 0 AND b.xyind IN (SELECT grid.xyind FROM grid);
                    END IF;
                    CREATE INDEX ON grid2 (rakv, energiam);
                ELSE
                        CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT b.xyind::varchar, rakv::int, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM grid_globals.buildings b WHERE rakv::int != 0 AND b.xyind IN (SELECT grid.xyind FROM grid);
                    CREATE INDEX ON grid2 (rakv); -- update?
                END IF;

            END IF;

            /* Luodaan väliaikainen taulu laskennan tuloksille */
            /* Creating temporary table for analysis results */
            DROP TABLE IF EXISTS results;
            CREATE TEMP TABLE results AS SELECT
                ST_SetSRID(g.geom,3067)::geometry(MultiPolygon, 3067),
                g.xyind::varchar(13),
                g.mun::int,
                g.zone::bigint,
                NULL::date as year,
                0::int floorspace,
                COALESCE(g.pop, 0)::smallint pop,
                COALESCE(g.employ, 0)::smallint employ,
                0::real tilat_vesi_tco2,
                0::real tilat_lammitys_tco2,
                0::real tilat_jaahdytys_tco2,
                0::real sahko_kiinteistot_tco2,
                0::real sahko_kotitaloudet_tco2,
                0::real sahko_palv_tco2,
                0::real sahko_tv_tco2,
                0::real liikenne_as_tco2,
                0::real liikenne_tp_tco2,
                0::real liikenne_tv_tco2,
                0::real liikenne_palv_tco2,
                0::real rak_korjaussaneeraus_tco2,
                0::real rak_purku_tco2,
                0::real rak_uudis_tco2,
                0::real sum_yhteensa_tco2,
                0::real sum_lammonsaato_tco2,
                0::real sum_liikenne_tco2,
                0::real sum_sahko_tco2,
                0::real sum_rakentaminen_tco2
            FROM grid g
                WHERE (COALESCE(g.pop,0) > 0 OR COALESCE(g.employ,0) > 0 )
                    OR g.xyind::varchar IN (SELECT DISTINCT ON (grid2.xyind) grid2.xyind::varchar FROM grid2);

            /* Kun käytetään static-skenaariota tulevaisuuslaskennassa, aseta laskenta lähtövuoden referenssitasolle */
            /* When using a 'static' scenario in the future scenario calculation, set the calculation reference year to baseYear */
            IF initialScenario = 'static'
                AND targetYear IS NOT NULL THEN
                initialYear := calculationYear;
                calculationYear := baseYear;
                calculationYears[1] := baseYear;
            END IF;

            ALTER TABLE grid2 ADD COLUMN IF NOT EXISTS mun int;
            UPDATE grid2 g2
                SET mun = g.mun
                FROM grid g
                WHERE g.xyind::varchar = g2.xyind::varchar;
            
            /* Täytetään tulostaulukko laskennan tuloksilla */
            /* Fill results table with calculations */

            IF localbuildings = TRUE THEN

                UPDATE results SET 
                    tilat_vesi_tco2 = COALESCE(buildings.property_water_gco2, 0) * grams_to_tons,
                    tilat_lammitys_tco2 = COALESCE(buildings.property_heat_gco2, 0) * grams_to_tons
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Käyttöveden lämmitys | Heating of water */
                    SUM((SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method, g2.energiam)))
                    AS property_water_gco2,
                    /* Rakennusten lämmitys | Heating of buildings */
                    SUM((SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method, g2.energiam)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method, g2.energiam)))
                    AS property_heat_gco2
                    FROM grid2 g2
                        GROUP BY g2.xyind) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;

            ELSE

                UPDATE results SET 
                    tilat_vesi_tco2 = COALESCE(buildings.property_water_gco2, 0) * grams_to_tons,
                    tilat_lammitys_tco2 = COALESCE(buildings.property_heat_gco2, 0) * grams_to_tons
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Käyttöveden lämmitys | Heating of water */
                    SUM((SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method)))
                    AS property_water_gco2,
                    /* Rakennusten lämmitys | Heating of buildings */
                    SUM((SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method)) +
                        (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method)))
                    AS property_heat_gco2
                    FROM grid2 g2
                    GROUP BY g2.xyind) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;
            END IF;

            UPDATE results SET 
                tilat_jaahdytys_tco2 = COALESCE(buildings.property_cooling_gco2 * grams_to_tons, 0),
                sahko_kiinteistot_tco2 = COALESCE(buildings.sahko_kiinteistot_co2 * grams_to_tons, 0),
                sahko_kotitaloudet_tco2 = COALESCE(buildings.sahko_kotitaloudet_co2 * grams_to_tons, 0),
                rak_korjaussaneeraus_tco2 = COALESCE(buildings.rak_korjaussaneeraus_co2 * grams_to_tons, 0)
            FROM
                (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                /* Rakennusten jäähdytys | Cooling of buildings */
                SUM((SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT functions.CO2_PropertyCooling(calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv)))
                AS property_cooling_gco2,
                /* Kiinteistösähkö | Electricity consumption of property technology */
                SUM((SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, liike_ala,  'liike', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT functions.CO2_ElectricityProperty(calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv)))
                AS sahko_kiinteistot_co2,
                /* Kotitalouksien sähkönkulutus | Energy consumption of households */
                SUM((SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien')) +
                    (SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita')) +
                    (SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert')))
                AS sahko_kotitaloudet_co2,
                /* Korjausrakentaminen ja saneeraus | Renovations and large-scale overhauls of buildings */
                SUM((SELECT functions.CO2_BuildRenovate(erpien_ala, calculationYears, 'erpien', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(rivita_ala, calculationYears, 'rivita', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(askert_ala, calculationYears, 'askert', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(liike_ala, calculationYears, 'liike', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(tsto_ala, calculationYears, 'tsto', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(liiken_ala, calculationYears, 'liiken', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(hoito_ala, calculationYears, 'hoito', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(kokoon_ala, calculationYears, 'kokoon', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(opetus_ala, calculationYears, 'opetus', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(teoll_ala, calculationYears, 'teoll', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(varast_ala, calculationYears, 'varast', g2.rakv, calculationScenario)) +
                    (SELECT functions.CO2_BuildRenovate(muut_ala, calculationYears, 'muut', g2.rakv, calculationScenario)))
                AS rak_korjaussaneeraus_co2
                    FROM grid2 g2
                        GROUP BY g2.xyind
                ) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;
        
            IF refined = FALSE THEN

                UPDATE results
                SET sahko_palv_tco2 = COALESCE(buildings.sahko_palv_co2 * grams_to_tons, 0),
                    sahko_tv_tco2 = COALESCE(buildings.sahko_tv_co2 * grams_to_tons, 0),
                    liikenne_tv_tco2 = COALESCE(buildings.liikenne_tv_co2 * grams_to_tons, 0),
                    liikenne_palv_tco2 = COALESCE(buildings.liikenne_palv_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Palveluiden sähkönkulutus | Electricity consumption of services */
                    SUM((SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, liike_ala, 'liike')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +	
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, opetus_ala, 'opetus')))
                    AS sahko_palv_co2,
                    /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                    SUM((SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_ala, 'teoll')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS sahko_tv_co2,
                    /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                    SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS liikenne_tv_co2,
                    /* Palveluliikenne | Service traffic */
                    SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_ala, 'myymal')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut')))
                    AS liikenne_palv_co2
                    FROM grid2 g2
                    GROUP BY g2.xyind) buildings
                WHERE buildings.xyind = results.xyind;
                
            ELSE 

                UPDATE results
                SET sahko_palv_tco2 = COALESCE(buildings.sahko_palv_co2 * grams_to_tons, 0),
                    sahko_tv_tco2 = COALESCE(buildings.sahko_tv_co2 * grams_to_tons, 0),
                    liikenne_tv_tco2 = COALESCE(buildings.liikenne_tv_co2 * grams_to_tons, 0),
                    liikenne_palv_tco2 = COALESCE(buildings.liikenne_palv_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Palveluiden sähkönkulutus | Electricity consumption of services */
                    SUM((SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_super_ala, 'myymal_super')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, majoit_ala, 'majoit')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +	
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, opetus_ala, 'opetus')))
                    AS sahko_palv_co2,
                    /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                    SUM((SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                        (SELECT functions.CO2_ElectricityIWHS(calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS sahko_tv_co2,
                    /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                    SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS liikenne_tv_co2,
                    /* Palveluliikenne | Service traffic */
                    SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_super_ala, 'myymal_super')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, majoit_ala, 'majoit')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus')) +
                        (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut')))
                    AS liikenne_palv_co2
                        FROM grid2 g2
                        GROUP BY g2.xyind
                    ) buildings
                WHERE buildings.xyind = results.xyind;
            END IF;

            IF targetYear IS NOT NULL THEN
                UPDATE results SET
                    rak_uudis_tco2 = COALESCE(buildings.rak_uudis_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (grid2.xyind) grid2.xyind,
                    SUM((SELECT functions.CO2_BuildConstruct(erpien_ala, calculationYears, 'erpien', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(rivita_ala, calculationYears, 'rivita', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(askert_ala, calculationYears, 'askert', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(liike_ala, calculationYears, 'liike', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(tsto_ala, calculationYears, 'tsto', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(liiken_ala, calculationYears, 'liiken', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(hoito_ala, calculationYears, 'hoito', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(kokoon_ala, calculationYears, 'kokoon', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(opetus_ala, calculationYears, 'opetus', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(teoll_ala, calculationYears, 'teoll', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(varast_ala, calculationYears, 'varast', calculationScenario)) +
                        (SELECT functions.CO2_BuildConstruct(muut_ala, calculationYears, 'muut', calculationScenario))
                    ) AS rak_uudis_co2
                        FROM grid2  
                            WHERE grid2.rakv = calculationYear
                            GROUP BY grid2.xyind
                    ) buildings
                            WHERE buildings.xyind = results.xyind;

                /* Lasketaan rakennusten purkamisen päästöt */
                /* Calculating emissions for demolishing buildings */
                UPDATE results SET rak_purku_tco2 = COALESCE(poistot.rak_purku_co2 * grams_to_tons, 0)
                    FROM (SELECT p.xyind,
                        SUM((SELECT functions.CO2_BuildDemolish(p.erpien::real, calculationYears, 'erpien', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.rivita::real, calculationYears, 'rivita', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.askert::real, calculationYears, 'askert', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.liike::real, calculationYears, 'liike', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.tsto::real, calculationYears, 'tsto', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.liiken::real, calculationYears, 'liiken', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.hoito::real, calculationYears, 'hoito', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.kokoon::real, calculationYears, 'kokoon', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.opetus::real, calculationYears, 'opetus', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.teoll::real, calculationYears, 'teoll', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.varast::real, calculationYears, 'varast', calculationScenario)) +
                            (SELECT functions.CO2_BuildDemolish(p.muut::real, calculationYears, 'muut', calculationScenario))
                        ) AS rak_purku_co2
                            FROM poistuma_alat p
                                GROUP BY p.xyind
                        ) poistot
                            WHERE results.xyind = poistot.xyind;

            END IF;

            UPDATE results SET
                liikenne_as_tco2 = COALESCE(pop.liikenne_as_co2 * grams_to_tons, 0),
                liikenne_tp_tco2 = COALESCE(pop.liikenne_tp_co2 * grams_to_tons, 0),
                sahko_kotitaloudet_tco2 = COALESCE(results.sahko_kotitaloudet_tco2 + NULLIF(pop.sahko_kotitaloudet_co2_as * grams_to_tons, 0), 0)
            FROM
                (SELECT g.xyind,
                    SUM((SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'bussi', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'raide', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'hlauto', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'muu', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)))
                    AS liikenne_as_co2,
                    SUM((SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'bussi', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'raide', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'hlauto', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'muu', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)))
                    AS liikenne_tp_co2,
                    SUM((SELECT functions.CO2_ElectricityHousehold(g.mun, calculationYears, calculationScenario, g.pop, NULL)))
                    AS sahko_kotitaloudet_co2_as
                    FROM grid g
                        WHERE (g.pop IS NOT NULL AND g.pop > 0)
                        OR (g.employ IS NOT NULL AND g.employ > 0)
                GROUP BY g.xyind) pop
            WHERE pop.xyind = results.xyind;

            IF initialScenario = 'static' AND targetYear IS NOT NULL
                THEN calculationYear := initialYear; calculationYears[1] := initialYear;
            END IF;

            UPDATE results r SET
                year = to_date(calculationYear::varchar, 'YYYY'),
                sum_lammonsaato_tco2 =
                    COALESCE(r.tilat_vesi_tco2, 0) +
                    COALESCE(r.tilat_lammitys_tco2, 0) +
                    COALESCE(r.tilat_jaahdytys_tco2, 0),
                sum_liikenne_tco2 =
                    COALESCE(r.liikenne_as_tco2, 0) +
                    COALESCE(r.liikenne_tp_tco2, 0) +
                    COALESCE(r.liikenne_tv_tco2, 0) +
                    COALESCE(r.liikenne_palv_tco2, 0), 
                sum_sahko_tco2 =
                    COALESCE(r.sahko_kiinteistot_tco2, 0) +
                    COALESCE(r.sahko_kotitaloudet_tco2, 0) +
                    COALESCE(r.sahko_palv_tco2, 0) +
                    COALESCE(r.sahko_tv_tco2, 0),
                sum_rakentaminen_tco2 =
                    COALESCE(r.rak_korjaussaneeraus_tco2, 0) +
                    COALESCE(r.rak_purku_tco2, 0) +
                    COALESCE(r.rak_uudis_tco2, 0);

            UPDATE results r SET
                sum_yhteensa_tco2 =
                    COALESCE(r.sum_lammonsaato_tco2,0) +
                    COALESCE(r.sum_liikenne_tco2,0) +
                    COALESCE(r.sum_sahko_tco2,0) +
                    COALESCE(r.sum_rakentaminen_tco2,0);

            UPDATE results res
            SET floorspace = r.rakyht_ala
            FROM (
                SELECT DISTINCT ON (grid2.xyind) grid2.xyind,
                    SUM(grid2.rakyht_ala) rakyht_ala
                FROM grid2
                    WHERE grid2.rakv::int != 0
                    GROUP BY grid2.xyind
            ) r
            WHERE res.xyind = r.xyind;

            /* Poistetaan purkulaskennoissa käytetty väliaikainen taulu */
            /* Remove the temporary table used in demolishing calculationg */
            DROP TABLE IF EXISTS poistuma_alat;

            IF targetYear IS NULL OR targetYear = calculationYear THEN
                DROP TABLE grid, grid2;
            END IF;

            RETURN QUERY SELECT * FROM results;
            DROP TABLE results;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION
        functions.CO2_CalculateEmissionsLoop(
            municipalities integer[],
            aoi regclass, -- Tutkimusalue | area of interest
            includeLongDistance boolean,
            includeBusinessTravel boolean,
            calculationScenario varchar, -- PITKO:n mukainen scenario
            method varchar, -- Päästöallokointimenetelmä, 'em' tai 'hjm'
            electricityType varchar, -- Sähkön päästölaji, 'hankinta' tai 'tuotanto'
            baseYear integer, -- Laskennan lähtövuosi
            targetYear integer, -- Laskennan tavoitevuosi
            plan_areas regclass default null, -- Taulu, jossa käyttötarkoitusalueet tai vastaavat
            plan_centers regclass default null, -- Taulu, jossa keskusverkkotiedot 
            plan_transit regclass default null -- Taulu, jossa intensiivinen joukkoliikennejärjestelmä,
        )
        RETURNS TABLE(
            geom geometry(MultiPolygon, 3067),
            xyind varchar(13),
            mun int,
            zone bigint,
            year date,
            floorspace int,
            pop smallint,
            employ smallint,
            tilat_vesi_tco2 real,
            tilat_lammitys_tco2 real,
            tilat_jaahdytys_tco2 real,
            sahko_kiinteistot_tco2 real,
            sahko_kotitaloudet_tco2 real,
            sahko_palv_tco2 real,
            sahko_tv_tco2 real,
            liikenne_as_tco2 real,
            liikenne_tp_tco2 real,
            liikenne_tv_tco2 real,
            liikenne_palv_tco2 real,
            rak_korjaussaneeraus_tco2 real,
            rak_purku_tco2 real,
            rak_uudis_tco2 real,
            sum_yhteensa_tco2 real,
            sum_lammonsaato_tco2 real,
            sum_liikenne_tco2 real,
            sum_sahko_tco2 real,
            sum_rakentaminen_tco2 real
        )
        AS $$
        DECLARE
            calculationYears integer[];
            calculationYear integer;
        BEGIN

            SELECT array(select generate_series(baseYear,targetYear))
            INTO calculationYears;

            FOREACH calculationYear in ARRAY calculationYears
            LOOP

                IF calculationYear = baseYear THEN
                    CREATE TEMP TABLE res AS
                    SELECT * FROM
                        functions.CO2_CalculateEmissions(
                            municipalities, aoi, includeLongDistance, includeBusinessTravel, array[calculationYear, 2017, 2050], calculationScenario, method, electricityType, baseYear, targetYear, plan_areas, plan_centers, plan_transit
                        );
                ELSE 
                    INSERT INTO res
                    SELECT * FROM
                        functions.CO2_CalculateEmissions(
                            municipalities, aoi, includeLongDistance, includeBusinessTravel, array[calculationYear, 2017, 2050], calculationScenario, method, electricityType, baseYear, targetYear, plan_areas, plan_centers, plan_transit
                        );
                END IF;
                
            END LOOP;

            UPDATE res SET zone = CASE
                WHEN LEFT(res.zone::varchar, 5)::int IN (99911, 99912) THEN 1
                WHEN LEFT(res.zone::varchar, 5)::int IN (99921, 99922) THEN 2
                WHEN LEFT(res.zone::varchar, 5)::int IN (99931, 99932) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (99941, 99942) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (99951, 99952) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (6, 99961, 99962, 99901, 99902, 99910) THEN 10
                WHEN LEFT(res.zone::varchar, 5)::int IN (99981, 99982, 99983, 99984, 99985, 99986, 99987) THEN RIGHT(LEFT(res.zone::varchar, 5),2)::int
            ELSE res.zone END;

            RETURN QUERY SELECT * FROM res;
            DROP TABLE IF EXISTS res;

        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade() -> None:
    pass
