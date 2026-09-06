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
$packagePath = Join-Path $GameRoot 'res\packages\gui-part3.pkg'
$entryPath = 'gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js'
$supportedHashes = @(
    '98D4D4060C141B5728F9126E4B43AD9E0E0BD6BA3FC72E14156391DB54737FBA'  # WoT 2.4.0.0
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($packagePath)
try {
    $entry = $zip.GetEntry($entryPath)
    if (-not $entry) {
        throw "Native hangar bundle is missing: $entryPath"
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

$sha = [Security.Cryptography.SHA256]::Create()
try {
    $sourceHash = (($sha.ComputeHash($sourceBytes) | ForEach-Object { $_.ToString('X2') }) -join '')
}
finally {
    $sha.Dispose()
}
if ($sourceHash -notin $supportedHashes) {
    throw "Unsupported native hangar bundle $sourceHash; supported hashes: $($supportedHashes -join ', ')"
}

$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
$replacements = @(
    @(
        'r={...t.primitives(["defaultFilters"])},',
        'r={...t.primitives(["defaultFilters","hccCarouselAuto","hccSortJson"])},'
    ),
    @(
        'l={...t.primitives(["carouselRowCount"]),filters:e.box(i,{deep:!1}),searchName:e.box(n?.[0]??""),nations:t.arrayClone("nationsOrder")};',
        'l={...t.primitives(["carouselRowCount"]),hccCarouselAuto:r.hccCarouselAuto,hccSortJson:r.hccSortJson,filters:e.box(i,{deep:!1}),searchName:e.box(n?.[0]??""),nations:t.arrayClone("nationsOrder")};'
    ),
    @(
        'h=q.primitive(()=>{const e=[...m.getAll()],t=a.requires.filters.model.computes.nationToIndex();return e.sort((e,a)=>Hi(t,Wi,e,a)),e});',
        'h=q.primitive(()=>{const e=[...m.getAll()],t=a.requires.filters.model.computes.nationToIndex(),s=(()=>{try{return JSON.parse(a.requires.filters.model.hccSortJson.get()||"{}")}catch(e){return{}}})(),n=s.values||{},i=new Set((s.allowed||[]).map(e=>String(e)));return s.filtered&&e.splice(0,e.length,...e.filter(e=>i.has(String(e.id))||i.has(String(e.inventoryId)))),e.sort((e,a)=>{const t=n[String(e.id)]||n[e.id]||[],s=n[String(a.id)]||n[a.id]||[];for(let e=0;e<t.length;e++){const a=Number(t[e]??0),n=Number(s[e]??0);if(a!==n)return a<n?-1:1}return Hi(t,Wi,e,a)}),e});'
    ),
    @(
        'o=(s?u(s.list):h()).filter(s=>!1!==r.has(s.id)&&(!!Ri(e,s,a.requires.statistic.model.get(s.id))&&Vi(t,s)));i(()=>n.set(o))',
        'o=(s?u(s.list):h()).filter(s=>!1!==r.has(s.id)&&(!!Ri(e,s,a.requires.statistic.model.get(s.id))&&Vi(t,s)));const hcc=(()=>{try{return JSON.parse(a.requires.filters.model.hccSortJson.get()||"{}")}catch(e){return{}}})(),hccValues=hcc.values||{},hccAllowed=new Set((hcc.allowed||[]).map(e=>String(e)));hcc.filtered&&o.splice(0,o.length,...o.filter(e=>hccAllowed.has(String(e.id))||hccAllowed.has(String(e.inventoryId)))),o.sort((e,t)=>{const a=hccValues[String(e.id)]||hccValues[e.id]||hccValues[String(e.inventoryId)]||hccValues[e.inventoryId]||[],s=hccValues[String(t.id)]||hccValues[t.id]||hccValues[String(t.inventoryId)]||hccValues[t.inventoryId]||[],n=Math.max(a.length,s.length);for(let e=0;e<n;e++){const t=Number(a[e]??0),n=Number(s[e]??0);if(t!==n)return t<n?-1:1}return 0}),i(()=>n.set(o))'
    ),
    @(
        'carouselTypeChange:n.createCallback(e=>({rowCount:e}),"onCarouselTypeChange")',
        'carouselTypeChange:n.createCallback(e=>"object"==typeof e?e:{rowCount:e,hccAuto:!1},"onCarouselTypeChange")'
    ),
    @(
        'onClick:function(){const e=1===a?2:1;t.controls.carouselTypeChange(e)},children:o.jsx(Le,{className:l(ax.carouselIcon,2===a&&ax.carouselIcon__active),path:"hangar.filter.carousel_selector"})',
        'onClick:function(){const e=a>=4?1:a+1;t.controls.carouselTypeChange(e)},children:o.jsx(Le,{className:l(ax.carouselIcon,1<a&&ax.carouselIcon__active),path:"hangar.filter.carousel_selector"})'
    ),
    @(
        'return jt(2===e?t.double:t.single)',
        'return jt(1<e?t.double:t.single)'
    ),
    @(
        's&&i(2!==t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t})',
        's&&i(1===t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t})'
    ),
    @(
        'N=(j=w,n.useMemo(()=>{const e=[];for(let t=0;t<j.length;t+=2)e.push(j.slice(t,t+2));return 1===e.at(-1)?.length&&e.at(-1)?.push(Yx),e},[j]));var j;',
        'N=(j=w,n.useMemo(()=>{const e=[];for(let t=0;t<j.length;t+=v)e.push(j.slice(t,t+v));const a=e.at(-1);if(a)for(;a.length<v;)a.push(Yx);return e},[j,v]));var j;'
    ),
    @(
        'function(e,t,a,s,n){const i=2===s;function r(s)',
        'function(e,t,a,s,n){const i=1<s;function r(s)'
    ),
    @(
        'totalElements:2===v?N.length:w.length',
        'totalElements:1<v?N.length:w.length'
    ),
    @(
        'return 2===v?',
        'return 1<v?'
    ),
    @(
        'classNames:{base:l(jy,I&&Iy),element:l(ky,t&&Sy)}',
        'classNames:{base:l(jy,I&&Iy),element:l(ky,t&&Sy,3===v&&"hcc-native-carousel--3",4===v&&"hcc-native-carousel--4")}'
    ),
    @(
        'className:l(rW,2===s&&oW)',
        'className:l(rW,1<s&&oW)'
    )
)

foreach ($replacement in $replacements) {
    $from = $replacement[0]
    $to = $replacement[1]
    $count = ([regex]::Matches($source, [regex]::Escape($from))).Count
    if ($count -ne 1) {
        throw "Expected one native carousel patch point, found $count for: $from"
    }
    $source = $source.Replace($from, $to)
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
[IO.File]::WriteAllText($OutputPath, $source, (New-Object Text.UTF8Encoding($false)))
Write-Output "Patched native carousel bundle: $OutputPath"
