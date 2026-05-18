# SENTINEL — Fivetran MCP Setup Script
# Run this from the sentinel folder: .\setup_mcp.ps1

Write-Host "Setting up Fivetran MCP server..." -ForegroundColor Cyan

# Load .env
$envFile = ".\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#][^=]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Write-Host "Loaded .env file" -ForegroundColor Green
} else {
    Write-Host "ERROR: .env file not found. Run from sentinel folder." -ForegroundColor Red
    exit 1
}

# Clone Fivetran MCP if not already present
$mcpPath = "..\fivetran-mcp"
if (-not (Test-Path $mcpPath)) {
    Write-Host "Cloning official Fivetran MCP server..." -ForegroundColor Yellow
    git clone https://github.com/fivetran/fivetran-mcp $mcpPath
    Write-Host "Cloned to $mcpPath" -ForegroundColor Green
} else {
    Write-Host "Fivetran MCP already cloned at $mcpPath" -ForegroundColor Green
}

# Install MCP dependencies
Write-Host "Installing MCP dependencies..." -ForegroundColor Yellow
Push-Location $mcpPath
pip install -r requirements.txt
Pop-Location

# Write MCP config
$mcpConfig = @"
{
  "fivetran_api_key": "$env:FIVETRAN_API_KEY",
  "fivetran_api_secret": "$env:FIVETRAN_API_SECRET",
  "allow_writes": true
}
"@

$mcpConfig | Out-File -FilePath "$mcpPath\.env.sentinel" -Encoding utf8
Write-Host "MCP config written" -ForegroundColor Green

Write-Host ""
Write-Host "DONE. To run the MCP server:" -ForegroundColor Cyan
Write-Host "  cd $mcpPath" -ForegroundColor White
Write-Host "  `$env:FIVETRAN_API_KEY='$env:FIVETRAN_API_KEY'" -ForegroundColor White
Write-Host "  `$env:FIVETRAN_API_SECRET='$env:FIVETRAN_API_SECRET'" -ForegroundColor White
Write-Host "  `$env:FIVETRAN_ALLOW_WRITES='true'" -ForegroundColor White
Write-Host "  python server.py" -ForegroundColor White
