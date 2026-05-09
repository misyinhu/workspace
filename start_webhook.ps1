$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
$p = Start-Process -FilePath "C:\Users\wang\AppData\Local\Programs\Python\Python312\python.exe" -ArgumentList "C:\projects\trading\notify\webhook_bridge.py" -WorkingDirectory "C:\projects\trading\notify" -WindowStyle Hidden -PassThru -EnvironmentVariables
Start-Sleep 3
if ($p.HasExited) {
    Write-Host "Failed to start, exit code:" $p.ExitCode
} else {
    Write-Host "Started successfully, PID:" $p.Id
}
