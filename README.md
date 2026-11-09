# Running the SUT (Synapse)
If you've installed and configured your container already, you can simply start it after stopping it. If not, refer to the README of the first assignment. Get all containers (running and stopped):
```bash
docker ps -a
# Copy the container id and run:
docker start 1fa59f56d69d
```

# Running the Plugin Adapter (Python)
To set up the to the plugin adapter, refer to its [README.md](smartdoor-adapter-python/README.md). To run it, run the convinient [adapter script](smartdoor-adapter-python/adapter). Or otherwise, start it with the following command:
```shell
cd smartdoor-adapter-python/
./.venv/bin/python3.12 src/adapter/plugin_adapter.py -n "Matrix-Plugin-Adapter" -u wss://course02.axini.com:443/adapters -t axini_cd6bee9ce8e267d59fec6f2ef791b6f1a1e6c747cb5ff65f393dc6d6e89e258ca752
```