param([ValidateSet('setup','seed','ingest','test','lint','run','publish')][string]$Task='run')
$ErrorActionPreference = 'Stop'
function Invoke-Checked { param([string]$Program, [string[]]$Arguments) & $Program @Arguments; if ($LASTEXITCODE -ne 0) { throw "$Program failed ($LASTEXITCODE)" } }
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
switch ($Task) {
  'setup' {
    if (!(Test-Path $python)) { Invoke-Checked 'python' @('-m','venv','.venv') }
    Invoke-Checked $python @('-m','pip','install','-r','requirements.lock')
    Invoke-Checked 'npm.cmd' @('ci')
    Invoke-Checked 'npm.cmd' @('run','build')
    Invoke-Checked $python @('manage.py','migrate')
  }
  'seed' { Invoke-Checked $python @('manage.py','generate_company_data'); Invoke-Checked $python @('manage.py','publish_analytics','--mode','demo') }
  'ingest' { Invoke-Checked $python @('manage.py','ingest_usgs'); Invoke-Checked $python @('manage.py','ingest_nhtsa') }
  'publish' { Invoke-Checked $python @('manage.py','calculate_risk','--mode','live'); Invoke-Checked $python @('manage.py','publish_analytics','--mode','live') }
  'test' { Invoke-Checked $python @('-m','pytest') }
  'lint' { Invoke-Checked $python @('-m','ruff','check','.'); Invoke-Checked $python @('-m','ruff','format','--check','.') }
  'run' { Invoke-Checked $python @('manage.py','runserver') }
}
