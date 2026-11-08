[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$GameRoot = [IO.Path]::GetFullPath($GameRoot)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$profiles = @(
    @{
        Name = '2.4.1.0'
        PackagePath = Join-Path $GameRoot 'res\packages\comp7.pkg'
        EntryPath = 'comp7/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js'
        SupportedHashes = @(
            '20BF8862B0B5DFDEB79CCFF666725FF76F731E855F0A4D2BFD9C28A19759B172',
            '0CF0AD68AB8A463E6CEF566132090760CC4EF4FD35038AA3982611FFAD67A34C'
        )
    },
    @{
        Name = '2.4.0.x'
        PackagePath = Join-Path $GameRoot 'res\packages\comp7.pkg'
        EntryPath = 'comp7/gui/gameface/_dist/production/mono/lobby/views/hangar/hangar.html/bundle.js'
        SupportedHashes = @(
            '2067FD7C155BC180E12DAF1825DB5E1BCAEBFA094D660E167D33B2FB24FEB6DA',
            'B296E8E6C4DABA266C3C6AC2AA72F91A340C63B4A210B9453A338E04B6E456C4'
        )
    }
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$profile = $null
$sourceBytes = $null
foreach ($candidate in $profiles) {
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
            $sourceBytes = $memory.ToArray()
        }
        finally {
            $memory.Dispose()
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
    $profile = $candidate
    break
}
if (-not $profile) {
    throw 'Comp7 hangar bundle is missing from both the 2.4.1.0 and 2.4.0.x client package layouts.'
}

$sha = [Security.Cryptography.SHA256]::Create()
try {
    $sourceHash = (($sha.ComputeHash($sourceBytes) | ForEach-Object { $_.ToString('X2') }) -join '')
}
finally {
    $sha.Dispose()
}
if ($sourceHash -notin $profile.SupportedHashes) {
    throw "Unsupported Comp7 hangar bundle $sourceHash for client layout $($profile.Name); supported hashes: $($profile.SupportedHashes -join ', ')"
}

$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
if ($profile.Name -eq '2.4.1.0') {
    $replacements = @(
        @(
            '2===e?t.double:t.single',
            '1<e?t.double:t.single'
        ),
        @(
            '2!==t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}',
            '1===t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}'
        ),
        @(
            'v=function(e){return(0,lr.useMemo)(()=>{const t=[];for(let a=0;a<e.length;a+=2)t.push(e.slice(a,a+2));return 1===t.at(-1)?.length&&t.at(-1)?.push(Yf),t},[e])}(b);',
            'v=function(e){return(0,lr.useMemo)(()=>{const t=[];for(let a=0;a<e.length;a+=_)t.push(e.slice(a,a+_));const n=t.at(-1);if(n)for(;n.length<_;)n.push(Yf);return t},[e,_])}(b);'
        ),
        @(
            'function(e,t,a,s,n){const r=2===s;function i(s)',
            'function(e,t,a,s,n){const r=1<s;function i(s)'
        ),
        @(
            'totalElements:2===_?v.length:b.length',
            'totalElements:1<_?v.length:b.length'
        ),
        @(
            'return 2===_?',
            'return 1<_?'
        ),
        @(
            'classNames:{base:Js(Iv,x&&wv),element:Js(jv,t&&Nv)}',
            'classNames:{base:Js(Iv,x&&wv),element:Js(jv,t&&Nv,3===_&&"hcc-native-carousel--3",4===_&&"hcc-native-carousel--4")}'
        ),
        @(
            'className:Js(E$,2===s&&A$)',
            'className:Js(E$,2===s&&A$,3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4")'
        )
    )
}
else {
    $replacements = @(
    @(
        '2===e?t.double:t.single',
        '1<e?t.double:t.single'
    ),
    @(
        '2!==t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}',
        '1===t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}'
    ),
    @(
        'w=(N=C,m.useMemo(()=>{const e=[];for(let t=0;t<N.length;t+=2)e.push(N.slice(t,t+2));return 1===e.at(-1)?.length&&e.at(-1)?.push(nf),e},[N]));var N;',
        'w=(N=C,m.useMemo(()=>{const e=[];for(let t=0;t<N.length;t+=b)e.push(N.slice(t,t+b));const a=e.at(-1);if(a)for(;a.length<b;)a.push(nf);return e},[N,b]));var N;'
    ),
    @(
        'function(e,t,a,s,n){const r=2===s;function i(s)',
        'function(e,t,a,s,n){const r=1<s;function i(s)'
    ),
    @(
        'totalElements:2===b?w.length:C.length',
        'totalElements:1<b?w.length:C.length'
    ),
    @(
        'return 2===b?',
        'return 1<b?'
    ),
    @(
        'className:g(qU,2===s&&$U)',
        'className:g(qU,1<s&&$U,3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4")'
    )
    )
}

foreach ($replacement in $replacements) {
    $from = $replacement[0]
    $to = $replacement[1]
    $count = ([regex]::Matches($source, [regex]::Escape($from))).Count
    if ($count -ne 1) {
        throw "Expected one Comp7 carousel patch point, found $count for: $from"
    }
    $source = $source.Replace($from, $to)
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
[IO.File]::WriteAllText($OutputPath, $source, (New-Object Text.UTF8Encoding($false)))
Write-Output "Patched Comp7 hangar bundle: $OutputPath"
