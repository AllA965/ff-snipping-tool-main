$path = 'updater.py'
$lines = Get-Content $path
$filtered = @()
foreach ($line in $lines) {
  if ($line -eq "in__':") { continue }
  $filtered += $line
}
Set-Content -Path $path -Value $filtered -Encoding utf8
