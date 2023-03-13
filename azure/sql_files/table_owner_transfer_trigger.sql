BEGIN;

CREATE OR REPLACE FUNCTION trigger_create_set_table_owner()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER -- run as function owner which is superuser
 SET search_path = admin, pg_temp -- make sure that pg_temp is not utilized
AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() WHERE command_tag='CREATE TABLE' LOOP
    EXECUTE format('ALTER TABLE %s OWNER TO end_users', obj.object_identity);
  END LOOP;
  FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() WHERE command_tag='CREATE SEQUENCE' LOOP
    EXECUTE format('ALTER SEQUENCE %s OWNER TO end_users', obj.object_identity);
  END LOOP;
  FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() WHERE command_tag='CREATE FUNCTION' LOOP
    EXECUTE format('ALTER FUNCTION %s OWNER TO end_users', obj.object_identity);
  END LOOP;
END;
$$;

DROP EVENT TRIGGER IF EXISTS trigger_create_set_table_owner CASCADE;
CREATE EVENT TRIGGER trigger_create_set_table_owner
    ON DDL_COMMAND_END
    WHEN TAG IN ('CREATE TABLE', 'CREATE SEQUENCE', 'CREATE FUNCTION')
    EXECUTE PROCEDURE trigger_create_set_table_owner();

REVOKE ALL ON FUNCTION trigger_create_set_table_owner() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION trigger_create_set_table_owner() TO "end_users";
COMMIT;