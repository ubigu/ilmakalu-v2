/* Rakennusten jäähdytys | Cooling of buildings 

YKR-ruudun rakennusten jäähdytystarve jaahdytys_kwh [kWh/a] on:
    jaahdytys_kwh = rakennus_ala * jaahdytys_osuus * jaahdytys_kwhm2 * jaahdytys_muoto * jaahdytys_muutos

Rakennusten jäähdytykseen tarvitun ostoenergian kasvihuonekaasupäästöt [CO2/a] ovat:
    jaahdytys_co2 = jaahdytys_kwh * (jmuoto_apu1 * sahko_gco2kwh + jmuoto_apu2 * jaahdytys_gco2kwh)

*/

CREATE SCHEMA IF NOT EXISTS functions;
DROP FUNCTION IF EXISTS functions.CO2_PropertyCooling;
CREATE OR REPLACE FUNCTION
functions.CO2_PropertyCooling(
    calculationYear integer, -- [year based on which emission values are calculated, min, max calculation years]
    calculationScenario varchar, -- PEIKKO-kehitysskenaario | PEIKKO development scenario
    floorSpace integer, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta [m2]
    buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
    buildingYear integer -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
)
RETURNS real AS
$$
DECLARE
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
    
    /* Dummy-kertoimet jäähdytysmuodoille | Dummy multipliers by method of cooling */
    /* Jäähdytyksen ominaispäästökertoimet | Emission values for cooling */

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