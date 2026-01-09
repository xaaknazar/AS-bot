# SCHEDULER-SYNC-PRO
## Application for automating the processes of collecting and sending data from OPC UA, PLC and TCP Modbus sensors

### Docker Build
To build the Docker image for SCHEDULER-SYNC-PRO, run the following command:
```bash
docker build -t scheduler-sync-pro .
```

### Docker Run
To run the SCHEDULER-SYNC-PRO application, use the following command:
```bash
docker run --env-file .env --name scheduler-sync-pro -p 8082:8000 --restart always -d scheduler-sync-pro
```

Follow these steps in order to successfully set up and initialize the SCHEDULER-SYNC-PRO app, 
and access the Swagger UI for the application API at ```localhost:8082/docs```