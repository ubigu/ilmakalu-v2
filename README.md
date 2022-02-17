# Get energy mode distribution by mode of transport and municipality

This project utilizes traficom pxAPI and the following statistics:
- [Passenger cars in traffic on 31 June 2021 by area](https://trafi2.stat.fi/PXWeb/pxweb/en/TraFi/TraFi__Liikennekaytossa_olevat_ajoneuvot/010_kanta_tau_101.px/)
- [Vehicles in traffic by quarter in 2008 to 2021](https://trafi2.stat.fi/PXWeb/pxweb/en/TraFi/TraFi__Liikennekaytossa_olevat_ajoneuvot/040_kanta_tau_104.px/)

User can give needed municipality code according to which energy mode distributions by mode of transport and municipality are saved to postgres database. 
Create a config.yaml file as adviced in the template to point to wanted database. 