[CmdletBinding()]
param(
    [string]$GameRoot = '',
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,
    [Parameter(Mandatory = $false)]
    [string]$Version
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($PackagePath)) {
    throw "PackagePath is required. This script builds a fullpack from an already-built .wotmod. Run 'build.ps1' instead, or call this script directly with -PackagePath '<path-to>.wotmod' -Version '<version>'."
}
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$PackagePath = [IO.Path]::GetFullPath($PackagePath)
if ([string]::IsNullOrWhiteSpace($Version)) {
    [xml]$meta = Get-Content -LiteralPath (Join-Path $repo 'meta.xml') -Raw
    $Version = [string]$meta.root.version
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw 'Version is missing from meta.xml; specify -Version explicitly.'
}

function Resolve-GameRoot {
    param([string]$PreferredRoot)

    $candidates = @()
    if ($PreferredRoot) {
        $candidates += $PreferredRoot
    }
    if ($env:WOT_ROOT) {
        $candidates += $env:WOT_ROOT
    }
    $candidates += 'G:\Games\World_of_Tanks_EU'
    $candidates += 'E:\Games\World_of_Tanks_EU'

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        try {
            $root = [IO.Path]::GetFullPath($candidate)
        }
        catch {
            continue
        }

        $versionXml = Join-Path $root 'version.xml'
        if (-not (Test-Path -LiteralPath $versionXml)) {
            continue
        }

        try {
            [xml]$versionData = Get-Content -LiteralPath $versionXml -Raw
        }
        catch {
            continue
        }

        $clientVersion = [string]$versionData.DocumentElement.version
        $match = [regex]::Match($clientVersion, '\d+\.\d+\.\d+\.\d+')
        if ($match.Success) {
            return [pscustomobject]@{
                Root = $root
                Version = $match.Value
            }
        }
    }

    throw "World of Tanks root not found. Set -GameRoot or WOT_ROOT to a valid client root containing version.xml with a client version."
}

$resolvedRoot = Resolve-GameRoot -PreferredRoot $GameRoot
$modsVersion = $resolvedRoot.Version
$modsRootFromClient = Join-Path $resolvedRoot.Root ("mods\$modsVersion")
$distModsRoot = Join-Path $repo 'dist\mods'
$resolvedVersion = $modsVersion
$dependencyRoots = @($modsRootFromClient)
if (Test-Path -LiteralPath $distModsRoot) {
$dependencyRoots += Get-ChildItem -LiteralPath $distModsRoot -Directory |
    Sort-Object Name -Descending |
    Select-Object -ExpandProperty FullName
}
$dependencyRoots = $dependencyRoots | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -Unique

function Select-LatestPackage {
param([string]$Directory, [string]$Filter)

$packages = @(Get-ChildItem -LiteralPath $Directory -Filter $Filter -File -ErrorAction SilentlyContinue)
if ($packages.Count -eq 0) {
    return $null
}
return $packages | Sort-Object Name -Descending | Select-Object -First 1
}

$dependencies = $null
$modMenu = $null
$gameface = $null
foreach ($root in ($dependencyRoots | Select-Object -Unique)) {
    $candidateModMenu = Select-LatestPackage $root 'aslain.modmenu_*.wotmod'
    $candidateGameface = Select-LatestPackage (Join-Path $root 'net.openwg') 'net.openwg.gameface_*.wotmod'
    if ($candidateModMenu -and $candidateGameface) {
        $dependencies = $root
        $modMenu = $candidateModMenu.FullName
        $gameface = $candidateGameface.FullName
        break
    }
}
if (-not $dependencies) {
    throw 'No dependency bundle found. Expected aslain.modmenu_*.wotmod and net.openwg.gameface_*.wotmod in the client mods directory or dist\mods.'
}

$releaseRoot = Join-Path $repo ('build\release-{0}-full' -f $Version)
$modsRoot = Join-Path $releaseRoot ("mods\$resolvedVersion")
$outputPath = Join-Path $repo ('dist\hangar_carousel_classic_{0}_full.zip' -f $Version)

foreach ($source in @($PackagePath, $modMenu, $gameface)) {
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Fullpack dependency is missing: $source"
    }
}

Remove-Item -LiteralPath $releaseRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path (Join-Path $modsRoot 'net.openwg') | Out-Null
Copy-Item -LiteralPath $PackagePath -Destination (Join-Path $modsRoot ([IO.Path]::GetFileName($PackagePath)))
Copy-Item -LiteralPath $modMenu -Destination (Join-Path $modsRoot ([IO.Path]::GetFileName($modMenu)))
Copy-Item -LiteralPath $gameface -Destination (Join-Path $modsRoot ('net.openwg\' + [IO.Path]::GetFileName($gameface)))

Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($releaseRoot, $outputPath, [IO.Compression.CompressionLevel]::NoCompression, $false)

$archive = [IO.Compression.ZipFile]::OpenRead($outputPath)
try {
    $required = @(
        ("mods/$resolvedVersion/" + [IO.Path]::GetFileName($PackagePath)),
        ("mods/$resolvedVersion/" + [IO.Path]::GetFileName($modMenu)),
        ("mods/$resolvedVersion/net.openwg/" + [IO.Path]::GetFileName($gameface))
    )
    $entries = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
    foreach ($entry in $required) {
        if ($entry -notin $entries) {
            throw "Fullpack entry is missing: $entry"
        }
    }
}
finally {
    $archive.Dispose()
}

Write-Output "Built full package: $outputPath"