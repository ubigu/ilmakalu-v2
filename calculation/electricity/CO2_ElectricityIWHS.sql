/* Sähkön käyttö, teollisuus, varastot ja palvelut | Electricity consumption, industry, warehouses and services

Palvelusektorin sekä teollisuuden ja varastojen sähkön käyttö muuhun kuin rakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin sahko_palv_kwh [kWh/a] perustuu kaavaan

    sahko_ptv_kwh  = rakennus_ala * sahko_ptv_kwhm2

Palvelusektorin sekä teollisuuden ja varastojen muuhun lämmitykseen ja kiinteistöshköön käytetyn sähkön kasvihuonekaasupäästöt sahko_palv_co2 [CO2-ekv/a] ovat 

    sahko_ptv_co2 = sahko_ptv_kwh  * sahko_gco2kwh

Teollisuus- ja varastorakennusten sähkön käyttö sisältää myös niiden kiinteistösähkön kulutuksen.

*/

DROP FUNCTION IF EXISTS public.CO2_ElectricityIWHS;
CREATE OR REPLACE FUNCTION
public.CO2_ElectricityIWHS(
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