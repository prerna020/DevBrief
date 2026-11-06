# Starts everything DevBrief needs, each service in its own window:
#   AI engine (8000), dashboard (3000), GitHub App receiver (3002), review worker.
# Run from the repo root:
#   .\start.ps1
# Close a window (or press Ctrl+C in it) to stop that service.
#
# The dashboard runs as an optimized production build (fast pages). It is
# rebuilt automatically when its code changed since the last build.
# To work on the dashboard code with live reload instead:  .\start.ps1 -Dev

param([switch]$Dev)

$root = $PSScriptRoot

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

$rootEnv = Read-EnvFile (Join-Path $root ".env")
$webEnv = Read-EnvFile (Join-Path $root "apps\web\.env.local")

if (-not $rootEnv["DATABASE_URL"] -or -not $webEnv["AUTH_SECRET"]) {
    Write-Host "Run step 1 first:  .\setup.ps1" -ForegroundColor Yellow
    exit 1
}
if (-not $rootEnv["APP_ID"] -or -not $webEnv["AUTH_GITHUB_ID"]) {
    Write-Host "Run step 2 first:  .\setup-github-app.ps1" -ForegroundColor Yellow
    exit 1
}

$uvicorn = Join-Path $root ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    Write-Host "Python environment missing. Run: uv sync --all-packages" -ForegroundColor Yellow
    exit 1
}

# Redis must be up before the receiver and worker start.
$redisUrl = $rootEnv["REDIS_URL"]
if ((-not $redisUrl) -or ($redisUrl -match '://(localhost|127\.0\.0\.1)')) {
    if (-not (Test-Port 6379)) {
        Write-Host "Redis is not running. Start Docker Desktop, then run:  docker compose up -d redis" -ForegroundColor Yellow
        Write-Host "(or re-run setup-github-app.ps1, which does this for you)"
        exit 1
    }
}

foreach ($p in @(@(3000, "dashboard"), @(3002, "GitHub App receiver"), @(8000, "AI engine"))) {
    if (Test-Port $p[0]) {
        Write-Host "Port $($p[0]) ($($p[1])) is already in use. Close the old DevBrief windows and try again." -ForegroundColor Yellow
        exit 1
    }
}

function Start-DevBriefWindow($title, $dir, $command) {
    Start-Process powershell -WorkingDirectory $dir -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
    )
}

Start-DevBriefWindow "DevBrief AI engine :8000" (Join-Path $root "services\ai-engine") "& '$uvicorn' app.main:app --port 8000"
$webDir = Join-Path $root "apps\web"
$buildId = Join-Path $webDir ".next\BUILD_ID"

if ($Dev) {
    # `next dev` and `next build` share the .next folder; start dev from a clean one.
    Remove-Item -Recurse -Force (Join-Path $webDir ".next") -ErrorAction SilentlyContinue
    $webCommand = "`$env:DEVBRIEF_LOCAL = '1'; bun run dev"
} else {
    $needsBuild = -not (Test-Path $buildId)
    if (-not $needsBuild) {
        $builtAt = (Get-Item $buildId).LastWriteTime
        $watched = @(
            (Join-Path $webDir "app"), (Join-Path $webDir "components"), (Join-Path $webDir "lib"),
            (Join-Path $webDir "public"), (Join-Path $root "packages\db\src")
        )
        $files = @(Get-ChildItem -Path $watched -Recurse -File -ErrorAction SilentlyContinue)
        foreach ($name in "package.json", "next.config.ts", "instrumentation.ts", ".env.local", "middleware.ts", "auth.ts", "auth.config.ts") {
            $p = Join-Path $webDir $name
            if (Test-Path $p) { $files += Get-Item $p }
        }
        $newest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($newest -and $newest.LastWriteTime -gt $builtAt) { $needsBuild = $true }
    }
    if ($needsBuild) {
        Write-Host "Building the dashboard (about 30 seconds; only needed after code changes)..." -ForegroundColor Cyan
        Push-Location $webDir
        try { & bun run build } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "The dashboard build failed. Fix the error above, or run .\start.ps1 -Dev" -ForegroundColor Yellow
            exit 1
        }
    }
    $webCommand = "`$env:DEVBRIEF_LOCAL = '1'; bun run start"
}
Start-DevBriefWindow "DevBrief dashboard :3000" $webDir $webCommand
Start-DevBriefWindow "DevBrief GitHub receiver :3002" (Join-Path $root "apps\github-app") "`$env:PORT = '3002'; bunx --bun probot run ./src/index.ts"
Start-DevBriefWindow "DevBrief review worker" (Join-Path $root "apps\worker") "bun run start:review"

Write-Host "Started four windows:" -ForegroundColor Green
Write-Host "  Dashboard:         http://localhost:3000"
Write-Host "  AI engine health:  http://localhost:8000/v1/health"
Write-Host "  GitHub receiver:   listening on :3002 (webhooks arrive through smee.io)"
Write-Host "  Review worker:     watches the queue"
Write-Host ""
Write-Host "Next: open the dashboard, sign in, connect your AI key in Settings,"
Write-Host "then click 'Install DevBrief on GitHub' and pick a repo."
