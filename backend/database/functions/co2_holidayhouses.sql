-- FUNCTION: functions.co2_holidayhouses(integer, character varying, character varying, integer, character varying)

-- DROP FUNCTION IF EXISTS functions.co2_holidayhouses(integer, character varying, character varying, integer, character varying);

CREATE OR REPLACE FUNCTION functions.co2_holidayhouses(
	calculationyear integer,
	method character varying,
	electricitytype character varying,
	holidayhouses integer,
	calculationscenario character varying)
    RETURNS real
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    e_gco2kWh real;
    holidayhouses_emissions real;
BEGIN
    -- If holidayhouses is zero or NULL, return 0
    IF holidayhouses <= 0 OR holidayhouses IS NULL THEN
        RETURN 0;
    END IF;

    -- Fetch the e.gco2kWh value based on the calculationyear, method, and electricitytype
    EXECUTE FORMAT('
        SELECT e.gco2kWh
        FROM energy.electricity e
        WHERE e.year = %L AND e.metodi = %L AND e.paastolaji = %L AND e.scenario = %L
        LIMIT 1', 
        calculationyear, method, electricitytype, calculationscenario) INTO e_gco2kWh;

    -- Calculate holidayhouses emissions
    holidayhouses_emissions := ((holidayhouses * 4100) * e_gco2kWh) + (holidayhouses * 416.58 * 1000);

    -- Return the calculated emissions value
    RETURN holidayhouses_emissions;

END;
$BODY$;

ALTER FUNCTION functions.co2_holidayhouses(integer, character varying, character varying, integer, character varying)
    OWNER TO docker;
