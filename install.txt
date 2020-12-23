sudo pip3 install mysql-connector-java

sudo cp PycharmProjects/cp630-daemons/relay_watcher.py /usr/bin
sudo cp PycharmProjects/cp630-daemons/sensor_reader.py /usr/bin

sudo cp PycharmProjects/cp630-daemons/relay-watcher.service /usr/lib/systemd/system
sudo cp PycharmProjects/cp630-daemons/sensor-reader.service /usr/lib/systemd/system

sudo systemctl daemon-reload

sudo systemctl enable relay-watcher.service
sudo systemctl enable sensor-reader.service

sudo systemctl start relay-watcher.service
sudo systemctl start sensor-reader.service