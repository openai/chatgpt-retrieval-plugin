<#
.SYNOPSIS
    Durchsucht alle verfügbaren lokalen und Netzwerk-Laufwerke nach Audiodateien
    und kopiert sie in einen zentralen Ordner "Audio_Quelle".

.DESCRIPTION
    - Alle Dateisystemlaufwerke (lokal und gemountete Netzwerkshares) werden rekursiv durchsucht.
    - Audiodateien mit den gebräuchlichsten Erweiterungen werden berücksichtigt.
    - Ordner, deren Pfad "Ableton" enthält, werden übersprungen.
    - Bereits vorhandene Dateien werden nicht überschrieben; stattdessen wird
      ein eindeutiger Dateiname erzeugt, sodass beide Versionen erhalten bleiben.

.NOTES
    Speichern Sie dieses Skript als audio_collect.ps1 und führen Sie es in einer
    PowerShell-Sitzung mit ausreichenden Berechtigungen aus.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Destination = (Join-Path -Path $env:USERPROFILE -ChildPath 'Audio_Quelle'),

    [string[]]$Extensions = @('*.mp3', '*.wav', '*.aiff', '*.flac', '*.aac', '*.ogg', '*.wma', '*.m4a'),

    [ValidateSet('Copy', 'HardLink')]
    [string]$TransferMode = 'Copy'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Destination)) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}

function Resolve-NormalizedPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
        return [System.IO.Path]::GetFullPath($resolved.ProviderPath)
    }
    catch {
        return $null
    }
}

$destinationFullPath = Resolve-NormalizedPath -Path $Destination

if (-not $destinationFullPath) {
    throw "Zielpfad '$Destination' konnte nicht aufgelöst werden."
}

function Test-IsDescendantPath {
    param(
        [Parameter(Mandatory)]
        [string]$Candidate,

        [Parameter(Mandatory)]
        [string]$Ancestor
    )

    try {
        $candidateFull = [System.IO.Path]::GetFullPath($Candidate)
    }
    catch {
        return $false
    }

    $ancestorFull = $Ancestor

    if (-not $ancestorFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $ancestorFull += [System.IO.Path]::DirectorySeparatorChar
    }

    return $candidateFull.Equals($Ancestor, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($ancestorFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-IsAbletonPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not $Path) {
        return $false
    }

    return $Path -match '(?i)(?:^|[\\/])Ableton(?:$|[\\/])'
}

function Get-UniqueTargetPath {
    param(
        [Parameter(Mandatory)]
        [string]$DestinationDirectory,

        [Parameter(Mandatory)]
        [string]$FileName
    )

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($FileName)
    $extension = [System.IO.Path]::GetExtension($FileName)
    $targetPath = Join-Path -Path $DestinationDirectory -ChildPath $FileName
    $suffix = 1

    while (Test-Path -LiteralPath $targetPath) {
        $newName = "{0} ({1}){2}" -f $baseName, $suffix, $extension
        $targetPath = Join-Path -Path $DestinationDirectory -ChildPath $newName
        $suffix += 1
    }

    return $targetPath
}

function Copy-AudioFile {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)]
        [System.IO.FileInfo]$Source,

        [Parameter(Mandatory)]
        [string]$DestinationDirectory
    )

    $targetPath = Get-UniqueTargetPath -DestinationDirectory $DestinationDirectory -FileName $Source.Name

    if ($PSCmdlet.ShouldProcess($Source.FullName, "Kopieren nach $targetPath")) {
        Copy-Item -LiteralPath $Source.FullName -Destination $targetPath
    }
}

function New-HardLinkOrCopy {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)]
        [System.IO.FileInfo]$Source,

        [Parameter(Mandatory)]
        [string]$DestinationDirectory
    )

    $targetPath = Get-UniqueTargetPath -DestinationDirectory $DestinationDirectory -FileName $Source.Name

    $sourceRoot = [System.IO.Path]::GetPathRoot($Source.FullName)
    $destinationRoot = [System.IO.Path]::GetPathRoot((Resolve-Path -LiteralPath $DestinationDirectory).Path)

    if ($sourceRoot -ieq $destinationRoot) {
        if ($PSCmdlet.ShouldProcess($Source.FullName, "Hardlink nach $targetPath")) {
            New-Item -ItemType HardLink -Path $targetPath -Value $Source.FullName | Out-Null
        }
    }
    else {
        Write-Warning "Hardlinks sind nur innerhalb desselben Laufwerks möglich. Datei wird kopiert: $($Source.FullName)"
        if ($PSCmdlet.ShouldProcess($Source.FullName, "Kopieren nach $targetPath")) {
            Copy-Item -LiteralPath $Source.FullName -Destination $targetPath
        }
    }
}

$searchRoots = @()

function Add-SearchRoot {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $normalized = Resolve-NormalizedPath -Path $Path

    if (-not $normalized) {
        return
    }

    if (Test-IsDescendantPath -Candidate $normalized -Ancestor $destinationFullPath) {
        return
    }

    if (-not ($searchRoots | Where-Object { $_.Normalized -eq $normalized })) {
        $searchRoots += [pscustomobject]@{ Original = $Path; Normalized = $normalized }
    }
}

Get-PSDrive -PSProvider FileSystem |
    Where-Object { $_.Root } |
    ForEach-Object { Add-SearchRoot -Path $_.Root }

if ($IsMacOS -or $IsLinux) {
    $volumeRoot = '/Volumes'
    if (Test-Path -LiteralPath $volumeRoot) {
        Get-ChildItem -LiteralPath $volumeRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Add-SearchRoot -Path $_.FullName }
    }
}

foreach ($root in $searchRoots) {
    foreach ($pattern in $Extensions) {
        Get-ChildItem -Path $root.Original -Filter $pattern -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object {
                -not (Test-IsAbletonPath -Path $_.DirectoryName) -and
                -not (Test-IsDescendantPath -Candidate $_.FullName -Ancestor $destinationFullPath)
            } |
            ForEach-Object {
                if ($TransferMode -eq 'HardLink') {
                    New-HardLinkOrCopy -Source $_ -DestinationDirectory $Destination
                }
                else {
                    Copy-AudioFile -Source $_ -DestinationDirectory $Destination
                }
            }
    }
}

if ($TransferMode -eq 'HardLink') {
    Write-Host "Audiodateien wurden nach '$Destination' verlinkt oder kopiert (falls Hardlink nicht möglich war)." -ForegroundColor Green
}
else {
    Write-Host "Audiodateien wurden nach '$Destination' kopiert." -ForegroundColor Green
}
