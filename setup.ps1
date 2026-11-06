# DevBrief one-time setup, step 1 of 2: database + secret keys.
# Run from the repo root:
#   .\setup.ps1
#
# Asks for your Neon database URL, generates the secret keys, writes .env and
# apps/web/.env.local, and creates the database tables.
# Safe to re-run: existing values (including GitHub App credentials added by
# step 2) are kept.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$utf8 = New-Object System.Text.UTF8Encoding($false)
$rootEnvPath = Join-Path $root ".env"
$webEnvPath = Join-Path $root "apps\web\.env.local"

function Read-EnvFile($path) {
    $values = @{}
    if (Test-Path $path) {
        foreach ($line in [IO.File]::ReadAllLines($path)) {
            if ($line -match '^\s*([A-Z0-9_]+)\s*=(.*)$') { $values[$Matches[1]] = $Matches[2].Trim() }
        }
    }
    return $values
}

# Sets KEY=value in a .env file: replaces the line if present, appends otherwise.
# Every other line is left untouched.
function Set-EnvValue($path, $key, $value) {
    $lines = New-Object System.Collections.Generic.List[string]
    if (Test-Path $path) { foreach ($l in [IO.File]::ReadAllLines($path)) { $lines.Add($l) } }
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$key\s*=") { $lines[$i] = "$key=$value"; $found = $true; break }
    }
    if (-not $found) { $lines.Add("$key=$value") }
    [IO.File]::WriteAllLines($path, $lines, $utf8)
}

function New-Secret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Test-Placeholder($v) { return (-not $v) -or ($v -match '^<|your_|_here') }

Write-Host ""
Write-Host "DevBrief setup (step 1 of 2)" -ForegroundColor Green
Write-Host "You need your Neon connection string (see LOCAL_SETUP.md, step 1)."
Write-Host ""

$existing = Read-EnvFile $rootEnvPath
$existingWeb = Read-EnvFile $webEnvPath

$databaseUrl = $existing["DATABASE_URL"]
if (-not (Test-Placeholder $databaseUrl)) {
    $databaseUrl = $databaseUrl.Trim("'", '"')
    $answer = Read-Host "Neon connection string [$databaseUrl]  (press Enter to keep)"
    if (-not [string]::IsNullOrWhiteSpace($answer)) { $databaseUrl = $answer.Trim().Trim("'", '"') }
} else {
    $databaseUrl = $null
}
while ($databaseUrl -notmatch '^postgres(ql)?://') {
    $databaseUrl = (Read-Host "Neon connection string (starts with postgresql://)").Trim().Trim("'", '"')
    if ($databaseUrl -notmatch '^postgres(ql)?://') { Write-Host "That does not look like a Postgres URL. Copy it from Neon > Connect." -ForegroundColor Yellow }
}

# Keep an existing ENCRYPTION_KEY: changing it makes already-saved provider keys unreadable.
$encryptionKey = $existing["ENCRYPTION_KEY"]
$validKey = $false
if ($encryptionKey) { try { $validKey = ([Convert]::FromBase64String($encryptionKey).Length -eq 32) } catch { $validKey = $false } }
if (-not $validKey) { $encryptionKey = New-Secret; Write-Host "Generated ENCRYPTION_KEY." }

$authSecret = $existingWeb["AUTH_SECRET"]
if (Test-Placeholder $authSecret) { $authSecret = New-Secret; Write-Host "Generated AUTH_SECRET." }

$internalToken = $existing["INTERNAL_SERVICE_TOKEN"]
if (Test-Placeholder $internalToken) { $internalToken = New-Secret }

Set-EnvValue $rootEnvPath "DATABASE_URL" $databaseUrl
Set-EnvValue $rootEnvPath "ENCRYPTION_KEY" $encryptionKey
Set-EnvValue $rootEnvPath "INTERNAL_SERVICE_TOKEN" $internalToken
Set-EnvValue $rootEnvPath "MAX_DIFF_CHARS" "40000"
if (Test-Placeholder $existing["REDIS_URL"]) { Set-EnvValue $rootEnvPath "REDIS_URL" "redis://localhost:6379" }

Set-EnvValue $webEnvPath "DATABASE_URL" $databaseUrl
Set-EnvValue $webEnvPath "ENCRYPTION_KEY" $encryptionKey
Set-EnvValue $webEnvPath "AUTH_SECRET" $authSecret
Set-EnvValue $webEnvPath "NEXT_PUBLIC_APP_URL" "http://localhost:3000"
Set-EnvValue $webEnvPath "NEXT_PUBLIC_AI_ENGINE_URL" "http://localhost:8000"
Write-Host "Wrote .env and apps\web\.env.local" -ForegroundColor Green

Write-Host ""
Write-Host "Creating database tables..." -ForegroundColor Green
Push-Location (Join-Path $root "packages\db")
try {
    $env:DATABASE_URL = $databaseUrl
    & bunx drizzle-kit migrate
    if ($LASTEXITCODE -ne 0) { throw "Migration failed. Check the Neon connection string and try again." }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Step 1 done." -ForegroundColor Green
Write-Host "Next: .\setup-github-app.ps1"
