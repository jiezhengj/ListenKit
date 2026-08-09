[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $CommandArguments
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-ListenKitCliPython {
    param(
        [Parameter(Mandatory = $true)] [string] $Executable,
        [string[]] $PrefixArguments = @()
    )

    & $Executable @PrefixArguments -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

$candidates = @()
if ($env:LISTENKIT_CLI_PYTHON) {
    $candidates += ,@($env:LISTENKIT_CLI_PYTHON, @())
} else {
    $candidates += ,@("py", @("-3.14"))
    $candidates += ,@("python3.14", @())
    $candidates += ,@("python", @())
}

$selected = $null
foreach ($candidate in $candidates) {
    $command = Get-Command $candidate[0] -ErrorAction SilentlyContinue
    if (-not $command) {
        continue
    }
    if (Test-ListenKitCliPython -Executable $command.Source -PrefixArguments $candidate[1]) {
        $selected = @($command.Source, $candidate[1])
        break
    }
}

if (-not $selected) {
    throw "Python 3.10 or newer is required to run the ListenKit CLI."
}

$originalPythonPath = $env:PYTHONPATH
$originalPythonUtf8 = $env:PYTHONUTF8
$originalPythonIoEncoding = $env:PYTHONIOENCODING
$originalPowerShellVersion = $env:LISTENKIT_POWERSHELL_VERSION
try {
    if ($originalPythonPath) {
        $env:PYTHONPATH = "$repoRoot$([IO.Path]::PathSeparator)$originalPythonPath"
    } else {
        $env:PYTHONPATH = $repoRoot
    }
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:LISTENKIT_POWERSHELL_VERSION = $PSVersionTable.PSVersion.ToString()
    & $selected[0] @($selected[1]) -m listenkit_cli @CommandArguments
    $status = $LASTEXITCODE
} finally {
    if ($null -eq $originalPythonPath) {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $originalPythonPath
    }
    if ($null -eq $originalPythonUtf8) {
        Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONUTF8 = $originalPythonUtf8
    }
    if ($null -eq $originalPythonIoEncoding) {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONIOENCODING = $originalPythonIoEncoding
    }
    if ($null -eq $originalPowerShellVersion) {
        Remove-Item Env:\LISTENKIT_POWERSHELL_VERSION -ErrorAction SilentlyContinue
    } else {
        $env:LISTENKIT_POWERSHELL_VERSION = $originalPowerShellVersion
    }
}

exit $status
