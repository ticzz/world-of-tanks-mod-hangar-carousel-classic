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
$packagePath = Join-Path $GameRoot 'res\packages\frontline.pkg'
$entryPath = 'frontline/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js'
if (-not (Test-Path -LiteralPath $packagePath)) {
    throw "Frontline package is missing: $packagePath"
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($packagePath)
try {
    $entry = $zip.GetEntry($entryPath)
    if (-not $entry) {
        throw "Frontline hangar bundle is missing from $packagePath."
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
if ($sourceHash -ne '15B951A22F4008936B6B027B3D08366183831A27F60DA1F82FF10245C9F895DB') {
    throw "Unsupported Frontline hangar bundle $sourceHash; expected the verified WoT 2.4.1.1 bundle."
}

$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
$replacements = @(
    @(
        'r={...e.primitives(["defaultFilters"])},',
        'r={...e.primitives(["defaultFilters","hccSortJson"])},'
    ),
    @(
        'o={...e.primitives(["carouselRowCount"]),filters:Ba.box(n,{deep:!1}),searchName:Ba.box(s?.[0]??""),nations:e.arrayClone("nationsOrder")};',
        'o={...e.primitives(["carouselRowCount"]),hccSortJson:r.hccSortJson,filters:Ba.box(n,{deep:!1}),searchName:Ba.box(s?.[0]??""),nations:e.arrayClone("nationsOrder")};'
    ),
    @(
        'h=ka.shallow(()=>{const t=e.filters.model.computes.nationToIndex();return S(e.myVehicles.model.getAll(),(e,a)=>bn(t,jn,e,a))})',
        'h=ka.shallow(()=>{const nationIndex=e.filters.model.computes.nationToIndex(),hcc=(()=>{try{return JSON.parse(e.filters.model.hccSortJson.get()||"{}")}catch(e){return{}}})(),values=hcc.values||{},allowed=new Set((hcc.allowed||[]).map(e=>String(e)));return S(e.myVehicles.model.getAll().filter(e=>!hcc.filtered||allowed.has(String(e.id))||allowed.has(String(e.inventoryId))),(e,a)=>{const t=values[String(e.id)]||values[e.id]||values[String(e.inventoryId)]||values[e.inventoryId]||[],s=values[String(a.id)]||values[a.id]||values[String(a.inventoryId)]||values[a.inventoryId]||[];for(let e=0;e<Math.max(t.length,s.length);e++){const a=Number(t[e]??0),n=Number(s[e]??0);if(a!==n)return a<n?-1:1}return bn(nationIndex,jn,e,a)})})'
    ),
    @(
        'v=ka.shallow(()=>{const t=i.filters.get(),a=h(),s=i.searchName.get();return a.filter(a=>!!gn(s,a)&&hn(t,a,e.statistic.model.get(a.id)))})',
        'v=ka.shallow(()=>{const t=i.filters.get(),a=h(),s=i.searchName.get(),hcc=(()=>{try{return JSON.parse(e.filters.model.hccSortJson.get()||"{}")}catch(e){return{}}})(),allowed=new Set((hcc.allowed||[]).map(e=>String(e)));return a.filter(a=>!!gn(s,a)&&hn(t,a,e.statistic.model.get(a.id))&&(!hcc.filtered||allowed.has(String(a.id))||allowed.has(String(a.inventoryId))))})'
    ),
    @(
        'm=ka.primitive(()=>{const t=[...c.getAll()],a=e.requires.filters.model.computes.nationToIndex();return t.sort((e,t)=>bn(a,jn,e,t)),t});',
        'm=ka.primitive(()=>{const t=[...c.getAll()],nationIndex=e.requires.filters.model.computes.nationToIndex(),hcc=(()=>{try{return JSON.parse(e.requires.filters.model.hccSortJson.get()||"{}")}catch(e){console.error("[HangarCarouselClassic] Invalid Frontline filter/sort payload",e);return{}}})(),values=hcc.values||{},allowed=new Set((hcc.allowed||[]).map(e=>String(e)));return hcc.filtered&&t.splice(0,t.length,...t.filter(e=>allowed.has(String(e.id))||allowed.has(String(e.inventoryId)))),t.sort((e,t)=>{const a=values[String(e.id)]||values[e.id]||values[String(e.inventoryId)]||values[e.inventoryId]||[],s=values[String(t.id)]||values[t.id]||values[String(t.inventoryId)]||values[t.inventoryId]||[];for(let e=0;e<Math.max(a.length,s.length);e++){const t=Number(a[e]??0),n=Number(s[e]??0);if(t!==n)return t<n?-1:1}return bn(nationIndex,jn,e,t)}),t});'
    ),
    @(
        'i=(n?l(n.list):m()).filter(a=>!1!==r.has(a.id)&&(!!hn(t,a,e.requires.statistic.model.get(a.id))&&gn(s,a)));ls(()=>a.set(i))',
        'i=(n?l(n.list):m()).filter(a=>!1!==r.has(a.id)&&(!!hn(t,a,e.requires.statistic.model.get(a.id))&&gn(s,a)));const hcc=(()=>{try{return JSON.parse(e.requires.filters.model.hccSortJson.get()||"{}")}catch(e){console.error("[HangarCarouselClassic] Invalid Frontline filter/sort payload",e);return{}}})(),hccValues=hcc.values||{},hccAllowed=new Set((hcc.allowed||[]).map(e=>String(e)));hcc.filtered&&i.splice(0,i.length,...i.filter(e=>hccAllowed.has(String(e.id))||hccAllowed.has(String(e.inventoryId)))),i.sort((e,t)=>{const a=hccValues[String(e.id)]||hccValues[e.id]||hccValues[String(e.inventoryId)]||hccValues[e.inventoryId]||[],s=hccValues[String(t.id)]||hccValues[t.id]||hccValues[String(t.inventoryId)]||hccValues[t.inventoryId]||[];for(let e=0;e<Math.max(a.length,s.length);e++){const t=Number(a[e]??0),n=Number(s[e]??0);if(t!==n)return t<n?-1:1}return 0}),ls(()=>a.set(i))'
    ),
    @(
        '2===e?t.double:t.single',
        '1<e?t.double:t.single'
    ),
    @(
        '2!==t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}',
        '1===t?{visibleSlots:Math.ceil(s/a),cardWidth:a,carouselRows:t}:{visibleSlots:Math.ceil(s/a*t),cardWidth:a,carouselRows:t}'
    ),
    @(
        'for(let a=0;a<e.length;a+=2)t.push(e.slice(a,a+2));return 1===t.at(-1)?.length&&t.at(-1)?.push(q_),t},[e])}(b)',
        'for(let a=0;a<e.length;a+=h)t.push(e.slice(a,a+h));const n=t.at(-1);if(n)for(;n.length<h;)n.push(q_);return t},[e,h])}(b)'
    ),
    @(
        'const r=2===s;function i(s)',
        'const r=1<s;function i(s)'
    ),
    @(
        'totalElements:2===h?x.length:b.length',
        'totalElements:1<h?x.length:b.length'
    ),
    @(
        'return 2===h?(0,nr.jsx)(ge,',
        'return 1<h?(0,nr.jsx)(ge,'
    ),
    @(
        'classNames:{base:Sa(bh,y&&xh),element:Sa(yh,t&&Ch)}',
        'classNames:{base:Sa(bh,y&&xh,3===h&&"hcc-native-carousel--3",4===h&&"hcc-native-carousel--4"),element:Sa(yh,t&&Ch)}'
    ),
    @(
        'className:Sa(CR,2===s&&jR)',
        'className:Sa(CR,2===s&&jR,3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4")'
    )
)

foreach ($replacement in $replacements) {
    $from = $replacement[0]
    $to = $replacement[1]
    $count = ([regex]::Matches($source, [regex]::Escape($from))).Count
    if ($count -ne 1) {
        throw "Expected one Frontline carousel patch point, found $count for: $from"
    }
    $source = $source.Replace($from, $to)
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
[IO.File]::WriteAllText($OutputPath, $source, (New-Object Text.UTF8Encoding($false)))
Write-Output "Patched Frontline hangar bundle: $OutputPath"
