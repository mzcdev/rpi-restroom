# rpi-restroom

## raspberry pi config

```bash
sudo raspi-config
```

```
Interfacing Options -> SPI -> Enabled
```

## Install Python Software

```bash
pip3 install awscli
pip3 install boto3
```

## run

```bash
./run.sh
```

## crontab

```bash
0,12,24,36,48 * * * * /home/pi/rpi-restroom/run.sh > /tmp/rpi-restroom.log 2>&1
```
