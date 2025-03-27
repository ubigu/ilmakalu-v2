/* Sähkön käyttö, teollisuus, varastot ja palvelut | Electricity consumption, industry, warehouses and services

Palvelusektorin sekä teollisuuden ja varastojen sähkön käyttö ja päästöt muuhun kuin rakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin perustuu kaavoihin
    sähkön käyttö kWh/a = kerrosala * [kWh/m2/a] 
    sähkön käytön päästöt gco2e/a = sähkön käyttö kWh/a * sähkön ominaispäästöt gco2/kWh
Teollisuus- ja varastorakennusten sähkön käyttö sisältää myös niiden kiinteistösähkön kulutuksen.
*/

CREATE SCHEMA IF NOT EXISTS functions;
DROP FUNCTION IF EXISTS functions.CO2_ElectricityIWHS;
CREATE OR REPLACE FUNCTION
functions.CO2_ElectricityIWHS(
    calculationYear integer, -- [year based on which emission values are calculated, min, max calculation years]
    calculationScenario varchar, -- PEIKKO-kehitysskenaario | PEIKKO development scenario
    floorSpace real, -- rakennustyypin kerrosala YKR-ruudussa laskentavuonna [m2]. Riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta.
    buildingType varchar -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
)
RETURNS real AS
$$
DECLARE
    services varchar[] default ARRAY['myymal_hyper', 'myymal_super', 'myymal_pien', 'myymal_muu', 'myymal', 'majoit', 'asla', 'ravint', 'tsto', 'liiken', 'hoito', 'kokoon', 'opetus', 'muut'];
    result_gco2 real;
BEGIN

    IF floorSpace <= 0
        OR floorSpace IS NULL THEN
        RETURN 0;
    ELSE

        /* Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh] * 
        Rakennustyypissä tapahtuvan toiminnan sähköintensiteetti kerrosneliömetriä kohti [kWh/m2] * kerrosala */
        EXECUTE FORMAT('
            WITH electricity_gco2kwh AS 
                (SELECT el.gco2kwh::real AS gco2 
                    FROM energy.electricity el
                        WHERE el.year = %3$L 
                        AND el.scenario = %2$L
                        LIMIT 1
                )
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