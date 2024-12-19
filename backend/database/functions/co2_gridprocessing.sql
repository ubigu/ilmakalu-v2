CREATE SCHEMA IF NOT EXISTS functions;

DROP FUNCTION IF EXISTS functions.CO2_GridProcessing;
CREATE OR REPLACE FUNCTION
functions.CO2_GridProcessing(
    municipalities integer[], -- List of municipality codes (kuntanumero) in integer format, without leading zeroes
    aoi regclass, -- Area of interest
    calculationYear integer, -- Currently processed year in the year-to-year calculation loop
    baseYear integer, -- The initial year, from which calculation started
    targetYear integer default null,
    plan_areas regclass default null,
    plan_transit regclass default null,
    plan_centers regclass default null,
    km2hm2 real default 1.25 -- Floor space to room space -ratio
) RETURNS TABLE (
    geom geometry(MultiPolygon, 3067),
    xyind varchar,
    mun int,
    zone bigint,
    holidayhouses int,
    maa_ha real,
    centdist smallint,
    pop smallint,
    employ smallint,
    k_ap_ala int,
    k_ar_ala int,
    k_ak_ala int,
    k_muu_ala int,
    k_poistuma int,
    alueteho real
)
AS $$
DECLARE
    startYearExists boolean;
    endYearExists boolean;
    kapaExists boolean;
    typeExists boolean;
    completionYearExists boolean;
    pubtrans_zones int[] default ARRAY[3,12,41, 99901, 99902, 99911, 99921, 99931, 99941, 99951, 99961, 99901, 99912, 99922, 99932, 99942, 99952, 99962, 99902, 99913, 99923, 99933, 99943, 99953, 99963, 99903];
BEGIN

IF calculationYear <= baseYear OR targetYear IS NULL OR plan_areas IS NULL THEN
    /* Creating a temporary table with e.g. YKR population and workplace data */
    EXECUTE format(
    'CREATE TEMP TABLE IF NOT EXISTS grid AS SELECT
        DISTINCT ON (grid.xyind, grid.geom)
        ST_SetSRID((ST_DUMP(grid.geom)).geom, 3067) :: geometry(Polygon, 3067) AS geom,
        grid.xyind :: varchar(13),
        grid.mun :: int,
        grid.zone :: bigint,
        grid.holidayhouses :: int,
        clc.maa_ha :: real,
        grid.centdist :: smallint,
        coalesce(pop.v_yht, 0) :: smallint AS pop,
        coalesce(employ.tp_yht, 0) :: smallint AS employ,
        0 :: int AS k_ap_ala,
        0 :: int AS k_ar_ala,
        0 :: int AS k_ak_ala,
        0 :: int AS k_muu_ala,
        0 :: int AS k_poistuma,
        0 :: real AS alueteho
        FROM delineations.grid grid
        LEFT JOIN grid_globals.pop pop
            ON grid.xyind :: varchar = pop.xyind :: varchar
            AND grid.mun :: int = pop.kunta :: int
        LEFT JOIN grid_globals.employ employ
            ON grid.xyind :: varchar = employ.xyind :: varchar
            AND grid.mun :: int = employ.kunta :: int
        LEFT JOIN grid_globals.clc clc 
            ON grid.xyind :: varchar = clc.xyind :: varchar
        WHERE grid.mun::int = ANY(%1$L);'
    , municipalities);
    CREATE INDEX ON grid USING GIST (geom);
    CREATE INDEX ON grid (xyind);
    CREATE INDEX ON grid (zone);
    CREATE INDEX ON grid (mun);

    IF aoi IS NOT NULL THEN
        EXECUTE format(
            'DELETE FROM grid
                WHERE NOT ST_Intersects(st_centroid(grid.geom),
                (SELECT st_union(st_transform(bounds.geom,3067)) FROM %s bounds))', aoi);
    END IF;

    /* Calculate initial aluetehokkuus = built floor square meters divided by the area's land area */    
    WITH buildings as (
        SELECT b.xyind, SUM(b.rakyht_ala)::int AS floorspace
            FROM grid_globals.buildings b
        WHERE b.rakv::int != 0 
        GROUP BY b.xyind
    ) UPDATE grid
        SET alueteho = buildings.floorspace / (grid.maa_ha * 10000)
        FROM buildings
        WHERE buildings.xyind = grid.xyind
            AND grid.maa_ha > 0;

END IF;

    IF targetYear IS NOT NULL AND plan_areas IS NOT NULL THEN

        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS kt AS SELECT * FROM %s', plan_areas);
            ALTER TABLE kt
                ALTER COLUMN geom TYPE geometry(MultiPolygon, 3067) USING ST_Multi(ST_force2d(ST_Transform(geom, 3067)));
            /* Calculate plan surface areas */
            ALTER TABLE kt
                ADD COLUMN IF NOT EXISTS area real default 0;
            UPDATE kt SET area = ST_AREA(kt.geom);
            CREATE INDEX ON kt USING GIST (geom);

        IF plan_centers IS NOT NULL THEN
            EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS kv AS SELECT * FROM %s', plan_centers);
            ALTER TABLE kv
                ALTER COLUMN geom TYPE geometry(Point, 3067) USING ST_force2d(ST_Transform(geom, 3067));
            CREATE INDEX ON kv USING GIST (geom);
        END IF;

        IF plan_transit IS NOT NULL THEN
            EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS pubtrans AS SELECT * FROM %s', plan_transit);
            ALTER TABLE pubtrans
                ALTER COLUMN geom TYPE geometry(Point, 3067) USING ST_force2d(ST_Transform(geom, 3067));
            CREATE INDEX ON pubtrans USING GIST (geom);
        END IF;

        EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_aloitusv') INTO startYearExists;
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_valmisv') INTO endYearExists;
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'year_completion') INTO completionYearExists;
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'type') INTO typeExists;
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = %L::regclass AND attname = %L AND NOT attisdropped)', plan_areas, 'k_ap_ala') INTO kapaExists;

        /* tp_yht column added to data originating from Vasara 2.0, since does not include this information */
        /* k_poistuma is not obligatory, but add it in any case. A default value 999999 will be added later on. */
        ALTER TABLE kt
            ADD COLUMN IF NOT EXISTS k_tp_yht real DEFAULT 0,
            ADD COLUMN IF NOT EXISTS k_poistuma real DEFAULT 0;

        /* Lasketaan käyttötarkoitusalueilta numeeriset arvot grid-ruuduille. */
        IF startYearExists AND endYearExists THEN

            /* Poista kaava-aineistosta kohteet, joita ei toteuteta laskentavuonna */
            DELETE FROM kt 
                WHERE NOT COALESCE(kt.k_aloitusv, baseYear) <= calculationYear AND
                    COALESCE(kt.k_valmisv, targetYear) >= calculationYear;

            /* Poista kaava-aineistosta kohteet, joissa ei ole kerrosalan tai työpaikkojen lisäystä tai poistumaa */
            DELETE FROM kt 
                WHERE COALESCE(kt.k_ap_ala,0) + COALESCE(kt.k_ar_ala,0) + COALESCE(kt.k_ak_ala,0) + COALESCE(kt.k_muu_ala,0) + COALESCE(kt.k_poistuma,0) + COALESCE(kt.k_tp_yht,0) = 0;

            /* Poista ei-käsiteltävät gridin kohteet */
            IF (SELECT COALESCE(COUNT(*),0) FROM kt) = 0 THEN
                DELETE FROM grid
                WHERE (COALESCE(grid.alueteho, 0) = 0 AND COALESCE(grid.employ, 0) = 0 AND COALESCE(grid.pop, 0) = 0);
            ELSE

            DELETE FROM grid
                WHERE (COALESCE(grid.alueteho, 0) = 0 AND COALESCE(grid.employ, 0) = 0 AND COALESCE(grid.pop, 0) = 0)
                AND NOT ST_INTERSECTS(grid.geom, (SELECT ST_union(kt.geom) FROM kt));

            ALTER TABLE kt
                ALTER COLUMN k_ap_ala TYPE real,
                ALTER COLUMN k_ar_ala TYPE real,
                ALTER COLUMN k_ak_ala TYPE real,
                ALTER COLUMN k_muu_ala TYPE real,
                ALTER COLUMN k_tp_yht TYPE real,
                ALTER COLUMN k_poistuma TYPE real;

            UPDATE kt set 
                k_ap_ala = kt.k_ap_ala / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1),
                k_ar_ala = kt.k_ar_ala / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1),   
                k_ak_ala = kt.k_ak_ala / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1),
                k_muu_ala = kt.k_muu_ala / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1),
                k_tp_yht = kt.k_tp_yht / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1),
                k_poistuma = kt.k_poistuma / (COALESCE(kt.k_valmisv, targetYear) - COALESCE(kt.k_aloitusv, baseYear) + 1);

            WITH parts as (
                SELECT DISTINCT ON (grid.xyind) grid.xyind AS xyind,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_ap_ala) AS k_ap_ala,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_ar_ala) AS k_ar_ala,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_ak_ala) AS k_ak_ala,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_muu_ala) AS k_muu_ala,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_tp_yht) AS k_tp_yht,
                    SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) / kt.area * kt.k_poistuma) AS k_poistuma                    
                FROM grid, kt
                WHERE ST_INTERSECTS(grid.geom, kt.geom)
                GROUP by grid.xyind
            ) UPDATE grid SET
                k_ap_ala = parts.k_ap_ala, 
                k_ar_ala = parts.k_ar_ala,
                k_ak_ala = parts.k_ak_ala,
                k_muu_ala = parts.k_muu_ala,
                k_poistuma = CASE WHEN parts.k_poistuma < 0 THEN parts.k_poistuma * (-1) ELSE COALESCE(parts.k_poistuma) END,
                employ = COALESCE(grid.employ,0) + parts.k_tp_yht
                FROM parts
                    WHERE parts.xyind = grid.xyind;

        END IF;

        ELSIF completionYearExists AND typeExists AND NOT kapaExists THEN
        
        UPDATE grid
            SET k_ap_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.kem2 <= 0 OR kt.kem2 IS NULL THEN 0 ELSE kt.kem2 END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.type IN ('ao','ap')
                    AND kt.year_completion = calculationYear
            ), k_ar_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.kem2 <= 0 OR kt.kem2 IS NULL THEN 0 ELSE kt.kem2 END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.type IN ('ar','kr')
                    AND kt.year_completion = calculationYear
            ), k_ak_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.kem2 <= 0 OR kt.kem2 IS NULL THEN 0 ELSE kt.kem2 END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.type IN ('ak','c')
                    AND kt.year_completion = calculationYear
            ), k_muu_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.kem2 <= 0 OR kt.kem2 IS NULL THEN 0 ELSE kt.kem2 END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.type IN ('tp','muu')
                    AND kt.year_completion = calculationYear
            ), employ = COALESCE(grid.employ,0) + CASE WHEN ST_Intersects(grid.geom, (SELECT ST_UNION(kt.geom) FROM kt)) THEN (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area * COALESCE(kt.k_tp_yht,0)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ) ELSE 0 END;

            IF demolitionsExist THEN
                UPDATE grid SET k_poistuma = (
                    SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                        kt.area *
                        (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) WHEN kt.k_poistuma IS NULL THEN 0 ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
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
                    kt.area *
                    (CASE WHEN kt.k_ap_ala <= 0 OR kt.k_ap_ala IS NULL THEN 0 ELSE kt.k_ap_ala END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ), k_ar_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_ar_ala <= 0 OR kt.k_ar_ala IS NULL THEN 0 ELSE kt.k_ar_ala END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ), k_ak_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_ak_ala <= 0 OR kt.k_ak_ala IS NULL THEN 0 ELSE kt.k_ak_ala END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ), k_muu_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_muu_ala <= 0 OR kt.k_muu_ala IS NULL THEN 0 ELSE kt.k_muu_ala END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ), employ = COALESCE(grid.employ,0) + CASE WHEN ST_Intersects(grid.geom, (SELECT ST_UNION(kt.geom) FROM kt)) THEN (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area * 
                    (CASE WHEN kt.k_tp_yht <= 0 OR kt.k_tp_yht IS NULL THEN 0 ELSE kt.k_tp_yht END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND kt.year_completion = calculationYear
            ) ELSE 0 END;

            IF demolitionsExist THEN
                UPDATE grid SET k_poistuma = (
                    SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                        kt.area *
                        (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) WHEN kt.k_poistuma IS NULL THEN 0 ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
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
                    kt.area *
                    (CASE WHEN kt.k_ap_ala <= 0 OR kt.k_ap_ala IS NULL THEN 0 ELSE kt.k_ap_ala / (targetYear - baseYear + 1) END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND baseYear <= calculationYear
            ), k_ar_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_ar_ala <= 0 OR kt.k_ar_ala IS NULL THEN 0 ELSE kt.k_ar_ala / (targetYear - baseYear + 1) END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND baseYear <= calculationYear
            ), k_ak_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_ak_ala <= 0 OR kt.k_ak_ala IS NULL THEN 0 ELSE kt.k_ak_ala / (targetYear - baseYear + 1) END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND baseYear <= calculationYear
            ), k_muu_ala = (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (CASE WHEN kt.k_muu_ala <= 0 OR kt.k_muu_ala IS NULL THEN 0 ELSE kt.k_muu_ala / (targetYear - baseYear + 1) END)), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND baseYear <= calculationYear
            ), employ =COALESCE(grid.employ,0) + CASE WHEN ST_Intersects(grid.geom, (SELECT ST_UNION(kt.geom) FROM kt)) THEN (
                SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                    kt.area *
                    (COALESCE(kt.k_tp_yht,0) / (targetYear - baseYear + 1))), 0)
                FROM kt
                    WHERE ST_Intersects(grid.geom, kt.geom)
                    AND baseYear <= calculationYear
            ) ELSE 0 END;
                IF demolitionsExist THEN
                    UPDATE grid SET k_poistuma = (
                        SELECT COALESCE(SUM(ST_Area(ST_Intersection(grid.geom, kt.geom)) /
                            kt.area *
                            (CASE WHEN kt.k_poistuma < 0 THEN kt.k_poistuma / (targetYear - baseYear + 1) * (-1) WHEN kt.k_poistuma IS NULL THEN 0 ELSE kt.k_poistuma / (targetYear - baseYear + 1) END)), 0)
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

        IF (SELECT COALESCE(COUNT(*),0) FROM kt) > 0 THEN

        UPDATE grid
            SET maa_ha = 5.9
            WHERE grid.k_ak_ala >= 200;

        UPDATE grid
            SET alueteho = COALESCE(grid.alueteho,0) + (CASE WHEN
                grid.maa_ha > 0
                THEN
                (COALESCE(grid.k_ap_ala, 0) + COALESCE(grid.k_ar_ala, 0) + COALESCE(grid.k_ak_ala, 0) + COALESCE(grid.k_muu_ala, 0) - COALESCE(grid.k_poistuma, 0)) / (10000 * grid.maa_ha)
                ELSE 0 END);

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

        END IF;
        
        /* KESKUSVERKON PÄIVITTÄMINEN
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

        CREATE INDEX ON centralnetwork USING GIST (geom);

        /* Add new centers to the central network only if the user has added such! */
        IF plan_centers IS NOT NULL THEN
            INSERT INTO centralnetwork
            SELECT st_force2d((ST_DUMP(plan.geom)).geom) as geom,
				(SELECT MAX(k.id) FROM centralnetwork k) + row_number() over (order by plan.geom desc),
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

            /* Update closest distance to centroids into grid data. */
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
        END IF;

        /* YHDYSKUNTARAKENTEEN VYÖHYKKEIDEN PÄIVITTÄMINEN */
        -- Keskustan jalankulkuvyöhyke
        /** Tested OK */
        CREATE TEMP TABLE IF NOT EXISTS grid_new AS
        SELECT * FROM
        (
            SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
            CASE
                WHEN left(grid.zone::varchar, 6)::int IN (999112, 999212, 999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                    THEN concat('99911', right(grid.zone::varchar, 4))::bigint
                WHEN left(grid.zone::varchar, 6)::int IN (999122, 999222, 999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                    THEN concat('99912', right(grid.zone::varchar, 4))::bigint
                ELSE 1
            END AS zone
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

        ANALYZE grid_new;
        CREATE INDEX IF NOT EXISTS grid_new_xyind ON grid_new (xyind);    
        
        /* Olemassaolevien alakeskusten reunojen kasvatus */
        /** Tested OK */
        INSERT INTO grid_new (geom, xyind, zone)
        SELECT DISTINCT ON (grid.geom) grid.geom, grid.xyind,
        CASE
            WHEN grid.zone IN (3,4,5, 81, 82, 83 ,84 ,85 ,86 ,87) THEN 10
            WHEN LEFT(grid.zone::varchar, 6)::int 
                IN (999312, 999412, 999512, 999612, 999101, 999811, 999821, 999831, 999841, 999851, 999861, 999871)
                    THEN CONCAT('999101', RIGHT(grid.zone::varchar, 4))::bigint
            WHEN LEFT(grid.zone::varchar, 6)::int
                IN (999322, 999422, 999522, 999622, 999102, 999812, 999822, 999832, 999842, 999852, 999862, 999872)
                    THEN CONCAT('999102', RIGHT(grid.zone::varchar, 4))::bigint
            ELSE grid.zone
        END AS zone
        FROM grid
        JOIN centralnetwork ON (
            /* Search for grid cells within current UZ central areas delineation */
            grid.xyind NOT IN (SELECT grid_new.xyind FROM grid_new)
            /* Conditions for filtering */
            AND (
                (grid.zone IN (10,11,12,6,837101) 
                OR LEFT(grid.zone::varchar, 6)::int IN (999101, 999102, 999111, 999112, 999121, 999122, 999612, 999622))
                OR (
                    grid.maa_ha != 0
                    AND ST_DWithin(
                        grid.geom, 
                        (SELECT ST_Union(grid.geom) FROM grid WHERE (grid.zone IN (10, 11, 12, 6, 837101) 
                        OR LEFT(grid.zone::varchar, 6)::int IN (999101, 999102, 999111, 999112, 999121, 999122, 999612, 999622))), 25)
                    AND (grid.alueteho > 0.05 AND grid.employ > 0)
                    AND (grid.alueteho > 0.2 AND grid.pop >= 100 AND grid.employ > 0)
                )
            )
            /* Select only edge neighbours, no corner touchers */
            /* Buffer + area based intersection trick */
            AND ST_Area(
                ST_Intersection(
                    grid.geom,
                    ST_Buffer(
                        (SELECT ST_Union(grid.geom) FROM grid WHERE (grid.zone = 1) 
                        OR LEFT(grid.zone::varchar, 6)::int IN (999112, 999122)), 1)
                )
            ) > 1
            AND (0.014028 * grid.pop + 0.821276 * grid.employ - 3.67) > 10
        );
        
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
                AND pubtrans.k_jltyyp::varchar = '1'
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
                AND pubtrans.k_jltyyp::varchar = '2'
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
                AND pubtrans.k_jltyyp::varchar = '3'
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
                    CASE WHEN pubtrans.k_jltyyp::varchar = '1' THEN 1000
                        WHEN pubtrans.k_jltyyp::varchar = '2' THEN 800 
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