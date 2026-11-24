[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,
    [Parameter(Mandatory = $true)]
    [string]$BundleOutputPath,
    [Parameter(Mandatory = $true)]
    [string]$CssOutputPath,
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [Parameter(Mandatory = $true)]
    [string]$StylePath
)

$ErrorActionPreference = 'Stop'
$GameRoot = [IO.Path]::GetFullPath($GameRoot)
$BundleOutputPath = [IO.Path]::GetFullPath($BundleOutputPath)
$CssOutputPath = [IO.Path]::GetFullPath($CssOutputPath)
$bundleProfiles = @(
    @{
        Name = '2.4.1.0'
        PackagePath = Join-Path $GameRoot 'res\packages\gui-part1.pkg'
        EntryPath = 'gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/bundle.js'
        SupportedHashes = @('53726CCCEC189A582835F16381DA5A47529A899EFAE96A562350085CF3649AE9', '3431D4C5026652F6C47766334291CF58203396D506141863CEC035CBB42F98E6')
    },
    @{
        Name = '2.4.0.x'
        PackagePath = Join-Path $GameRoot 'res\packages\gui-part4.pkg'
        EntryPath = 'gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js'
        SupportedHashes = @(
            '9E3C202258E9182E2788BAD4B09C3EDA969AB8F5A73A08CAA6A2B7E377C342C5',
            '50FEDA5422470443F98F2E1B549F04F4E85156DA151BDB953FCEAC61B1DE0AA9',
            '2ED1410D4FE2E3EA65D91800EF2C9EAE99CFA61DC66F2C8BB5E7DC419B09E280'
        )
    }
)
$cssPackagePath = Join-Path $GameRoot 'res\packages\gui-part2.pkg'
$cssEntryPath = 'gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css'
$supportedCssHashes = @(
    'FED446477AD05AFC9556AC3FD92DF45573E8F9121466A562105BAAF695C61726'  # WoT 2.4.0.0
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Read-ZipEntryBytes([string]$packagePath, [string]$entryPath) {
    $zip = [IO.Compression.ZipFile]::OpenRead($packagePath)
    try {
        $entry = $zip.GetEntry($entryPath)
        if (-not $entry) {
            throw "Native tooltip resource is missing: $entryPath"
        }
        $stream = $entry.Open()
        $memory = New-Object IO.MemoryStream
        try {
            $stream.CopyTo($memory)
            return $memory.ToArray()
        }
        finally {
            $memory.Dispose()
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
}

function Get-BytesHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('X2') }) -join '')
    }
    finally {
        $sha.Dispose()
    }
}

$bundleProfile = $null
$bundleBytes = $null
foreach ($candidate in $bundleProfiles) {
    if (-not (Test-Path -LiteralPath $candidate.PackagePath)) {
        continue
    }
    $zip = [IO.Compression.ZipFile]::OpenRead($candidate.PackagePath)
    try {
        $entry = $zip.GetEntry($candidate.EntryPath)
        if (-not $entry) {
            continue
        }
        $stream = $entry.Open()
        $memory = New-Object IO.MemoryStream
        try {
            $stream.CopyTo($memory)
            $bundleBytes = $memory.ToArray()
        }
        finally {
            $memory.Dispose()
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
    $bundleProfile = $candidate
    break
}
if (-not $bundleProfile) {
    throw 'Native tooltip bundle is missing from both the 2.4.1.0 and 2.4.0.x client package layouts.'
}
$cssBytes = Read-ZipEntryBytes $cssPackagePath $cssEntryPath
$bundleHash = Get-BytesHash $bundleBytes
$cssHash = Get-BytesHash $cssBytes
if ($bundleHash -notin $bundleProfile.SupportedHashes) {
    throw "Unsupported native tooltip bundle $bundleHash for client layout $($bundleProfile.Name); supported hashes: $($bundleProfile.SupportedHashes -join ', ')"
}
if ($cssHash -notin $supportedCssHashes) {
    throw "Unsupported native tooltip stylesheet $cssHash; supported hashes: $($supportedCssHashes -join ', ')"
}

$utf8 = New-Object Text.UTF8Encoding($false)
$bundle = [Text.Encoding]::UTF8.GetString($bundleBytes)
$bundle += "`n/* Hangar Carousel Classic tooltip renderer */`n"
$bundle += [IO.File]::ReadAllText([IO.Path]::GetFullPath($ScriptPath), [Text.Encoding]::UTF8)

$css = [Text.Encoding]::UTF8.GetString($cssBytes)
$css += "`n/* Hangar Carousel Classic tooltip styles */`n"
$css += [IO.File]::ReadAllText([IO.Path]::GetFullPath($StylePath), [Text.Encoding]::UTF8)

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BundleOutputPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CssOutputPath) | Out-Null
[IO.File]::WriteAllText($BundleOutputPath, $bundle, $utf8)
[IO.File]::WriteAllText($CssOutputPath, $css, $utf8)
Write-Output "Patched native tooltip bundle: $BundleOutputPath"
Write-Output "Patched native tooltip stylesheet: $CssOutputPath"
