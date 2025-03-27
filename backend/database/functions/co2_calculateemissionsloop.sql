CREATE SCHEMA IF NOT EXISTS functions;

DROP FUNCTION IF EXISTS functions.CO2_CalculateEmissionsLoop;
CREATE OR REPLACE FUNCTION
functions.CO2_CalculateEmissionsLoop(
    municipalities integer[],
    aoi regclass, -- Tutkimusalue | area of interest
    calculationScenario varchar, -- PEIKKO:n mukainen scenario
    baseYear integer, -- Laskennan lähtövuosi
    targetYear integer, -- Laskennan tavoitevuosi
    plan_areas regclass default null, -- Taulu, jossa käyttötarkoitusalueet tai vastaavat
    plan_transit regclass default null, -- Taulu, jossa intensiivinen joukkoliikennejärjestelmä,
    plan_centers regclass default null, -- Taulu, jossa keskusverkkotiedot 
    includeLongDistance boolean default true,
    includeBusinessTravel boolean default true
)
RETURNS TABLE(
    geom geometry(Polygon, 3067),
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
    sahko_mokit_tco2 real,
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
    sum_rakentaminen_tco2 real,
    sum_jatehuolto_tco2 real
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
                    municipalities, aoi, calculationYear, calculationScenario, baseYear, targetYear, plan_areas, plan_transit, plan_centers, includeLongDistance, includeBusinessTravel
                );
        ELSE 
            INSERT INTO res
            SELECT * FROM
                functions.CO2_CalculateEmissions(
                    municipalities, aoi, calculationYear, calculationScenario, baseYear, targetYear, plan_areas, plan_transit, plan_centers, includeLongDistance, includeBusinessTravel
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