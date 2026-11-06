# DevBrief one-time setup, step 2 of 2: Redis + the GitHub App.
# Run from the repo root after setup.ps1:
#   .\setup-github-app.ps1
#
# What it does:
#   1. Makes sure Redis is running (the job queue between GitHub and the reviewer).
#   2. Creates a GitHub App for you. You only click two buttons in your browser.
#      Probot's built-in wizard sends GitHub the app settings from
#      apps\github-app\app.yml, so nothing has to be typed by hand.
#   3. Copies the app's credentials into .env and apps\web\.env.local.
# Safe to re-run: it skips steps that are already done.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$githubAppDir = Join-Path $root "apps\github-app"
$githubAppEnv = Join-Path $githubAppDir ".env"
$rootEnv = Join-Path $root ".env"
$wizardPort = 3002

function Read-EnvFile($path) {
    $values = @{}
    if (Test-Path $path) {
        foreach ($line in [IO.File]::ReadAllLines($path)) {
            if ($line -match '^\s*([A-Z0-9_]+)\s*=(.*)$') { $values[$Matches[1]] = $Matches[2].Trim() }
        }
    }
    return $values
}

function Test-Port($port) {
    # Servers may listen on IPv4 (127.0.0.1) or IPv6 (::1) only, so try both.
    foreach ($addr in @("127.0.0.1", "::1")) {
        try {
            $family = if ($addr -eq "::1") { [System.Net.Sockets.AddressFamily]::InterNetworkV6 } else { [System.Net.Sockets.AddressFamily]::InterNetwork }
            $client = New-Object System.Net.Sockets.TcpClient($family)
            $task = $client.ConnectAsync([System.Net.IPAddress]::Parse($addr), $port)
            $ok = $task.Wait(1500) -and $client.Connected
            $client.Close()
            if ($ok) { return $true }
        } catch { }
    }
    return $false
}

if (-not (Test-Path $rootEnv) -or -not (Read-EnvFile $rootEnv)["DATABASE_URL"]) {
    Write-Host "Run step 1 first:  .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "DevBrief setup (step 2 of 2)" -ForegroundColor Green

# ---- 1. Redis ---------------------------------------------------------------
$redisUrl = (Read-EnvFile $rootEnv)["REDIS_URL"]
$localRedis = (-not $redisUrl) -or ($redisUrl -match '://(localhost|127\.0\.0\.1)')
if ($localRedis) {
    if (Test-Port 6379) {
        Write-Host "[1/3] Redis is already running." -ForegroundColor Green
    } else {
        Write-Host "[1/3] Starting Redis with Docker..." -ForegroundColor Green
        $dockerOk = $false
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
        if (-not $dockerOk) {
            $desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if (Test-Path $desktop) {
                Write-Host "      Docker Desktop is not running. Starting it (this can take a minute or two)..."
                Start-Process $desktop
                for ($i = 0; $i -lt 90 -and -not $dockerOk; $i++) {
                    Start-Sleep 2
                    & docker info *> $null
                    if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
                }
            }
        }
        if (-not $dockerOk) {
            Write-Host ""
            Write-Host "Could not start Docker. Pick one:" -ForegroundColor Yellow
            Write-Host "  A) Open Docker Desktop yourself, wait until it says 'running', then run this script again."
            Write-Host "  B) Use a free cloud Redis: create a database at https://upstash.com, copy its"
            Write-Host "     'rediss://...' URL into REDIS_URL in .env, then run this script again."
            exit 1
        }
        Push-Location $root
        try { & docker compose up -d redis } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw "docker compose failed." }
        for ($i = 0; $i -lt 30 -and -not (Test-Port 6379); $i++) { Start-Sleep 1 }
        if (-not (Test-Port 6379)) { throw "Redis did not start on port 6379." }
        Write-Host "      Redis is running." -ForegroundColor Green
    }
} else {
    Write-Host "[1/3] Using the Redis from REDIS_URL in .env." -ForegroundColor Green
}

# ---- 2. GitHub App ----------------------------------------------------------
$appEnv = Read-EnvFile $githubAppEnv
if ($appEnv["APP_ID"] -and $appEnv["PRIVATE_KEY"]) {
    Write-Host "[2/3] GitHub App already created (APP_ID $($appEnv['APP_ID']))." -ForegroundColor Green
} else {
    Write-Host "[2/3] Creating the GitHub App..." -ForegroundColor Green
    if (Test-Port $wizardPort) { throw "Port $wizardPort is in use. Close whatever uses it and run this script again." }

    # A smee.io channel forwards GitHub's webhooks to your laptop, so no public URL is needed.
    if (-not $appEnv["WEBHOOK_PROXY_URL"]) {
        $channel = (& curl.exe -s -o NUL -w "%{redirect_url}" https://smee.io/new)
        if ($channel -notmatch '^https://smee\.io/') { throw "Could not create a smee.io channel. Check your internet connection." }
        $existingLines = if (Test-Path $githubAppEnv) { [IO.File]::ReadAllText($githubAppEnv).TrimEnd() + "`n" } else { "" }
        [IO.File]::WriteAllText($githubAppEnv, $existingLines + "WEBHOOK_PROXY_URL=$channel`n", (New-Object System.Text.UTF8Encoding($false)))
    }

    $env:PORT = "$wizardPort"
    $log = Join-Path $env:TEMP "devbrief-probot-setup.log"
    $proc = Start-Process -FilePath "bunx.exe" -ArgumentList "--bun", "probot", "run", "./src/index.ts" `
        -WorkingDirectory $githubAppDir -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    try {
        for ($i = 0; $i -lt 40 -and -not (Test-Port $wizardPort); $i++) { Start-Sleep 1 }
        if (-not (Test-Port $wizardPort)) { throw "The setup helper did not start. See $log" }

        Start-Process "http://localhost:$wizardPort"
        Write-Host ""
        Write-Host "  Your browser opened. Do this:" -ForegroundColor Cyan
        Write-Host "   1. Click 'Register GitHub App'."
        Write-Host "   2. On GitHub, sign in if asked and click 'Create GitHub App'."
        Write-Host "      (If the name 'DevBrief Reviewer' is taken, type another name first.)"
        Write-Host "   3. GitHub then shows an 'Install' page. Do NOT install here: close that tab."
        Write-Host "      You will install from the DevBrief dashboard, which also links it to your account."
        Write-Host ""
        Write-Host "  Waiting for you to finish (up to 10 minutes)..."

        $done = $false
        for ($i = 0; $i -lt 300 -and -not $done; $i++) {
            Start-Sleep 2
            $v = Read-EnvFile $githubAppEnv
            if ($v["APP_ID"] -and $v["PRIVATE_KEY"] -and $v["GITHUB_CLIENT_SECRET"]) { $done = $true }
        }
        if (-not $done) { throw "Timed out waiting for the GitHub App to be created. Run this script again." }
    } finally {
        if ($proc -and -not $proc.HasExited) { & taskkill /PID $proc.Id /T /F *> $null }
        Remove-Item Env:PORT -ErrorAction SilentlyContinue
    }
    Write-Host "      GitHub App created." -ForegroundColor Green
}

# ---- 3. Copy credentials where they are needed ------------------------------
Write-Host "[3/3] Saving credentials..." -ForegroundColor Green
Push-Location (Join-Path $root "apps\worker")
try {
    & bun run scripts/finish-github-app.ts
    if ($LASTEXITCODE -ne 0) { throw "Could not finish the GitHub App setup (see the message above)." }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next: .\start.ps1"
