$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$python = (Get-Command python.exe -ErrorAction Stop).Source
$buildRoot = Join-Path $env:TEMP 'CardClickerBuild'
$venv = Join-Path $buildRoot 'venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$dist = Join-Path $buildRoot 'dist'
$work = Join-Path $buildRoot 'work'
$spec = Join-Path $buildRoot 'spec'
$stageRoot = Join-Path $buildRoot 'package'
$stage = Join-Path $stageRoot 'NoPixel Giveaway Clicker'
$stageRootFull = [System.IO.Path]::GetFullPath($stageRoot).TrimEnd('\') + '\'
$stageFull = [System.IO.Path]::GetFullPath($stage)
$release = Join-Path $project 'release'

New-Item -ItemType Directory -Force -Path $buildRoot, $release | Out-Null
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv --system-site-packages $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the temporary build environment.' }
}
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $project 'requirements.txt') -r (Join-Path $project 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install the build requirements.' }

& $venvPython -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all playwright --collect-all greenlet --name 'NoPixel Giveaway Clicker' --distpath $dist --workpath $work --specpath $spec (Join-Path $project 'auto_clicker.py')
if ($LASTEXITCODE -ne 0) { throw 'The standalone app build failed.' }

if (-not $stageFull.StartsWith($stageRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The package staging path is outside the temporary build folder.'
}
if (Test-Path -LiteralPath $stageFull) {
    Remove-Item -LiteralPath $stageFull -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stageFull | Out-Null
Copy-Item -LiteralPath (Join-Path $dist 'NoPixel Giveaway Clicker.exe') -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $project 'Create Desktop Shortcut.vbs') -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $project 'QUICK_START.txt') -Destination $stage -Force
$archive = Join-Path $release 'NoPixel Giveaway Clicker.zip'
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -CompressionLevel Optimal -Force
Write-Host "Package ready: $archive"
