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
$bundlePackagePath = Join-Path $GameRoot 'res\packages\gui-part4.pkg'
$cssPackagePath = Join-Path $GameRoot 'res\packages\gui-part2.pkg'
$bundleEntryPath = 'gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js'
$cssEntryPath = 'gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css'
$supportedBundleHashes = @(
    '9E3C202258E9182E2788BAD4B09C3EDA969AB8F5A73A08CAA6A2B7E377C342C5'  # WoT 2.4.0.0
)
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

$bundleBytes = Read-ZipEntryBytes $bundlePackagePath $bundleEntryPath
$cssBytes = Read-ZipEntryBytes $cssPackagePath $cssEntryPath
$bundleHash = Get-BytesHash $bundleBytes
$cssHash = Get-BytesHash $cssBytes
if ($bundleHash -notin $supportedBundleHashes) {
    throw "Unsupported native tooltip bundle $bundleHash; supported hashes: $($supportedBundleHashes -join ', ')"
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
