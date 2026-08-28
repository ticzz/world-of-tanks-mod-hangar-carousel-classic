[CmdletBinding()]
param(
    [string]$GameRoot = '',
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($PackagePath)) {
    throw "PackagePath is required. This script builds a fullpack from an already-built .wotmod. Run 'build.ps1' instead, or call this script directly with -PackagePath '<path-to>.wotmod' -Version '<version>'."
}
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$PackagePath = [IO.Path]::GetFullPath($PackagePath)

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
foreach ($candidate in @('2.3.1.3', '2.3.1.2')) {
    $candidatePath = Join-Path $distModsRoot $candidate
    if (Test-Path -LiteralPath $candidatePath) {
        $dependencyRoots += $candidatePath
    }
}

$dependencies = $null
$settingsApi = $null
$gameface = $null
foreach ($root in ($dependencyRoots | Select-Object -Unique)) {
    $candidateSettings = Join-Path $root 'aslain.modssettingsapi_1.7.1.wotmod'
    $candidateGameface = Join-Path $root 'net.openwg\net.openwg.gameface_1.1.6.wotmod'
    if ((Test-Path -LiteralPath $candidateSettings) -and (Test-Path -LiteralPath $candidateGameface)) {
        $dependencies = $root
        $settingsApi = $candidateSettings
        $gameface = $candidateGameface
        $resolvedVersion = [IO.Path]::GetFileName($root)
        break
    }
}
if (-not $dependencies) {
    throw "No supported dependency bundle found using actual client path or dist\mods. Expected aslain.modssettingsapi_1.7.1.wotmod and net.openwg.gameface_1.1.6.wotmod."
}

$releaseRoot = Join-Path $repo ('build\release-{0}-full' -f $Version)
$modsRoot = Join-Path $releaseRoot ("mods\$resolvedVersion")
$outputPath = Join-Path $repo ('dist\hangar_carousel_classic_{0}_full.zip' -f $Version)

foreach ($source in @($PackagePath, $settingsApi, $gameface)) {
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Fullpack dependency is missing: $source"
    }
}

Remove-Item -LiteralPath $releaseRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path (Join-Path $modsRoot 'net.openwg') | Out-Null
Copy-Item -LiteralPath $PackagePath -Destination (Join-Path $modsRoot ([IO.Path]::GetFileName($PackagePath)))
Copy-Item -LiteralPath $settingsApi -Destination (Join-Path $modsRoot ([IO.Path]::GetFileName($settingsApi)))
Copy-Item -LiteralPath $gameface -Destination (Join-Path $modsRoot 'net.openwg\net.openwg.gameface_1.1.6.wotmod')

Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($releaseRoot, $outputPath, [IO.Compression.CompressionLevel]::NoCompression, $false)

$archive = [IO.Compression.ZipFile]::OpenRead($outputPath)
try {
    $required = @(
        ("mods/$resolvedVersion/" + [IO.Path]::GetFileName($PackagePath)),
        "mods/$resolvedVersion/aslain.modssettingsapi_1.7.1.wotmod",
        "mods/$resolvedVersion/net.openwg/net.openwg.gameface_1.1.6.wotmod"
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