[CmdletBinding()]
param(
    [string]$Python27,
    [switch]$Install,
    [string]$GameRoot = ''
)

$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$build = Join-Path $repo 'build'
$stage = Join-Path $build 'stage'
$dist = Join-Path $repo 'dist'
$metaPath = Join-Path $repo 'meta.xml'
[xml]$meta = Get-Content -LiteralPath $metaPath -Raw
$version = [string]$meta.root.version
if ([string]::IsNullOrWhiteSpace($version)) {
    throw "Version missing in $metaPath"
}
$packageName = "mod_hangar_carousel_classic_$version.wotmod"
$packagePath = Join-Path $dist $packageName
$packagePathUnversioned = Join-Path $dist 'mod_hangar_carousel_classic.wotmod'

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
        if (Test-Path -LiteralPath (Join-Path $root 'res\packages\gui-part3.pkg')) {
            return $root
        }
    }

    throw "World of Tanks root not found. Set -GameRoot or WOT_ROOT to a valid client root containing res\\packages\\gui-part3.pkg."
}

$GameRoot = Resolve-GameRoot -PreferredRoot $GameRoot

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Resolve-NativeEntryPath {
    param(
        [Parameter(Mandatory = $true)] [string]$PackageName,
        [Parameter(Mandatory = $true)] [string]$CurrentEntry,
        [Parameter(Mandatory = $true)] [string]$LegacyEntry
    )

    $packagePath = Join-Path $GameRoot ('res\packages\' + $PackageName)
    $zip = [IO.Compression.ZipFile]::OpenRead($packagePath)
    try {
        if ($zip.GetEntry($CurrentEntry)) {
            return $CurrentEntry
        }
        if ($zip.GetEntry($LegacyEntry)) {
            return $LegacyEntry
        }
    }
    finally {
        $zip.Dispose()
    }
    throw "Native resource entry not found in $packagePath."
}

$mainEntry = Resolve-NativeEntryPath `
    -PackageName 'gui-part2.pkg' `
    -CurrentEntry 'gui/gameface/_dist/production/mono/hangar/main/bundle.js' `
    -LegacyEntry 'gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js'
$comp7Entry = Resolve-NativeEntryPath `
    -PackageName 'comp7.pkg' `
    -CurrentEntry 'comp7/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js' `
    -LegacyEntry 'comp7/gui/gameface/_dist/production/mono/lobby/views/hangar/hangar.html/bundle.js'
$frontlineEntry = 'frontline/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js'
$frontlinePackagePath = Join-Path $GameRoot 'res\packages\frontline.pkg'
if (-not (Test-Path -LiteralPath $frontlinePackagePath)) {
    throw "Frontline package not found: $frontlinePackagePath"
}
$frontlineZip = [IO.Compression.ZipFile]::OpenRead($frontlinePackagePath)
try {
    if (-not $frontlineZip.GetEntry($frontlineEntry)) {
        throw "Frontline hangar bundle not found in $frontlinePackagePath."
    }
}
finally {
    $frontlineZip.Dispose()
}
$tooltipEntry = Resolve-NativeEntryPath `
    -PackageName 'gui-part1.pkg' `
    -CurrentEntry 'gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/bundle.js' `
    -LegacyEntry 'gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js'
$mainBundleOutput = Join-Path $stage ('res\' + $mainEntry.Replace('/', '\'))
$comp7BundleOutput = Join-Path $stage ('res\' + $comp7Entry.Replace('/', '\'))
$frontlineBundleOutput = Join-Path $stage ('res\' + $frontlineEntry.Replace('/', '\'))
$tooltipBundleOutput = Join-Path $stage ('res\' + $tooltipEntry.Replace('/', '\'))

if (-not $Python27) {
    $Python27 = & (Join-Path $PSScriptRoot 'bootstrap-python27.ps1')
}
$Python27 = [IO.Path]::GetFullPath(($Python27 | Select-Object -Last 1))
if (-not (Test-Path -LiteralPath $Python27)) {
    throw "Python 2.7 not found: $Python27"
}

Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path `
    (Join-Path $stage 'res\scripts\client\gui\mods'), `
    (Join-Path $stage 'res\gui\gameface\mods\hcc\hangar_carousel_classic'), `
    (Split-Path -Parent $mainBundleOutput), `
    (Split-Path -Parent $comp7BundleOutput), `
    (Split-Path -Parent $frontlineBundleOutput), `
    (Split-Path -Parent $tooltipBundleOutput), `
    (Join-Path $stage 'res\gui\gameface\_dist\production\mono\hangar\vehicle_tooltip'), `
    $dist | Out-Null

$pythonSource = Join-Path $repo 'res\scripts\client\gui\mods\mod_hangar_carousel_classic.py'
$pythonText = Get-Content -LiteralPath $pythonSource -Raw
if ($pythonText.Contains('.createPlaylist(')) {
    throw 'Classic must not create dynamic vehicle playlists.'
}
& $Python27 -m py_compile $pythonSource
if ($LASTEXITCODE -ne 0) {
    throw 'Python 2.7 compilation failed.'
}
$compiled = "$pythonSource`c"

Copy-Item -LiteralPath (Join-Path $repo 'meta.xml') -Destination (Join-Path $stage 'meta.xml')
Copy-Item -LiteralPath $compiled -Destination (Join-Path $stage 'res\scripts\client\gui\mods\mod_hangar_carousel_classic.pyc')
Copy-Item -LiteralPath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.js') `
    -Destination (Join-Path $stage 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.js')
Copy-Item -LiteralPath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.js') `
    -Destination (Join-Path $stage 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.js')
Copy-Item -LiteralPath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.css') `
    -Destination (Join-Path $stage 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.css')
Copy-Item -LiteralPath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.css') `
    -Destination (Join-Path $stage 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.css')
& (Join-Path $PSScriptRoot 'patch-native-carousel.ps1') `
    -GameRoot $GameRoot `
    -OutputPath $mainBundleOutput
& (Join-Path $PSScriptRoot 'patch-native-comp7-carousel.ps1') `
    -GameRoot $GameRoot `
    -OutputPath $comp7BundleOutput
& (Join-Path $PSScriptRoot 'patch-native-frontline-carousel.ps1') `
    -GameRoot $GameRoot `
    -OutputPath $frontlineBundleOutput
& (Join-Path $PSScriptRoot 'patch-native-tooltip.ps1') `
    -GameRoot $GameRoot `
    -BundleOutputPath $tooltipBundleOutput `
    -CssOutputPath (Join-Path $stage 'res\gui\gameface\_dist\production\mono\hangar\vehicle_tooltip\vehicle_tooltip.css') `
    -ScriptPath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.js') `
    -StylePath (Join-Path $repo 'res\gui\gameface\mods\hcc\hangar_carousel_classic\hangar_carousel_classic.tooltip.css')

Remove-Item -LiteralPath $packagePath -Force -ErrorAction SilentlyContinue
& $Python27 (Join-Path $PSScriptRoot 'package_wotmod.py') $stage $packagePath
if ($LASTEXITCODE -ne 0) {
    throw 'WoT package creation failed.'
}

Remove-Item -LiteralPath $packagePathUnversioned -Force -ErrorAction SilentlyContinue
& $Python27 (Join-Path $PSScriptRoot 'package_wotmod.py') $stage $packagePathUnversioned
if ($LASTEXITCODE -ne 0) {
    throw 'Unversioned WoT package creation failed.'
}

& (Join-Path $PSScriptRoot 'validate.ps1') -PackagePath $packagePath
& (Join-Path $PSScriptRoot 'validate.ps1') -PackagePath $packagePathUnversioned
& (Join-Path $PSScriptRoot 'build-full.ps1') -PackagePath $packagePath -Version $version -GameRoot $GameRoot
if ($Install) {
    & (Join-Path $PSScriptRoot 'install.ps1') -GameRoot $GameRoot -PackagePath $packagePath
}

Write-Output $packagePath
Write-Output $packagePathUnversioned
