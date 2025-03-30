This is a subway arrivals board which can display up to two stations.

### Hardware
- [Adafruit MatrixPortal S3](https://www.adafruit.com/product/5778) - $20
- 2x [Adafruit 64x32 RGB LED Matrix - 2.5mm](https://www.adafruit.com/product/5036) - $40 ea
- Custom 3D printed case (will be uploaded to Printables)

### Instructions
1. Add your Wi-Fi SSID and password to `settings.toml`.
2. Edit `config.py` and add the URL to your subway line. You can find a list of all GTFS-realtime feeds at [Subway Realtime Feeds](https://api.mta.info/#/subwayRealTimeFeeds).
3. Also add the Stop IDs for your desired station in `config.py`. Northbound and Southbound will have different Stop IDs. There isn't a great resource for these, but if you Google you should be able to find them.
4. Copy files to the MatrixPortal S3's storage by connecting it to your computer over USB.

### Resources
- [GTFS-realtime Reference for the New York City Subway](https://www.mta.info/document/134521)
- [MTA Subway Stations and Complexes](https://data.ny.gov/w/5f5g-n3cz/caer-yrtv?cur=YKNbfco1WDe)
