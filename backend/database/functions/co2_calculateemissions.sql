-- FUNCTION: functions.co2_calculateemissions(integer[], regclass, integer, character varying, character varying, character varying, integer, integer, regclass, regclass, regclass, boolean, boolean)

-- DROP FUNCTION IF EXISTS functions.co2_calculateemissions(integer[], regclass, integer, character varying, character varying, character varying, integer, integer, regclass, regclass, regclass, boolean, boolean);

CREATE OR REPLACE FUNCTION functions.co2_calculateemissions(
	municipalities integer[],
	aoi regclass,
	calculationyear integer,
	calculationscenario character varying DEFAULT 'wemp'::character varying,
	baseyear integer DEFAULT NULL::integer,
	targetyear integer DEFAULT NULL::integer,
	plan_areas regclass DEFAULT NULL::regclass,
	plan_transit regclass DEFAULT NULL::regclass,
	plan_centers regclass DEFAULT NULL::regclass,
	includelongdistance boolean DEFAULT true,
	includebusinesstravel boolean DEFAULT true)
    RETURNS TABLE(geom geometry, xyind character varying, mun integer, zone bigint, year date, floorspace integer, pop smallint, employ smallint, tilat_vesi_tco2 real, tilat_lammitys_tco2 real, tilat_jaahdytys_tco2 real, sahko_kiinteistot_tco2 real, sahko_kotitaloudet_tco2 real, sahko_palv_tco2 real, sahko_tv_tco2 real, sahko_mokit_tco2 real, liikenne_as_tco2 real, liikenne_tp_tco2 real, liikenne_tv_tco2 real, liikenne_palv_tco2 real, rak_korjaussaneeraus_tco2 real, rak_purku_tco2 real, rak_uudis_tco2 real, sum_yhteensa_tco2 real, sum_lammonsaato_tco2 real, sum_liikenne_tco2 real, sum_sahko_tco2 real, sum_rakentaminen_tco2 real, sum_jatehuolto_tco2 real) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
    DECLARE
        loopYear integer;
        localbuildings boolean;
        refined boolean;
        grams_to_tons real default 0.000001; -- Muuntaa grammat tonneiksi (0.000001) [t/g].
    BEGIN

        /* Jos valitaan 'static'-skenaario, eli huomioidaan laskennassa vain yhdyskuntarakenteen muutos, asetetaan PEIKKO-skenaarioksi 'wemp'.
            Samalla sidotaan laskennan referenssivuodeksi laskennan aloitusyear.
            If the 'static' skenaario is selected, i.e. only changes in the urban structure are taken into account, set the PEIKKO skenaario to 'wemp'.
            At the same time, fix the calculation reference year into current year / baseYear */
        /* Kun käytetään static-skenaariota tulevaisuuslaskennassa, aseta laskenta lähtövuoden referenssitasolle */
        /* When using a 'static' scenario in the future scenario calculation, set the calculation reference year to baseYear */

        IF baseYear IS NULL THEN baseYear := calculationYear; END IF;

        loopYear := calculationYear;

        IF calculationScenario = 'static'
            THEN
                calculationScenario := 'wemp';
                calculationYear := baseYear;
        END IF;

        IF calculationYear < 2018 THEN calculationYear := 2018; END IF;
        IF calculationYear > 2050 THEN calculationYear := 2050; END IF;

        /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää energiamuototiedon */
        /* Checking, whether or not local building data with energy source information is present */
        SELECT EXISTS (
            SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'energiam'
                AND NOT attisdropped
        ) INTO localbuildings;

        /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää tarkemmat TOL-johdannaiset */
        /* Checking, whether or not local building data with detailed usage source information is present */
        SELECT EXISTS (
            SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'myymal_pien_ala'
                AND NOT attisdropped
        ) INTO refined;

        /* Numeeristetaan suunnitelma-aineistoa | 'Numerizing' the given plan data */
        DROP TABLE IF EXISTS grid_temp;
        CREATE TEMP TABLE grid_temp AS
            SELECT * FROM functions.CO2_GridProcessing(municipalities, aoi, loopYear, baseYear, targetYear, plan_areas, plan_transit, plan_centers, 1.25::real);
        DROP TABLE IF EXISTS grid;
        ALTER TABLE grid_temp RENAME TO grid;

        --------------------------------------------------------

        IF targetYear IS NOT NULL THEN

            /* Luodaan pohja-aineisto rakennusdatan työstölle */
            /* Building a template for manipulating building data */
            /* Ensimmäisenä laskentavuotena otetaan pohjat YKR-rakennuksista */
            /* Filter out years = 0 / 0000 = total sum rows */
            IF loopYear = baseYear
                THEN
                    EXECUTE format(
                        'CREATE TEMP TABLE IF NOT EXISTS rak_initial AS
                            SELECT * FROM grid_globals.buildings
                            WHERE rakv::int != 0
                                AND xyind::varchar IN
                                    (SELECT grid.xyind::varchar FROM grid)
                                AND rakv::int <= %L',
                    loopYear);
                    /* Seuraavina vuosina otetaan pohjat loopatusta rakennusdatasta */
                ELSE 
                    ALTER TABLE grid2 RENAME to rak_initial;
            END IF;

            ANALYZE rak_initial;
            DROP INDEX IF EXISTS rak_initial_index;
            CREATE INDEX IF NOT EXISTS rak_initial_index ON rak_initial (xyind, rakv, energiam);

            /* Luodaan väliaikainen taulu rakennusten purkamisen päästölaskentaa varten
            Creating a temporary table for emission calculations of demolishing buildings
            Default demolishing rate: 0.15% annually of existing building stock.
            Huuhka, S. & Lahdensivu J. Statistical and geographical study on demolish buildings. Building research and information vol 44:1, 73-96. */

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

            /* Kyselyt: Puretaan rakennukset datasta ja rakennetaan uusia */
            /* Valitaan ajettava kysely sen perusteella, millaista rakennusdataa on käytössä */
            /* Queries: Demolishing and buildings buildings from the building data */
            /* Choose correct query depending on the type of building data in use */

            IF localbuildings = true THEN
                IF refined = true THEN 
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, myymal_pien_ala :: int, myymal_super_ala :: int, myymal_hyper_ala :: int, myymal_muu_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, teoll_elint_ala :: int, teoll_tekst_ala :: int, teoll_puu_ala :: int, teoll_paper_ala :: int, teoll_miner_ala :: int, teoll_kemia_ala :: int, teoll_kone_ala :: int, teoll_mjalos_ala :: int, teoll_metal_ala :: int, teoll_vesi_ala :: int, teoll_energ_ala :: int, teoll_yhdysk_ala :: int, teoll_kaivos_ala :: int, teoll_muu_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM functions.CO2_UpdateBuildingsRefined(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYear, baseYear, targetYear, calculationScenario);
                ELSE 
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM functions.CO2_UpdateBuildingsLocal(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYear, baseYear, targetYear, calculationScenario);
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
            g.geom::geometry(Polygon, 3067),
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
            0::real sahko_mokit_tco2,
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
            0::real sum_rakentaminen_tco2,
            0::real sum_jatehuolto_tco2
        FROM grid g
            WHERE (COALESCE(g.pop,0) > 0 OR COALESCE(g.employ,0) > 0 )
                OR g.xyind::varchar IN (SELECT DISTINCT ON (grid2.xyind) grid2.xyind::varchar FROM grid2);

        ANALYZE results;
        CREATE INDEX IF NOT EXISTS results_xyind_index ON results (xyind);

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
                SUM((SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, liike_ala, 'liike', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv, g2.energiam)))
                AS property_water_gco2,
                /* Rakennusten lämmitys | Heating of buildings */
                SUM((SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, liike_ala, 'liike', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv, g2.energiam)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv, g2.energiam)))
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
                SUM((SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, liike_ala, 'liike', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT functions.CO2_PropertyWater(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv)))
                AS property_water_gco2,
                /* Rakennusten lämmitys | Heating of buildings */
                SUM((SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, liike_ala, 'liike', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT functions.CO2_PropertyHeat(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv)))
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
            SUM((SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, liike_ala, 'liike', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                (SELECT functions.CO2_PropertyCooling(calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv)))
            AS property_cooling_gco2,
            /* Kiinteistösähkö | Electricity consumption of property technology */
            SUM((SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, liike_ala,  'liike', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                (SELECT functions.CO2_ElectricityProperty(calculationYear, calculationScenario, muut_ala, 'muut', g2.rakv)))
            AS sahko_kiinteistot_co2,
            /* Kotitalouksien sähkönkulutus | Energy consumption of households */
            SUM((SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYear, calculationScenario, erpien_ala, 'erpien')) +
                (SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYear, calculationScenario, rivita_ala, 'rivita')) +
                (SELECT functions.CO2_ElectricityHousehold(g2.mun, calculationYear, calculationScenario, askert_ala, 'askert')))
            AS sahko_kotitaloudet_co2,
            /* Korjausrakentaminen ja saneeraus | Renovations and large-scale overhauls of buildings */
            SUM((SELECT functions.CO2_BuildRenovate(erpien_ala, calculationYear, 'erpien', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(rivita_ala, calculationYear, 'rivita', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(askert_ala, calculationYear, 'askert', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(liike_ala, calculationYear, 'liike', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(tsto_ala, calculationYear, 'tsto', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(liiken_ala, calculationYear, 'liiken', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(hoito_ala, calculationYear, 'hoito', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(kokoon_ala, calculationYear, 'kokoon', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(opetus_ala, calculationYear, 'opetus', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(teoll_ala, calculationYear, 'teoll', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(varast_ala, calculationYear, 'varast', g2.rakv, calculationScenario)) +
                (SELECT functions.CO2_BuildRenovate(muut_ala, calculationYear, 'muut', g2.rakv, calculationScenario)))
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
                SUM((SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, liike_ala, 'liike')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon')) +	
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus')))
                AS sahko_palv_co2,
                /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                SUM((SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast')))
                AS sahko_tv_co2,
                /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_ala, 'teoll')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast')))
                AS liikenne_tv_co2,
                /* Palveluliikenne | Service traffic */
                SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, myymal_ala, 'myymal')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, asla_ala, 'asla')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, ravint_ala, 'ravint')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut')))
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
                SUM((SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, myymal_super_ala, 'myymal_super')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, majoit_ala, 'majoit')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, asla_ala, 'asla')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, ravint_ala, 'ravint')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon')) +	
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus')))
                AS sahko_palv_co2,
                /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                SUM((SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                    (SELECT functions.CO2_ElectricityIWHS(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast')))
                AS sahko_tv_co2,
                /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, varast_ala, 'varast')))
                AS liikenne_tv_co2,
                /* Palveluliikenne | Service traffic */
                SUM((SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, myymal_super_ala, 'myymal_super')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, majoit_ala, 'majoit')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, asla_ala, 'asla')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, ravint_ala, 'ravint')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, tsto_ala, 'tsto')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, liiken_ala, 'liiken')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, hoito_ala, 'hoito')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, kokoon_ala, 'kokoon')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, opetus_ala, 'opetus')) +
                    (SELECT functions.CO2_TrafficIWHS(g2.mun, calculationYear, calculationScenario, muut_ala, 'muut')))
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
                SUM((SELECT functions.CO2_BuildConstruct(erpien_ala, calculationYear, 'erpien', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(rivita_ala, calculationYear, 'rivita', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(askert_ala, calculationYear, 'askert', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(liike_ala, calculationYear, 'liike', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(tsto_ala, calculationYear, 'tsto', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(liiken_ala, calculationYear, 'liiken', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(hoito_ala, calculationYear, 'hoito', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(kokoon_ala, calculationYear, 'kokoon', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(opetus_ala, calculationYear, 'opetus', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(teoll_ala, calculationYear, 'teoll', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(varast_ala, calculationYear, 'varast', calculationScenario)) +
                    (SELECT functions.CO2_BuildConstruct(muut_ala, calculationYear, 'muut', calculationScenario))
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
                    SUM((SELECT functions.CO2_BuildDemolish(p.erpien::real, calculationYear, 'erpien', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.rivita::real, calculationYear, 'rivita', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.askert::real, calculationYear, 'askert', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.liike::real, calculationYear, 'liike', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.tsto::real, calculationYear, 'tsto', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.liiken::real, calculationYear, 'liiken', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.hoito::real, calculationYear, 'hoito', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.kokoon::real, calculationYear, 'kokoon', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.opetus::real, calculationYear, 'opetus', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.teoll::real, calculationYear, 'teoll', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.varast::real, calculationYear, 'varast', calculationScenario)) +
                        (SELECT functions.CO2_BuildDemolish(p.muut::real, calculationYear, 'muut', calculationScenario))
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
                SUM((SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYear, 'bussi', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYear, 'raide', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYear, 'hlauto', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.pop, calculationYear, 'muu', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)))
                AS liikenne_as_co2,
                SUM((SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYear, 'bussi', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYear, 'raide', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYear, 'hlauto', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                    (SELECT functions.CO2_TrafficPersonal(g.mun, g.employ, calculationYear, 'muu', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)))
                AS liikenne_tp_co2,
                SUM((SELECT functions.CO2_ElectricityHousehold(g.mun, calculationYear, calculationScenario, g.pop, NULL)))
                AS sahko_kotitaloudet_co2_as
                FROM grid g
                    WHERE (g.pop IS NOT NULL AND g.pop > 0)
                    OR (g.employ IS NOT NULL AND g.employ > 0)
            GROUP BY g.xyind) pop
        WHERE pop.xyind = results.xyind;

        /* Jätehuollon asukaskohtaisten päästöjen ennustemalli */
        UPDATE results SET
            sum_jatehuolto_tco2 = COALESCE(pop.waste_emissions_per_person_sum, 0)
        FROM
            (SELECT g.xyind,
                ((EXP(79.702742 - 0.040097 * calculationYear)) * g.pop) as waste_emissions_per_person_sum
            FROM grid g
                WHERE (g.pop IS NOT NULL AND g.pop > 0)
            GROUP BY g.xyind, g.pop) pop
        WHERE pop.xyind = results.xyind;
		
		 /*mökkien päästöt*/
        UPDATE results SET
            sahko_mokit_tco2 = COALESCE(hh.holidayhouses_emissions_sum * grams_to_tons, 0)
        FROM (SELECT g.xyind,
            functions.co2_holidayhouses(calculationyear, g.holidayhouses, calculationscenario) AS holidayhouses_emissions_sum
            FROM grid g
                WHERE g.holidayhouses IS NOT NULL AND g.holidayhouses > 0
        GROUP BY g.xyind, g.holidayhouses) hh
        WHERE hh.xyind = results.xyind;

        /* Add categorical total sums to results */
        UPDATE results r SET
            year = to_date(loopYear::varchar, 'YYYY'),
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
                COALESCE(r.sahko_tv_tco2, 0) +
                COALESCE(r.sahko_mokit_tco2, 0),
            sum_rakentaminen_tco2 =
                COALESCE(r.rak_korjaussaneeraus_tco2, 0) +
                COALESCE(r.rak_purku_tco2, 0) +
                COALESCE(r.rak_uudis_tco2, 0);

        /* Add total emission sum to results */
        UPDATE results r SET
            sum_yhteensa_tco2 =
                COALESCE(r.sum_lammonsaato_tco2, 0) +
                COALESCE(r.sum_liikenne_tco2, 0) +
                COALESCE(r.sum_sahko_tco2, 0) +
                COALESCE(r.sum_rakentaminen_tco2, 0) +
                COALESCE(r.sum_jatehuolto_tco2, 0);

        /* Lisätään päivitetyt kerrosneliömetrisummat kokonaiskerrosneliömäärään */
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

        /* Remove temporary grids at the end of calculation */
        IF targetYear IS NULL OR targetYear = calculationYear THEN
            DROP TABLE grid, grid2;
        END IF;

        RETURN QUERY SELECT * FROM results;
        DROP TABLE results;

    END;
    
$BODY$;

-- ALTER FUNCTION functions.co2_calculateemissions(integer[], regclass, integer, character varying, character varying, character varying, integer, integer, regclass, regclass, regclass, boolean, boolean)
--    OWNER TO docker;