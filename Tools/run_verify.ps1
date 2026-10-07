# Run verify_in_editor.py in the scratch project RSFX_dev (UE 5.7). Output: <project>\Saved\verify\sfx_*.png and the log.
param([int]$MaxSec = 900, [string]$Script = 'verify_in_editor.py', [string]$Tag = 'sfxverify')
$proj = 'E:\UE5\RSFX_dev\RSFX_dev.uproject'
$ue = 'C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe'
$L = 'E:\UE5\RSFX_dev\Saved\Logs\RSFX_dev.log'
for ($w = 0; $w -lt 90 -and (Get-Process UnrealEditor -ErrorAction SilentlyContinue); $w++) { Start-Sleep -Seconds 2 }
if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw "UnrealEditor still running" }
if (Test-Path $L) { Move-Item $L ($L + '.prev') -Force -ErrorAction SilentlyContinue }
$a = @("`"$proj`"", "-ExecCmds=`"py E:/UE5/Rapture_StyleFX/Tools/$Script`"", '-nosplash')
$p = Start-Process -FilePath $ue -ArgumentList $a -PassThru; $t0 = Get-Date; $r = 'TIMEOUT'
for ($i = 0; $i -lt [int]($MaxSec / 5); $i++) {
  if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) { $r = 'EXITED'; break }
  if ((Test-Path $L) -and (Select-String -Path $L -Pattern "\[$Tag\] DONE" -Quiet)) { $r = 'DONE'; break }
  Start-Sleep -Seconds 5 }
if ($r -eq 'TIMEOUT') { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
for ($w = 0; $w -lt 60 -and (Get-Process -Id $p.Id -ErrorAction SilentlyContinue); $w++) { Start-Sleep -Seconds 2 }
Get-Process CrashReportClientEditor -ErrorAction SilentlyContinue | Stop-Process -Force
"{0} after {1:N0}s" -f $r, ((Get-Date) - $t0).TotalSeconds
if (Test-Path $L) { Select-String -Path $L -Pattern '\[sfxverify\]|\[sfxparams\]|\[Rapture_StyleFX\]|LogPython: Error|Failed to compile|Fatal error' | ForEach-Object { $_.Line.Substring([Math]::Min(26, $_.Line.Length)) } | Select-Object -First 60 }

