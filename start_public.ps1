# CodeTutor 一键启动:本地服务 + 公网隧道 + 自动同步链接到所有材料
# 用法:右键 → 使用 PowerShell 运行;或 powershell -ExecutionPolicy Bypass -File start_public.ps1

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# 1. 启动 Flask(若未运行)
$listen = Get-NetTCPConnection -LocalPort 5050 -State Listen
if (-not $listen) {
    Start-Process -FilePath "py" -ArgumentList "web_app.py" -WorkingDirectory $root -WindowStyle Hidden
    Write-Host "[1/3] Flask starting..."
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $tcp = New-Object Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", 5050); $tcp.Close(); break
        } catch {}
    }
} else {
    Write-Host "[1/3] Flask already running"
}

# 2. 启动 Cloudflare 隧道(若未运行)
$log = "$env:TEMP\cloudflared.log"
if (-not (Get-Process cloudflared -ErrorAction SilentlyContinue)) {
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath "$root\cloudflared.exe" -ArgumentList "tunnel", "--url", "http://127.0.0.1:5050" -RedirectStandardError $log -WindowStyle Hidden
    Write-Host "[2/3] Tunnel starting..."
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        $c = Get-Content $log -Raw -ErrorAction SilentlyContinue
        if ($c -match "https://[a-z0-9-]+\.trycloudflare\.com") { break }
    }
} else {
    Write-Host "[2/3] Tunnel already running"
}

# 3. 抓取域名并自动同步到申报书/README/二维码/提交包
$c = Get-Content $log -Raw -ErrorAction SilentlyContinue
$m = [regex]::Match($c, "https://[a-z0-9-]+\.trycloudflare\.com")
Write-Host ""
Write-Host "=============================================="
Write-Host "  Local:  http://127.0.0.1:5050"
if ($m.Success) {
    Write-Host "  Public: $($m.Value)"
    Write-Host "  Demo:   $($m.Value)/?demo=0"
    Write-Host "=============================================="
    Write-Host "[3/3] Syncing new URL to all materials..."
    py scripts\sync_link.py $m.Value
} else {
    Write-Host "  Failed to get public URL, see $log"
    Write-Host "=============================================="
}
Write-Host ""
Write-Host "Note: closing this window is OK. After reboot, run this script again;"
Write-Host "a NEW domain will be assigned and auto-synced to all materials."
