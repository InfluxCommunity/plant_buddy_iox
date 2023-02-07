import influxdb_client
import pandas as pd
from pandas.core.frame import DataFrame
from flightsql import FlightSQLClient
import pyarrow

class influxHelper:
    def __init__(self, org, bucket, token, host="https://us-east-1-1.aws.cloud2.influxdata.com") -> None:
        self.client = influxdb_client.InfluxDBClient(
            url = host,
            token = token,
            org = org,
            timeout = 30000
    )
        
        host = host.split("://")[1]
        self.flight_client = FlightSQLClient(host=host,
                         token=token,
                         metadata= {'bucket-name': bucket}
                         )

    
        self.cloud_bucket = bucket
        self.cloud_org = org
        # Ref to serial sensor samples. 
        self.sensor_names = {"LI":"light", "HU":"humidity", "ST":"soil_temperature",
                "AT":"air_temperature", "SM":"soil_moisture"}

        self.write_api = self.client.write_api()
        self.query_api = self.client.query_api()


    # The write to influx function formats the data point then writes to the database
    def write_to_influx(self,data):
        p = (influxdb_client.Point("sensor_data")
                            .tag("user",data["user"])
                            .tag("device_id",data["device"])
                            .field(data["sensor_name"], int(data["value"])
                            ))
        self.write_api.write(bucket=self.cloud_bucket, org=self.cloud_org, record=p)
        print(p, flush=True)
        
    # The parse line function formats the data object
    def parse_line(self, line, user_name):
        data = {"device" : line[:2],
                "sensor_name" : self.sensor_names.get(line[2:4], "unkown"),
                "value" : line[4:],
                "user": user_name}
        return data

 

    # Wrapper function used to query InfluxDB> Calls Flux script with paramaters. Data query to data frame.
    def querydata(self, sensor_name, deviceID) -> DataFrame:       
 
        query = self.flight_client.execute(f"SELECT {sensor_name}, time FROM sensor_data WHERE time > (NOW() - INTERVAL '2 HOURS') AND device_id='{deviceID}'")
        
        # Create reader to consume result
        reader = self.flight_client.do_get(query.endpoints[0].ticket)

        # Read all data into a pyarrow.Table
        Table = reader.read_all()
        print(Table)

        # Convert to Pandas DataFrame
        df = Table.to_pandas()
        df = df.sort_values(by="time")
        print(df)
        return df
    
