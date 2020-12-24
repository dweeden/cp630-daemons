import signal
import sys
import time
from datetime import datetime

import adafruit_dht
import board
import mysql.connector

POLLING_INTERVAL_SECONDS = 15
RETRY_INTERVAL = 0.1
DATABASE_HOST = "localhost"
DATABASE_NAME = "worker"
DATABASE_USER = "cp630"
DATABASE_PASSWORD = "cp630"
SENSOR_READING_INSERT_COMMAND = "insert into sensor_reading (temp, humidity) VALUES (%s, %s)"


def signal_handler(sig, frame):
    print('Script terminating')
    sys.exit(0)


# register for clean exit
signal.signal(signal.SIGINT, signal_handler)

# initialize sensor (pulseio not applicable for pin 2)
sensor = adafruit_dht.DHT22(board.D2)

cursor = None
connection = None
try:

    # connect to database
    connection = mysql.connector.connect(host=DATABASE_HOST, database=DATABASE_NAME, user=DATABASE_USER,
                                         password=DATABASE_PASSWORD, auth_plugin='mysql_native_password')

    if connection.is_connected():
        print("Connected to worker database")

        # open cursor
        cursor = connection.cursor()

        # main sensor reading loop
        print("Starting main sensor reading loop")
        while True:

            try:

                # cache readings and ensure they're valid
                t = sensor.temperature
                h = sensor.humidity
                if t is None or h is None:
                    # print("Invalid sensor data")
                    time.sleep(RETRY_INTERVAL)
                    continue

                # data is valid -> persist
                # print(f"Temp: {t} C, Humidity: {h}%")
                cursor.execute(SENSOR_READING_INSERT_COMMAND, (t, h))
                connection.commit()

            except Exception as error:
                # DHT sensors are not that robust
                # print("Exception: " + error.args[0])
                time.sleep(RETRY_INTERVAL)
                continue

            # sleep
            time.sleep(POLLING_INTERVAL_SECONDS)

    else:
        print("Couldn't connect to to worker database")

finally:
    # cleanup
    print("Cleaning up")
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()
    sensor.exit()

print("Script has completed")
