param([string]$Address = '127.0.0.1', [switch]$Demo, [switch]$AgentRouter, [string]$ListeningTranscript)
$ErrorActionPreference = 'Stop'
$listeningFile = if ($ListeningTranscript) { (Resolve-Path -LiteralPath $ListeningTranscript).Path }
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath './connection.key')) {
    python -c "from pathlib import Path; from secrets import token_urlsafe; Path('connection.key').write_text(token_urlsafe(36), encoding='utf-8')"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$options = @('--bind', $Address)
if ($Demo) { $options += '--demo' }
if ($AgentRouter) { $options += @('--provider', 'agentrouter') }
if ($listeningFile) { $options += @('--listening-transcript', $listeningFile) }
python -X utf8 ./phone_server.py @options
exit $LASTEXITCODE
