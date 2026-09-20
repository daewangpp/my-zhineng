# CodeTutor 守护进程:每分钟巡检,保证链接持续在线
# - Flask 挂了 → 自动拉起
# - cloudflared 挂了 → 自动重连;若域名变化 → 自动同步到申报书/README/二维码/提交包
# 用法: powershell -ExecutionPolicy Bypass -File watchdog.ps1   (已注册开机自启)

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = "$env:TEMP\cloudflared.log"
$stateFile = "$root\reports\current_url.txt"

function Get-TunnelUrl {
    $c = Get-Content $log -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match($c, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($m.Success) { return $m.Value }
    return $null
}

function Start-Flask {
    Start-Process -FilePath "py" -ArgumentList "web_app.py" -WorkingDirectory $root -WindowStyle Hidden
}

function Start-Tunnel {
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath "$root\cloudflared.exe" -ArgumentList "tunnel", "--url", "http://127.0.0.1:5050" -RedirectStandardError $log -WindowStyle Hidden
}

while ($true) {
    # 1. 检查 Flask
    $listen = Get-NetTCPConnection -LocalPort 5050 -State Listen
    if (-not $listen) {
        Start-Flask
        Start-Sleep -Seconds 5
    }

    # 2. 检查隧道进程
    if (-not (Get-Process cloudflared -ErrorAction SilentlyContinue)) {
        Start-Tunnel
        Start-Sleep -Seconds 20
    }

    # 3. 域名变化检测 → 自动同步材料
    $current = Get-TunnelUrl
    $recorded = Get-Content $stateFile -ErrorAction SilentlyContinue
    if ($current -and ($current -ne $recorded)) {
        Set-Location $root
        py scripts\sync_link.py $current
    }

    Start-Sleep -Seconds 60
}
