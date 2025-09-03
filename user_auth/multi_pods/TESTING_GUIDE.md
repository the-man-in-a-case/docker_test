kubectl port-forward manager-deployment-7dbc6d7765-ftqkr 28080:8080

curl.exe -X POST -H "Authorization: Bearer default-token" http://localhost:28080/trigger-update