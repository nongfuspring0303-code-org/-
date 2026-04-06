$ErrorActionPreference = "Stop"

$wsPort = if ($env:EDT_WS_PORT) { $env:EDT_WS_PORT } else { "18765" }
$apiPort = if ($env:EDT_API_PORT) { $env:EDT_API_PORT } else { "18787" }
$webPort = if ($env:EDT_WEB_PORT) { $env:EDT_WEB_PORT } else { "18080" }

python scripts/run_c_module_stack.py `
  --ws-port $wsPort `
  --api-port $apiPort `
  --web-port $webPort