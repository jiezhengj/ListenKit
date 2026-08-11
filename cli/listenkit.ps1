[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $CommandArguments
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$status = 1

function Test-ListenKitCliPython {
    param(
        [Parameter(Mandatory = $true)] [string] $Executable,
        [string[]] $PrefixArguments = @()
    )

    try {
        & $Executable @PrefixArguments -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Add-ListenKitPythonCandidate {
    param(
        [System.Collections.ArrayList] $Candidates,
        [Parameter(Mandatory = $true)] [string] $Executable,
        [string[]] $PrefixArguments = @()
    )

    if ($Executable) {
        [void] $Candidates.Add(
            [PSCustomObject]@{
                Executable = $Executable
                PrefixArguments = $PrefixArguments
            }
        )
    }
}

$hadPythonHome = Test-Path Env:\PYTHONHOME
$originalPythonHome = $env:PYTHONHOME
$hadPythonPath = Test-Path Env:\PYTHONPATH
$originalPythonPath = $env:PYTHONPATH
$hadPythonUtf8 = Test-Path Env:\PYTHONUTF8
$originalPythonUtf8 = $env:PYTHONUTF8
$hadPythonIoEncoding = Test-Path Env:\PYTHONIOENCODING
$originalPythonIoEncoding = $env:PYTHONIOENCODING
$hadPowerShellVersion = Test-Path Env:\LISTENKIT_POWERSHELL_VERSION
$originalPowerShellVersion = $env:LISTENKIT_POWERSHELL_VERSION
$originalConsoleOutputEncoding = [Console]::OutputEncoding
$originalPowerShellOutputEncoding = $OutputEncoding

try {
    Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:LISTENKIT_POWERSHELL_VERSION = $PSVersionTable.PSVersion.ToString()
    $utf8NoBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom

    $candidates = New-Object System.Collections.ArrayList
    if ($env:LISTENKIT_CLI_PYTHON) {
        Add-ListenKitPythonCandidate -Candidates $candidates -Executable $env:LISTENKIT_CLI_PYTHON
    } else {
        if ($env:LISTENKIT_FASTER_WHISPER_VENV_DIR) {
            $managedPython = Join-Path $env:LISTENKIT_FASTER_WHISPER_VENV_DIR "Scripts\python.exe"
            Add-ListenKitPythonCandidate -Candidates $candidates -Executable $managedPython
        } elseif ($env:LOCALAPPDATA) {
            $managedPython = Join-Path $env:LOCALAPPDATA "ListenKit\venvs\cpython-314\Scripts\python.exe"
            Add-ListenKitPythonCandidate -Candidates $candidates -Executable $managedPython
        }
        if ($env:LOCALAPPDATA) {
            $localPython314 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
            Add-ListenKitPythonCandidate -Candidates $candidates -Executable $localPython314
        }
        if ($env:ProgramFiles) {
            $programFilesPython314 = Join-Path $env:ProgramFiles "Python314\python.exe"
            Add-ListenKitPythonCandidate -Candidates $candidates -Executable $programFilesPython314
        }
        Add-ListenKitPythonCandidate -Candidates $candidates -Executable "py" -PrefixArguments @("-3.14")
        Add-ListenKitPythonCandidate -Candidates $candidates -Executable "python3.14"
        Add-ListenKitPythonCandidate -Candidates $candidates -Executable "python"
    }

    $selected = $null
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Executable -CommandType Application -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }
        if (Test-ListenKitCliPython -Executable $command.Source -PrefixArguments $candidate.PrefixArguments) {
            $selected = [PSCustomObject]@{
                Executable = $command.Source
                PrefixArguments = $candidate.PrefixArguments
            }
            break
        }
    }

    if (-not $selected) {
        if ($env:LISTENKIT_CLI_PYTHON) {
            throw "LISTENKIT_CLI_PYTHON is not a usable Python 3.10+ executable: $env:LISTENKIT_CLI_PYTHON"
        }
        throw "Python 3.10 or newer is required to run the ListenKit CLI. This CLI-host requirement is separate from the Python 3.14 managed ASR runtime required by init-runtime. Install Python or set LISTENKIT_CLI_PYTHON."
    }

    $env:PYTHONPATH = $repoRoot
    & $selected.Executable @($selected.PrefixArguments) -m listenkit_cli @CommandArguments
    $status = $LASTEXITCODE
} finally {
    if ($hadPythonHome) {
        $env:PYTHONHOME = $originalPythonHome
    } else {
        Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    }
    if ($hadPythonPath) {
        $env:PYTHONPATH = $originalPythonPath
    } else {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    }
    if ($hadPythonUtf8) {
        $env:PYTHONUTF8 = $originalPythonUtf8
    } else {
        Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
    }
    if ($hadPythonIoEncoding) {
        $env:PYTHONIOENCODING = $originalPythonIoEncoding
    } else {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    }
    if ($hadPowerShellVersion) {
        $env:LISTENKIT_POWERSHELL_VERSION = $originalPowerShellVersion
    } else {
        Remove-Item Env:\LISTENKIT_POWERSHELL_VERSION -ErrorAction SilentlyContinue
    }
    [Console]::OutputEncoding = $originalConsoleOutputEncoding
    $OutputEncoding = $originalPowerShellOutputEncoding
}

exit $status
